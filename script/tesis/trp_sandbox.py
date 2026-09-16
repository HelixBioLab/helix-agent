#!/usr/bin/env python3
"""Operator-only Linux resource allocation. Never install this as a setuid helper.

Run with sudo and a reviewed command after --. The command runs as --user;
only this supervisor creates mounts/cgroups. One fresh directory per allocation.
The evidence copy and task logs stay on the quota until explicitly exported.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import signal
import subprocess
import sys
import time
import uuid

VERSION = "trp-sandbox/1.0.0"
MiB = 1024**2


def run(*argv):
    return subprocess.run(argv, check=True, text=True, capture_output=True,
                          env={**os.environ, "LC_ALL": "C"}).stdout.strip()


def write(path, value):
    target = Path(path)
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.chmod(0o644)
    temporary.replace(target)


def group_snapshot(group):
    base = Path("/sys/fs/cgroup") / group
    result = {}
    for name in ("cpu.max", "cpu.stat", "memory.max", "memory.min", "memory.current",
                 "memory.peak", "memory.events", "memory.swap.max", "pids.current"):
        if (base / name).exists():
            result[name] = (base / name).read_text().strip()
    return result


def quota(mount):
    report = run("xfs_quota", "-x", "-c", "report -p -b -n", str(mount))
    line = re.search(r"^#42\s+(\d+)\s+(\d+)\s+(\d+)\s", report, re.M)
    if not line:
        raise RuntimeError("XFS project 42 missing from kernel report")
    state = run("xfs_quota", "-x", "-c", "state -p", str(mount))
    if "Accounting: ON" not in state or "Enforcement: ON" not in state:
        raise RuntimeError("XFS project accounting/enforcement inactive")
    return {"usedBytes": int(line[1]) * 1024, "hardBytes": int(line[3]) * 1024,
            "report": report, "state": state}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", required=True, help="New directory; refuses existing paths")
    p.add_argument("--user", required=True)
    p.add_argument("--cwd", required=True)
    p.add_argument("--work-mib", type=int, default=64)
    p.add_argument("--seconds", type=int, default=1080)
    p.add_argument("--path", required=True, help="Reviewed executable search path")
    p.add_argument("--nextflow-home", required=True, help="Preloaded distribution cache")
    p.add_argument("--env", action="append", default=[])
    p.add_argument("command", nargs=argparse.REMAINDER)
    a = p.parse_args()
    command = a.command[1:] if a.command[:1] == ["--"] else a.command
    if os.geteuid() != 0 or not command or not 1 <= a.work_mib <= 1024 or not 1 <= a.seconds <= 3600:
        p.error("Root supervisor, command, 1..1024 MiB and 1..3600 seconds required")
    account = pwd.getpwnam(a.user)
    if account.pw_uid == 0:
        p.error("Controller must be an unprivileged user")
    base = Path(a.base).absolute()
    if not re.fullmatch(r"/[A-Za-z0-9_./-]+", str(base)):
        p.error("Base path must contain only letters, digits, slash, dot, underscore or hyphen")
    if base.exists() or base.is_symlink() or not base.parent.is_dir():
        p.error("Base must be a new child of an existing directory")
    # The parent is operator-selected, not an LLM tool argument. Nothing is deleted.
    base.mkdir(mode=0o755)
    name = "trp" + uuid.uuid4().hex[:16]
    aggregate = name + ".slice"
    tasks = name + "-tasks.slice"
    controller = name + "-controller.service"
    state_dir = Path("/run/trp-sandbox")
    state_dir.mkdir(mode=0o755, exist_ok=True)
    if state_dir.stat().st_uid != 0 or state_dir.stat().st_mode & 0o022:
        raise RuntimeError("Unsafe state directory")
    state_path = state_dir / (name + ".json")
    disk, mount = base / "disk.img", base / "mount"
    mount.mkdir()
    workspace = mount / "workspace"
    mounted = False
    started = time.monotonic()
    samples = []
    observed_containers = {}
    event_process = None
    event_file = None
    aborted = False
    def stop_signal(_signum, _frame):
        nonlocal aborted
        aborted = True
    signal.signal(signal.SIGTERM, stop_signal)
    signal.signal(signal.SIGINT, stop_signal)
    code = 1
    try:
        run("fallocate", "-l", str(max(512, a.work_mib + 256)) + "M", str(disk))
        disk.chmod(0o600)
        run("mkfs.xfs", "-f", "-q", str(disk))
        run("mount", "-o", "loop,prjquota,allocsize=4k", str(disk), str(mount))
        mounted = True
        workspace.mkdir(mode=0o700)
        run("xfs_quota", "-x", "-c", f"project -s -p {workspace} 42", str(mount))
        run("xfs_quota", "-x", "-c", f"limit -p bhard={a.work_mib * 1024}k 42", str(mount))
        os.chown(workspace, account.pw_uid, account.pw_gid)
        for directory in (workspace / "tmp", workspace / "home", workspace / "export"):
            directory.mkdir(mode=0o700)
            os.chown(directory, account.pw_uid, account.pw_gid)
        run("systemctl", "start", aggregate)
        run("systemctl", "set-property", "--runtime", aggregate, "CPUQuota=300%",
            "MemoryMax=4G", "MemoryMin=4G", "MemorySwapMax=0", "TasksMax=512")
        run("systemctl", "start", tasks)
        run("systemctl", "set-property", "--runtime", tasks, "CPUQuota=200%",
            "MemoryMax=2G", "MemoryMin=2G", "MemorySwapMax=0", "TasksMax=256")
        config = {"version": VERSION, "id": name, "workspace": str(workspace),
                  "device": workspace.stat().st_dev, "projectId": 42,
                  "workBytes": a.work_mib * MiB, "cpus": 3, "memoryBytes": 4096 * MiB,
                  "aggregate": aggregate, "tasks": aggregate + "/" + tasks,
                  "dockerParent": tasks, "controller": aggregate + "/" + controller,
                  "controllerCpus": 1, "controllerMemoryBytes": 2048 * MiB,
                  "controllerMemoryMin": 2048 * MiB, "wallSeconds": a.seconds,
                  "supervisorSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        def snapshot():
            nonlocal samples
            q = quota(mount)
            sample = {"elapsedSeconds": round(time.monotonic() - started, 3),
                      "observedAt": time.time(), "quota": q,
                      "aggregate": group_snapshot(aggregate),
                      "controller": group_snapshot(config["controller"]),
                      "tasks": group_snapshot(config["tasks"])}
            samples.append(sample)
            write(state_path, {"config": config, "sample": sample, "supervisorPid": os.getpid()})
            return sample
        snapshot()
        event_file = (base / "docker-events.jsonl").open("w")
        event_process = subprocess.Popen(["docker", "events", "--filter", "label=trp.sandbox=" + name,
                                          "--format", "{{json .}}"], stdout=event_file, stderr=subprocess.DEVNULL)
        env = {"PATH": a.path, "HOME": str(workspace / "home"), "USER": a.user,
               "TMPDIR": str(workspace / "tmp"), "NXF_HOME": a.nextflow_home,
               "NXF_OFFLINE": "true", "NXF_DISABLE_CHECK_LATEST": "true",
               "NXF_OPTS": f"-Xmx1536m -XX:ActiveProcessorCount=1 -Djava.io.tmpdir={workspace / 'tmp'}",
               "BIOINFORMATICA_TRP_SANDBOX": str(state_path),
               "TRP_SANDBOX_WORKSPACE": str(workspace), "TRP_REFERENCE_OUTPUT": str(workspace / "export/reference"),
               "LC_ALL": "C", "LANG": "C.UTF-8"}
        for item in a.env:
            key, value = item.split("=", 1)
            if key in env or not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
                raise ValueError("Cannot override reserved sandbox environment")
            env[key] = value
        run("systemd-run", "--quiet", "--unit=" + controller, "--slice=" + aggregate,
            "--property=User=" + a.user, "--property=Group=" + str(account.pw_gid),
            "--property=WorkingDirectory=" + str(Path(a.cwd).resolve()),
            "--property=CPUQuota=100%", "--property=MemoryMax=2G", "--property=MemoryMin=2G",
            "--property=MemorySwapMax=0", "--property=TasksMax=256", "--property=RemainAfterExit=yes",
            "--property=OOMPolicy=continue",
            "--property=RuntimeMaxSec=" + str(a.seconds), "--property=KillMode=control-group",
            "--property=StandardOutput=append:" + str(workspace / "launcher.stdout.log"),
            "--property=StandardError=append:" + str(workspace / "launcher.stderr.log"),
            *("--setenv=" + k + "=" + v for k, v in env.items()), "--", *command)
        while True:
            snapshot()
            # The generated Docker label restricts inspection to this allocation.
            ids = run("docker", "ps", "-aq", "--filter", "label=trp.sandbox=" + name).split()
            for identity in ids:
                if identity not in observed_containers:
                    data = json.loads(run("docker", "inspect", identity))[0]
                    observed_containers[identity] = {"Id": identity, "Image": data["Image"],
                        "HostConfig": {k: data["HostConfig"][k] for k in
                            ("CgroupParent", "Memory", "MemorySwap", "NanoCpus", "ReadonlyRootfs", "LogConfig")},
                        "Pid": data["State"]["Pid"]}
            state = run("systemctl", "show", controller, "--property=SubState", "--value")
            if state in ("exited", "failed", "dead") or aborted or time.monotonic() - started > a.seconds + 30:
                break
            time.sleep(0.1)
        code = int(run("systemctl", "show", controller, "--property=ExecMainStatus", "--value"))
        if aborted:
            code = 130
        result = run("systemctl", "show", controller, "--property=Result", "--value")
        if result != "success" and code == 0:
            code = 1
        snapshot()
        event_process.terminate()
        event_process.wait(timeout=10)
        event_file.close()
        write(base / "resource-observation.json", {"version": VERSION, "config": config,
              "command": command, "exitCode": code, "serviceResult": result,
              "samplePeriodSeconds": 0.1, "sampling": "0.1 second sleep plus quota/docker queries; actual timestamps retained",
              "sampledPeakWorkBytes": max(s["quota"]["usedBytes"] for s in samples),
              "observedContainers": list(observed_containers.values()), "samples": samples,
              "scope": "development resource contrast; no independent scientific evaluation",
              "exclusions": ["preloaded distribution, source and dependency caches", "Docker image layers and shared daemon",
                             "supervisor observations outside project, retained separately"]})
        # Export only after the budgeted command has stopped. This is an explicitly
        # separate archival copy, never counted as space still available to the run.
        run("systemctl", "stop", controller)
        run("systemctl", "stop", tasks)
        shutil.copytree(workspace, base / "artifacts", symlinks=True)
        for directory, dirs, files in os.walk(base / "artifacts"):
            os.chown(directory, account.pw_uid, account.pw_gid)
            for item in dirs + files:
                os.chown(Path(directory) / item, account.pw_uid, account.pw_gid, follow_symlinks=False)
        print(json.dumps({"exitCode": code, "evidence": str(base / "resource-observation.json")}))
    finally:
        if event_process and event_process.poll() is None:
            event_process.terminate()
            event_process.wait(timeout=10)
        if event_file and not event_file.closed:
            event_file.close()
        for unit in (controller, tasks, aggregate):
            subprocess.run(["systemctl", "stop", unit], capture_output=True)
        subprocess.run(["systemctl", "reset-failed", controller], capture_output=True)
        state_path.unlink(missing_ok=True)
        # No lazy unmount: an outstanding user/container is an error worth preserving.
        if mounted:
            run("umount", str(mount))
        # Keep the private image and artifacts for review; no automatic data deletion.
    return code


if __name__ == "__main__":
    sys.exit(main())
