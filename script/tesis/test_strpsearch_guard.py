"""Scientific-output guard tests; no Docker is needed for these rejection cases."""
import copy
import json
from pathlib import Path
import unittest
from strpsearch_guard import validate, validate_profile

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT/'evaluation/trp/reference/strpsearch-probe-f3/region_1/2XQH_A_162_269.json'

class GuardTests(unittest.TestCase):
    def setUp(self):
        self.rows = json.loads(FIXTURE.read_text())
        self.log = 'Task finished with 0 errors'
        self.residues = set(range(159,417))
    def check(self): return validate(self.log,self.rows,self.residues,'A')
    def test_real_reference(self):
        units, regions = self.check()
        self.assertEqual((len(units),len(regions)),(7,1))
        self.assertEqual((units[0]['start'], units[-1]['end']),(162,269))
    def test_zero_exit_does_not_override_errors(self):
        self.log = 'Task finished with 2 errors'
        with self.assertRaises(ValueError): self.check()
    def test_missing_success_marker(self):
        self.log = 'The query file format is ambiguous'
        with self.assertRaises(ValueError): self.check()
    def test_no_output_is_not_negative(self):
        self.rows = []
        with self.assertRaises(ValueError): self.check()
    def test_wrong_chain(self):
        self.rows[0]['chain_id']='B'
        with self.assertRaises(ValueError): self.check()
    def test_insertion_code(self):
        self.rows[0]['start']='162A'
        with self.assertRaises(ValueError): self.check()
    def test_unobserved_residue(self):
        self.residues.remove(163)
        with self.assertRaises(ValueError): self.check()
    def test_overlapping_units(self):
        self.rows.append(copy.deepcopy(self.rows[0]))
        with self.assertRaises(ValueError): self.check()
    def test_outside_region(self):
        self.rows[0]['region_id']='other'
        with self.assertRaises(ValueError): self.check()
    def test_nonfinite_annotation(self):
        self.rows[0]['score']=float('nan')
        with self.assertRaises(ValueError): self.check()
    def test_nonfinite_profile(self):
        for bad in [float('nan'),float('inf'),'NaN',True]:
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                validate_profile({'x':[1,2],'y':[0.4,bad]})
    def test_ambiguous_profile(self):
        with self.assertRaises(ValueError): validate_profile({'x':[1,1],'y':[.4,.5]})
    def test_malformed_profile(self):
        with self.assertRaises(ValueError): validate_profile({'x':[1,2],'y':[.4]})
    def test_real_profile(self):
        validate_profile(json.loads(FIXTURE.with_name(FIXTURE.stem+'_profile.json').read_text()))

if __name__ == '__main__': unittest.main()
