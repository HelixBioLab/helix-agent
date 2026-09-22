import copy
import json
from pathlib import Path
import tempfile
import unittest

from run_structural_reference import requests
from predicted_geometry import derive, prepare, verify_proposal, execute, validate_csv

REQUEST=dict(requests())['alphafold']
REQUEST['options']['units']=[{'start':10,'end':16},{'start':17,'end':23},{'start':24,'end':30}]

class PredictedGeometry(unittest.TestCase):
    def test_real_afdb_preserves_confidence_without_experimental_claim(self):
        report,units,pdb=derive(REQUEST)
        self.assertEqual(report['provenance']['confidenceScale'],'pLDDT_0_100')
        self.assertEqual(len(units),3)
        self.assertNotIn('EXPDTA',pdb)
        self.assertNotIn('HEADER',pdb)
        self.assertIn('B COLUMN IS PLDDT',pdb)
        rows=[l for l in pdb.splitlines() if l.startswith('ATOM')]
        self.assertEqual(len(rows),21)
        source={int(r['auth']):r for r in report['mapping']}
        for line in rows:
            row=source[int(line[22:26])]
            self.assertAlmostEqual(float(line[60:66]),row['b'],places=2)
            self.assertEqual(line[21],'A')

    def test_missing_pae_rejected(self):
        request=copy.deepcopy(REQUEST);request.pop('pae')
        with self.assertRaisesRegex(ValueError,'PAE-required'):derive(request)

    def test_mismatched_sequence_rejected(self):
        request=copy.deepcopy(REQUEST)
        request['api'][0]['sequence']='A'*len(request['api'][0]['sequence'])
        with self.assertRaises(ValueError):derive(request)

    def test_experimental_source_rejected(self):
        with self.assertRaises(ValueError):derive(dict(requests())['experimental'])

    def test_unknown_producer_rejected(self):
        request=copy.deepcopy(REQUEST)
        request['structure']=request['structure'].replace('AlphaFold','UnknownModel')
        with self.assertRaises(ValueError):derive(request)

    def test_short_geometre_unit_rejected(self):
        request=copy.deepcopy(REQUEST);request['options']['units'][0]={'start':10,'end':14}
        with self.assertRaisesRegex(ValueError,'window-six'):derive(request)

    def test_two_units_cannot_fit_geometre_circle(self):
        request=copy.deepcopy(REQUEST);request['options']['units']=request['options']['units'][:2]
        with self.assertRaisesRegex(ValueError,'three-units'):derive(request)

    def test_preparation_rejects_changed_input_and_wrong_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)/'proposal';p=prepare(REQUEST,d)
            verify_proposal(d,p['digest'])
            with self.assertRaisesRegex(ValueError,'digest-mismatch'):verify_proposal(d,'0'*64)
            (d/'afdb.pdb').write_text((d/'afdb.pdb').read_text()+'REMARK CHANGED\n')
            with self.assertRaisesRegex(ValueError,'input-changed'):verify_proposal(d,p['digest'])

    def test_injected_output_rejected_before_docker(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)/'proposal';p=prepare(REQUEST,d)
            (d/'geometry.csv').write_text('pretend success')
            with self.assertRaisesRegex(ValueError,'injected-output'):execute(d,p['digest'])

    def test_csv_rejects_nonfinite_values(self):
        header='pdb_id,chain,unit_start,unit_end,curvature,twist,twist_hand,pitch,pitch_hand,tmscore,yaw\n'
        rows='afdb,A,10,20,nan,0,0,0,0,0,0\nafdb,A,mean,,0,0,0,0,0,0,0\nafdb,A,std,,0,0,0,0,0,0,0\n'
        with self.assertRaisesRegex(ValueError,'nonfinite'):
            validate_csv(header+rows,{'chain':'A','units':[{'start':10,'end':20}]})

if __name__=='__main__':unittest.main()
