#!/usr/bin/env python3
"""Archive a finished sandbox run without copying its private filesystem image."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile


def main():
    p = argparse.ArgumentParser()
    p.add_argument("run", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    observation = a.run / "resource-observation.json"
    if not observation.is_file():
        p.error("Run has no final observation")
    included = {"resource-observation.json": observation}
    for name in ["docker-events.jsonl", "artifacts/probe.json", "artifacts/launcher.stdout.log", "artifacts/launcher.stderr.log"]:
        if (a.run / name).is_file():
            included[name] = a.run / name
    evidence = a.run / "artifacts/export/reference/evidence"
    if evidence.is_dir():
        for file in sorted(evidence.rglob("*")):
            if file.is_symlink():
                raise ValueError("Portable evidence must not contain symlinks")
            if file.is_file():
                included["evidence/" + file.relative_to(evidence).as_posix()] = file
        engineering = a.run / "artifacts/export/reference/engineering-reference.json"
        included["engineering-reference.json"] = engineering
    target = a.output / (a.run.name + ".tar.gz")
    if target.exists():
        p.error("Archive already exists")
    with target.open("xb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode="w|") as archive:
            for name, source in sorted(included.items()):
                data = source.read_bytes()
                info = tarfile.TarInfo(name)
                info.size = len(data)
                info.mode = 0o600
                archive.addfile(info, io.BytesIO(data))
    print(json.dumps({"path": str(target), "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                      "files": len(included), "bytes": target.stat().st_size}))


if __name__ == "__main__":
    main()
