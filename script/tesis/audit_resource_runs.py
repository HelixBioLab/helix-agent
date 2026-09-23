#!/usr/bin/env python3
"""Recompute R3.2 engineering results from closed archives using trusted code."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "evaluation/trp/reference/resources-r32"


def archive(path, target):
    with tarfile.open(path) as tar:
        names = set()
        for member in tar:
            parts = Path(member.name).parts
            if not member.isfile() or member.name.startswith("/") or ".." in parts or member.name in names:
                raise ValueError("Unsafe resource archive member")
            names.add(member.name)
            destination = target / member.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(tar.extractfile(member).read())


def evaluate(directory):
    obs = json.loads((directory / "resource-observation.json").read_text())
    config = obs["config"]
    assert obs["exitCode"] == 0 and obs["serviceResult"] == "success"
    for sample in obs["samples"]:
        assert sample["quota"]["hardBytes"] == config["workBytes"]
        assert sample["quota"]["usedBytes"] <= config["workBytes"]
        for name, cpus, memory in [("aggregate", 3, 4096*1024**2),
                                  ("controller", 1, 2048*1024**2), ("tasks", 2, 2048*1024**2)]:
            group = sample[name]
            if not group:
                assert name == "controller"  # before systemd starts the service
                continue
            quota, period = map(int, group["cpu.max"].split())
            assert quota / period == cpus
            assert int(group["memory.max"]) == memory and int(group["memory.min"]) == memory
            assert int(group["memory.swap.max"]) == 0
    probe = directory / "artifacts/probe.json"
    if probe.exists():
        data = json.loads(probe.read_text())
        assert data["passed"] and not data["scientificRun"]
        return {"kind": "pressure", **data, "sampledPeakWorkBytes": obs["sampledPeakWorkBytes"]}
    evidence = directory / "evidence"
    manifest = hashlib.sha256((evidence / "manifest.json").read_bytes()).hexdigest()
    check = subprocess.run(["python3", str(ROOT / "packages/helix/src/trp/verify_bundle.py.txt"),
                            str(evidence), "--sha256", manifest], capture_output=True, text=True, check=True)
    cold = json.loads(check.stdout)
    run = evidence / "run"
    admission = json.loads((run / "admission.json").read_text())
    budget = json.loads((run / "budget.json").read_text())
    result = json.loads((run / "run.json").read_text())
    assert result["status"] == "succeeded"
    assert json.loads((run / "enforcement.json").read_text()) == config
    assert config["workBytes"] <= budget["workBytes"] and budget["requireHardStorageLimit"]
    containers = obs["observedContainers"]
    assert len(containers) == 4
    for item in containers:
        h = item["HostConfig"]
        assert h["CgroupParent"] == config["dockerParent"]
        assert h["Memory"] == h["MemorySwap"] == 2048*1024**2
        assert h["NanoCpus"] == 2*10**9 and h["ReadonlyRootfs"]
        assert h["LogConfig"]["Type"] == "none"
    events = directory / "docker-events.jsonl"
    if events.exists():
        docker = [json.loads(line) for line in events.read_text().splitlines()]
        for action in ("create", "start", "die"):
            assert sum(e.get("Action") == action for e in docker) == 4
    demand = admission["demand"]
    observed = obs["sampledPeakWorkBytes"]
    peak_memory = max(int(s["aggregate"].get("memory.peak", 0)) for s in obs["samples"])
    assert peak_memory <= budget["memoryBytes"]
    return {"kind": "workflow", "estimator": demand["version"], "sourceBytes": demand["sourceBytes"],
            "estimatedWorkBytes": demand["workBytes"], "sampledPeakWorkBytes": observed,
            "budgetWorkBytes": budget["workBytes"], "signedRelativeMargin": demand["workBytes"] / observed - 1,
            "underestimated": demand["workBytes"] < observed,
            "budgetExceeded": observed > budget["workBytes"], "peakMemoryBytes": peak_memory,
            "elapsedSeconds": obs["samples"][-1]["elapsedSeconds"], "containers": len(containers),
            "measuredTasks": result["measuredTasks"], "geometrySha256": result["geometry"]["sha256"],
            "manifestSha256": manifest, "offlineVerification": cold}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--write", action="store_true")
    a = p.parse_args()
    index = json.loads((REFERENCE / "archives.json").read_text())
    rows = []
    for item in index:
        source = REFERENCE / item["path"]
        assert hashlib.sha256(source.read_bytes()).hexdigest() == item["sha256"]
        with tempfile.TemporaryDirectory(prefix="trp-resource-audit-") as tmp:
            directory = Path(tmp)
            archive(source, directory)
            row = evaluate(directory)
            row["id"] = item["id"]
            rows.append(row)
    final = [r for r in rows if r["id"].startswith("verification-")]
    previous = [r for r in rows if r["id"].startswith("validation-")]
    assert len(final) == 7 and len(previous) == 6
    assert all(r["measuredTasks"] == {"scientificTasks": 2, "stubTasks": 2} for r in final)
    metrics = {"n": len(final), "successful": len(final),
               "budgetExceeded": sum(r["budgetExceeded"] for r in final),
               "underestimated": sum(r["underestimated"] for r in final),
               "medianRelativeOverestimate": statistics.median(max(0, r["signedRelativeMargin"]) for r in final),
               "medianSignedMargin": statistics.median(r["signedRelativeMargin"] for r in final),
               "maxPeakMemoryBytes": max(r["peakMemoryBytes"] for r in final),
               "maxElapsedSeconds": max(r["elapsedSeconds"] for r in final),
               "previousUnderestimatesRetained": sum(r["underestimated"] for r in previous)}
    accepted = metrics["budgetExceeded"] == metrics["underestimated"] == 0 and metrics["medianRelativeOverestimate"] <= .25
    report = {"version": "trp-resource-audit/1.0.0", "engineeringGatePassed": accepted,
              "heldoutEvaluation": False, "thresholdsChanged": False, "metrics": metrics, "runs": rows,
              "limitations": ["Resource engineering contrasts use one development structure and REMARK-size perturbations, not seven independent proteins.",
                              "Storage peaks are samples, not an exact high-water kernel counter. Kernel quota separately enforces the approved budget.",
                              "Quota covers allocated XFS blocks; apparent sparse-file lengths and shared software/image caches are different quantities.",
                              "CPU bandwidth limits are not exclusive cores; memory.min protects used memory subject to kernel hierarchy.",
                              "The reserved 40-scenario T-RESOURCE campaign remains pending."]}
    if a.write:
        (ROOT / "docs/tesis/evidencia/r32.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"engineeringGatePassed": accepted, "metrics": metrics}, indent=2))
    if not accepted:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
