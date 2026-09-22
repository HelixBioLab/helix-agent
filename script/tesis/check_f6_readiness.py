#!/usr/bin/env python3
"""Check a scoped F6 freeze without running inference or manufacturing evidence.

This verifies freeze metadata and artifact bytes. It does not certify scientific
labels, partition independence or sample quality; those need a recorded review.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SCOPES = ("language", "graphs", "resources", "trace", "structural")
COMMON = ("protocol_sha256", "catalog_sha256", "case_manifest_sha256",
          "assignments_sha256", "source_and_license_manifest_sha256",
          "hardware_inventory_sha256", "image_manifest_sha256", "dependency_lock_sha256")
EXTERNAL = ("annotation_guide_sha256", "annotation_agreement_sha256")


def present(value):
    return value is not None and value not in ("", "pending", "unknown", "template_not_frozen")


def check(freeze, protocol, artifacts, root, commit, dirty, scopes, cluster=False):
    """Return per-scope blockers; artifacts maps hash field names to local paths."""
    if not scopes or not set(scopes) <= set(SCOPES):
        raise ValueError("Choose one or more supported scopes")
    cache = {}

    def artifact(key):
        if key in cache:
            return cache[key]
        expected = freeze.get(key)
        path = artifacts.get(key)
        reason = None
        if not isinstance(expected, str) or not re.fullmatch(r"[a-f0-9]{64}", expected):
            reason = f"{key}: missing or invalid frozen SHA-256"
        elif not path:
            reason = f"{key}: artifact path missing"
        else:
            target = (root / path).resolve()
            try:
                actual = hashlib.sha256(target.read_bytes()).hexdigest()
                if actual != expected:
                    reason = f"{key}: artifact hash mismatch"
            except OSError:
                reason = f"{key}: artifact unavailable"
        cache[key] = reason
        return reason

    common = []
    if freeze.get("status") != "frozen":
        common.append("status: freeze has not been finalized")
    for key in ("frozen_at", "catalog_version"):
        if not present(freeze.get(key)):
            common.append(f"{key}: missing")
    if not re.fullmatch(r"[a-f0-9]{40}", str(freeze.get("code_commit", ""))) or freeze.get("code_commit") != commit:
        common.append("code_commit: absent or different from evaluated checkout")
    if dirty:
        common.append("code_commit: working tree contains uncommitted changes")
    if freeze.get("protocol_version") != protocol.get("version"):
        common.append("protocol_version: mismatch")
    if freeze.get("order_seeds") != protocol.get("order_seeds"):
        common.append("order_seeds: mismatch with protocol")
    for key in COMMON:
        if reason := artifact(key):
            common.append(reason)
    if cluster and freeze.get("cluster_access") != "confirmed":
        common.append("cluster_access: required only for a campaign claiming cluster execution")
    results = {}
    for scope in scopes:
        reasons = list(common)
        if scope in ("language", "trace", "structural"):
            for key in ("external_annotator_id",):
                if not present(freeze.get(key)):
                    reasons.append(f"{key}: independent participant not recorded")
            if freeze.get("external_annotation") != "confirmed":
                reasons.append("external_annotation: participant agreement pending")
            for key in EXTERNAL:
                if reason := artifact(key):
                    reasons.append(reason)
        if scope == "language":
            for key in ("provider", "model_id", "provider_model_revision", "provider_seed_support"):
                if not present(freeze.get(key)):
                    reasons.append(f"{key}: exact model configuration missing")
            for key in ("temperature", "top_p"):
                # Explicit unsupported is allowed; omitting a default is not.
                value = freeze.get(key)
                if value != "unsupported" and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 or (key == "top_p" and value > 1)):
                    reasons.append(f"{key}: record numeric value or unsupported")
            for key in ("max_output_tokens", "api_call_budget"):
                value = freeze.get(key)
                if type(value) is not int or value <= 0:
                    reasons.append(f"{key}: positive integer required")
            value = freeze.get("api_cost_limit")
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                reasons.append("api_cost_limit: positive authorized limit required")
            if reason := artifact("system_instructions_sha256"):
                reasons.append(reason)
        if scope == "structural":
            for key in ("original_structural_inputs_sha256", "independent_reference_review_sha256"):
                if reason := artifact(key):
                    reasons.append(reason)
        # A signed-off review must address minima, family separation, references
        # and eligibility; a hash alone cannot establish their scientific truth.
        if reason := artifact(f"{scope}_corpus_review_sha256"):
            reasons.append(reason)
        results[scope] = {"metadata_ready": not reasons, "blockers": reasons}
    return {"schema_version": "trp-f6-readiness/1.0", "scopes": results,
            "metadata_ready": all(r["metadata_ready"] for r in results.values()),
            "cluster_claim": cluster, "paid_calls_executed": 0,
            "scope_limit": "Metadata and artifact integrity only; scientific adequacy and independent labels require review. Development executions remain permitted when this gate is blocked.",
            "protocol_sample_minima": protocol["sample_minima"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", type=Path, default=ROOT / "evaluation/trp/freeze.template.json")
    parser.add_argument("--artifacts", type=Path, help="JSON mapping SHA-256 fields to file paths")
    parser.add_argument("--scope", action="append", choices=SCOPES)
    parser.add_argument("--cluster", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    protocol = json.loads((ROOT / "evaluation/trp/protocol.json").read_text())
    freeze = json.loads(args.freeze.read_text())
    artifacts = json.loads(args.artifacts.read_text()) if args.artifacts else {}
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
    result = check(freeze, protocol, artifacts, ROOT, commit, dirty, args.scope or SCOPES, args.cluster)
    result["observed_commit"] = commit
    result["freeze_path"] = str(args.freeze.relative_to(ROOT)) if args.freeze.is_relative_to(ROOT) else str(args.freeze)
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded)
    print(encoded)
    return 0 if result["metadata_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
