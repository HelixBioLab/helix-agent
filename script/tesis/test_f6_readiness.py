import hashlib
import tempfile
import unittest
from pathlib import Path

from check_f6_readiness import check, COMMON, EXTERNAL, SCOPES


class FreezeReadiness(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.protocol = {"version": "1", "order_seeds": [1, 2, 3], "sample_minima": {"valid_graphs": 50}}
        self.freeze = {"status": "frozen", "frozen_at": "2026-09-21T00:00:00Z", "code_commit": "a" * 40,
                       "catalog_version": "1", "protocol_version": "1", "order_seeds": [1, 2, 3],
                       "provider": "provider", "model_id": "exact-model", "provider_model_revision": "revision",
                       "provider_seed_support": False, "temperature": "unsupported", "top_p": 1,
                       "max_output_tokens": 100, "api_call_budget": 1000, "api_cost_limit": 1,
                       "external_annotator_id": "external-person", "external_annotation": "confirmed"}
        self.artifacts = {}
        for key in (*COMMON, *EXTERNAL, "system_instructions_sha256", "original_structural_inputs_sha256",
                    "independent_reference_review_sha256", *(f"{s}_corpus_review_sha256" for s in SCOPES)):
            (self.root / key).write_text(key)
            self.artifacts[key] = key
            self.freeze[key] = hashlib.sha256(key.encode()).hexdigest()

    def run_check(self, scopes=SCOPES, dirty=False, cluster=False):
        return check(self.freeze, self.protocol, self.artifacts, self.root, "a" * 40, dirty, scopes, cluster)

    def test_complete_artifacts_pass_metadata_gate(self):
        self.assertTrue(self.run_check()["metadata_ready"])

    def test_tampered_file_blocks_all_scopes(self):
        (self.root / "catalog_sha256").write_text("tampered")
        self.assertFalse(self.run_check()["metadata_ready"])
        self.assertTrue(all(any("hash mismatch" in b for b in v["blockers"]) for v in self.run_check()["scopes"].values()))

    def test_annotator_does_not_block_graphs_or_resources(self):
        self.freeze["external_annotator_id"] = None
        self.freeze["external_annotation"] = "pending"
        results = self.run_check()["scopes"]
        self.assertTrue(results["graphs"]["metadata_ready"])
        self.assertTrue(results["resources"]["metadata_ready"])
        self.assertFalse(results["structural"]["metadata_ready"])
        self.assertFalse(results["language"]["metadata_ready"])

    def test_cluster_dependency_is_conditional(self):
        self.assertTrue(self.run_check()["metadata_ready"])
        self.assertFalse(self.run_check(cluster=True)["metadata_ready"])

    def test_no_freeze_from_dirty_checkout(self):
        self.assertFalse(self.run_check(dirty=True)["metadata_ready"])

    def test_model_and_budget_only_required_for_language(self):
        self.freeze["model_id"] = None
        self.freeze["api_cost_limit"] = None
        self.assertTrue(self.run_check(scopes=["graphs"])["metadata_ready"])
        self.assertFalse(self.run_check(scopes=["language"])["metadata_ready"])

    def test_template_never_passes(self):
        self.freeze["status"] = "template_not_frozen"
        self.assertFalse(self.run_check()["metadata_ready"])

    def test_missing_file_blocks(self):
        (self.root / "assignments_sha256").unlink()
        self.assertFalse(self.run_check()["metadata_ready"])

    def test_protocol_seed_changes_block(self):
        self.freeze["order_seeds"] = [4, 5, 6]
        self.assertFalse(self.run_check()["metadata_ready"])

    def test_invalid_scope_rejected(self):
        with self.assertRaises(ValueError):
            self.run_check(scopes=["anything"])

    def test_nonfinite_budget_does_not_pass(self):
        self.freeze["api_cost_limit"] = float("nan")
        self.assertFalse(self.run_check(scopes=["language"])["metadata_ready"])


if __name__ == "__main__":
    unittest.main()
