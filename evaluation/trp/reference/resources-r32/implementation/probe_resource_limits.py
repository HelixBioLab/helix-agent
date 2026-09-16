#!/usr/bin/env python3
"""Intentional pressure tests inside an operator allocation, not scientific cases."""
import argparse
import errno
import json
import multiprocessing
import os
from pathlib import Path
import time


def spin(seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        sum(range(1000))


def fill_memory():
    blocks = []
    while True:
        blocks.append(bytearray(16 * 1024**2))


def values(path):
    return {k: int(v) for k, v in (line.split() for line in path.read_text().splitlines())}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["disk", "cpu", "memory"])
    a = p.parse_args()
    state = json.loads(Path(os.environ["BIOINFORMATICA_TRP_SANDBOX"]).read_text())
    root = Path(state["config"]["workspace"])
    cg = Path("/sys/fs/cgroup") / state["config"]["controller"]
    result = {"mode": a.mode, "kind": "intentional-kernel-limit-probe", "scientificRun": False}
    if a.mode == "disk":
        total = 0
        targets = [root / f"fill-{i}" for i in range(2)]
        for item in targets:
            item.mkdir()
        try:
            # Alternate directories: the limit must be aggregate, not per-file.
            with (targets[0] / "a.bin").open("wb", buffering=0) as f, (targets[1] / "b.bin").open("wb", buffering=0) as g:
                for _ in range(4096):
                    for stream in (f, g):
                        total += stream.write(b"x" * (256 * 1024))
        except OSError as e:
            result.update({"errno": e.errno, "message": str(e), "writtenBytes": total})
            assert e.errno in (errno.EDQUOT, errno.ENOSPC), result
        else:
            raise AssertionError("Kernel allowed writes past the workspace budget")
        assert total <= state["config"]["workBytes"]
        # Leave the saturated project visible for several supervisor samples.
        time.sleep(0.5)
        # Release space for the probe report; supervisor keeps peak/counters.
        for item in targets:
            for file in item.iterdir():
                file.unlink()
    elif a.mode == "cpu":
        before = values(cg / "cpu.stat")
        start = time.monotonic()
        children = [multiprocessing.Process(target=spin, args=(4,)) for _ in range(4)]
        for child in children:
            child.start()
        for child in children:
            child.join()
        elapsed = time.monotonic() - start
        after = values(cg / "cpu.stat")
        cores = (after["usage_usec"] - before["usage_usec"]) / 1e6 / elapsed
        result.update({"elapsedSeconds": elapsed, "before": before, "after": after, "meanCpus": cores})
        assert after["nr_throttled"] > before["nr_throttled"] and cores < 1.1, result
    else:
        before = values(cg / "memory.events")
        child = multiprocessing.Process(target=fill_memory)
        child.start()
        child.join(30)
        if child.is_alive():
            child.kill()
            raise AssertionError("Memory limit did not kill the allocating process")
        after = values(cg / "memory.events")
        result.update({"before": before, "after": after, "childExitCode": child.exitcode,
                       "peakBytes": int((cg / "memory.peak").read_text()),
                       "hardBytes": int((cg / "memory.max").read_text())})
        assert child.exitcode == -9 and after["oom_kill"] > before["oom_kill"], result
    result["passed"] = True
    (root / "probe.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
