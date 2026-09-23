#!/usr/bin/env python3
"""Check a Helix NDJSON snapshot using only Python's standard library.

Usage: python3 verify_snapshot.py /path/to/corpus/name.manifest.json [...]
Exit 0 means every supplied snapshot matches; 1 means a check failed; 2 is usage.
This checks file integrity and record counts, not biological truth or authenticity.
"""

import argparse
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re
import sys


def reject_constant(value):
    raise ValueError(f"non-JSON number: {value}")


def unique_keys(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def parse_json(raw):
    return json.loads(raw, parse_constant=reject_constant, object_pairs_hook=unique_keys)


def verify(filename):
    """Stream and hash the original bytes; never import the snapshot writer."""
    manifest_path = Path(filename).resolve(strict=True)
    manifest = parse_json(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be a JSON object")
    for field in ("source", "endpoint", "fetchedAt", "data"):
        if not isinstance(manifest.get(field), str) or not manifest[field].strip():
            raise ValueError(f"{field} must be a non-empty string")
    for field in ("rows", "bytes"):
        if type(manifest.get(field)) is not int or manifest[field] < 0:
            raise ValueError(f"{field} must be a non-negative integer")
    if not isinstance(manifest.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", manifest["sha256"]):
        raise ValueError("sha256 must be 64 lowercase hexadecimal characters")

    relative = Path(manifest["data"])
    windows = PureWindowsPath(manifest["data"])
    if relative.is_absolute() or windows.drive or windows.root or "\\" in manifest["data"]:
        raise ValueError("data must be a portable relative path inside the manifest directory")
    target = (manifest_path.parent / relative).resolve(strict=True)
    if not target.is_relative_to(manifest_path.parent) or target == manifest_path:
        raise ValueError("data must resolve inside the manifest directory to a separate file")
    if not target.is_file():
        raise ValueError("data is not a regular file")

    digest = hashlib.sha256()
    rows = 0
    size = 0
    with target.open("rb") as stream:
        for line in stream:
            digest.update(line)
            size += len(line)
            if not line.strip():
                raise ValueError(f"blank NDJSON record at line {rows + 1}")
            parse_json(line.decode("utf-8"))
            rows += 1
    problems = []
    for field, observed in (("sha256", digest.hexdigest()), ("bytes", size), ("rows", rows)):
        if observed != manifest[field]:
            problems.append(f"{field}: recorded {manifest[field]}, observed {observed}")
    if problems:
        raise ValueError("; ".join(problems))
    return {"manifest": str(manifest_path), "ok": True, "rows": rows, "bytes": size, "sha256": digest.hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifests", nargs="+", help="Explicit snapshot manifest paths; an empty selection is an error")
    args = parser.parse_args()
    checks = []
    for filename in args.manifests:
        try:
            checks.append(verify(filename))
        except (OSError, ValueError, RuntimeError, RecursionError) as error:
            checks.append({"manifest": filename, "ok": False, "error": str(error)})
    ok = all(check["ok"] for check in checks)
    print(json.dumps({"ok": ok, "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
