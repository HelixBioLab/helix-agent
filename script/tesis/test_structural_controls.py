"""F5 development checks using real source files and labelled perturbations."""
import copy
import hashlib
import json
import unittest
import gemmi
from run_structural_reference import inspect, requests

REAL = dict(requests())

def cif_change(request, category, change):
    request = copy.deepcopy(request)
    doc=gemmi.cif.read_string(request['structure'])
    block=doc.sole_block()
    data=block.get_mmcif_category(category)
    change(data)
    block.set_mmcif_category(category,data)
    request['structure']=doc.as_string()
    return request

def verdict(request, control):
    return next(c for c in inspect(request)['checks'] if c['id']==control)

class StructuralControls(unittest.TestCase):
    def test_real_experimental_author_label_mapping(self):
        result=inspect(REAL['experimental'])
        self.assertTrue(result['summary']['mechanicalAdmission'])
        row=next(r for r in result['mapping'] if r['auth']=='161')
        self.assertNotEqual(row['label'],161)
        self.assertEqual(result['provenance']['confidenceScale'],'Bfactor_A2')

    def test_same_number_wrong_frame_loses_coverage(self):
        r=copy.deepcopy(REAL['experimental']);r['options']['frame']='label_seq_id'
        self.assertEqual(verdict(r,'element-coverage')['status'],'fail')

    def test_explicit_label_mapping_preserves_residues(self):
        original=inspect(REAL['experimental'])
        by_auth={r['auth']:r['label'] for r in original['mapping']}
        r=copy.deepcopy(REAL['experimental']);r['options']['frame']='label_seq_id'
        r['options']['units']=[{'start':by_auth[str(u['start'])],'end':by_auth[str(u['end'])]} for u in r['options']['units']]
        result=inspect(r)
        self.assertTrue(result['summary']['mechanicalAdmission'])
        self.assertEqual(verdict(r,'element-coverage')['value']['requested'],verdict(REAL['experimental'],'element-coverage')['value']['requested'])

    def test_real_afdb_bound_pae(self):
        r=inspect(REAL['alphafold'])
        self.assertEqual(r['provenance']['confidenceScale'],'pLDDT_0_100')
        self.assertEqual(verdict(REAL['alphafold'],'interunit-pae')['status'],'pass')
        self.assertEqual(r['summary']['biologicalValidity'],'not_established')

    def test_unknown_producer_not_guessed_from_B(self):
        r=cif_change(REAL['alphafold'],'_software.',lambda c:c['name'].__setitem__(0,'Unknown'))
        self.assertEqual(verdict(r,'confidence-scale')['status'],'not_evaluable')
        self.assertFalse(inspect(r)['summary']['mechanicalAdmission'])

    def test_confidence_values_disagree_with_local_metric(self):
        def change(c):
            i=c['label_atom_id'].index('CA'); c['B_iso_or_equiv'][i]='0.95'
        r=cif_change(REAL['alphafold'],'_atom_site.',change)
        self.assertEqual(verdict(r,'confidence-scale')['status'],'fail')

    def test_inverted_filter_rejected(self):
        r=copy.deepcopy(REAL['alphafold']);r['options']['filter']={'scale':'pLDDT_0_100','operator':'<=','threshold':70}
        check=verdict(r,'filter-direction')
        self.assertEqual(check['status'],'fail');self.assertEqual(check['threshold']['operator'],'>=')

    def test_correct_filter_checks_without_trimming(self):
        r=copy.deepcopy(REAL['alphafold']);r['options']['filter']={'scale':'pLDDT_0_100','operator':'>=','threshold':70}
        self.assertEqual(verdict(r,'filter-direction')['status'],'pass')
        self.assertEqual(len(inspect(r)['mapping']),142)

    def test_scale_cannot_be_silently_normalized(self):
        r=copy.deepcopy(REAL['alphafold']);r['options']['filter']={'scale':'pLDDT_0_1','operator':'>=','threshold':.7}
        self.assertEqual(verdict(r,'filter-direction')['status'],'fail')

    def test_experimental_B_filter_wrong_direction(self):
        r=copy.deepcopy(REAL['experimental']);r['options']['filter']={'scale':'Bfactor_A2','operator':'>=','threshold':30}
        self.assertEqual(verdict(r,'filter-direction')['status'],'fail')

    def test_missing_pae_is_not_evaluable(self):
        r=copy.deepcopy(REAL['alphafold']);del r['pae']
        self.assertEqual(verdict(r,'interunit-pae')['status'],'not_evaluable')
        self.assertFalse(inspect(r)['summary']['mechanicalAdmission'])

    def test_missing_api_is_not_evaluable(self):
        r=copy.deepcopy(REAL['alphafold']);del r['api']
        self.assertEqual(verdict(r,'interunit-pae')['status'],'not_evaluable')

    def test_pae_asymmetric_reverse_block(self):
        r=copy.deepcopy(REAL['alphafold']);r['pae'][0]['predicted_aligned_error'][20][9]=30
        c=verdict(r,'interunit-pae');self.assertEqual(c['status'],'fail')
        self.assertEqual(c['value']['pairs'][0]['reverseMax'],30)

    def test_wrong_pae_shape(self):
        r=copy.deepcopy(REAL['alphafold']);r['pae'][0]['predicted_aligned_error'].pop()
        self.assertEqual(verdict(r,'interunit-pae')['status'],'fail')

    def test_pae_negative_value(self):
        r=copy.deepcopy(REAL['alphafold']);r['pae'][0]['predicted_aligned_error'][0][1]=-1
        self.assertEqual(verdict(r,'interunit-pae')['status'],'fail')

    def test_wrong_sequence_even_same_length(self):
        r=copy.deepcopy(REAL['alphafold']);r['api'][0]['sequence']='A'*142
        self.assertEqual(verdict(r,'interunit-pae')['status'],'fail')

    def test_wrong_version_url(self):
        r=copy.deepcopy(REAL['alphafold']);r['options']['paeUrl']=r['options']['paeUrl'].replace('v6','v5')
        self.assertEqual(verdict(r,'interunit-pae')['status'],'fail')

    def test_wrong_chain_api(self):
        r=copy.deepcopy(REAL['alphafold']);r['api'][0]['chainId']='B'
        self.assertEqual(verdict(r,'interunit-pae')['status'],'fail')

    def test_wrong_entry_same_sequence(self):
        r=copy.deepcopy(REAL['alphafold']);r['api'][0]['entryId']='AF-WRONG-F1'
        self.assertEqual(verdict(r,'interunit-pae')['status'],'fail')

    def test_no_implicit_multiple_entry_choice(self):
        r=copy.deepcopy(REAL['alphafold']);r['api'].append(copy.deepcopy(r['api'][0]))
        self.assertEqual(verdict(r,'interunit-pae')['status'],'fail')

    def test_local_confidence_threshold_is_separate(self):
        r=copy.deepcopy(REAL['alphafold']);r['options']['plddtMin']=100
        self.assertEqual(verdict(r,'interunit-pae')['status'],'fail')

    def test_duplicate_CA_never_first_wins(self):
        def change(c):
            i=c['label_atom_id'].index('CA')
            for values in c.values(): values.append(values[i])
        r=cif_change(REAL['experimental'],'_atom_site.',change)
        self.assertEqual(verdict(r,'residue-frame')['status'],'fail')

    def test_author_insertion_code_refused(self):
        def change(c):
            i=next(i for i in range(len(c['auth_seq_id'])) if c['auth_seq_id'][i]=='161' and c['label_atom_id'][i]=='CA')
            c['pdbx_PDB_ins_code'][i]='A'
        r=cif_change(REAL['experimental'],'_atom_site.',change)
        self.assertEqual(verdict(r,'residue-frame')['status'],'fail')

    def test_alternate_CA_refused(self):
        def change(c):
            i=next(i for i in range(len(c['auth_seq_id'])) if c['auth_seq_id'][i]=='161' and c['label_atom_id'][i]=='CA')
            c['label_alt_id'][i]='B'
        r=cif_change(REAL['experimental'],'_atom_site.',change)
        self.assertEqual(verdict(r,'residue-frame')['status'],'fail')

    def test_missing_CA_does_not_disappear_silently(self):
        def change(c):
            i=next(i for i in range(len(c['auth_seq_id'])) if c['auth_seq_id'][i]=='161' and c['label_atom_id'][i]=='CA')
            for values in c.values(): values.pop(i)
        r=cif_change(REAL['experimental'],'_atom_site.',change)
        c=verdict(r,'element-coverage');self.assertEqual(c['status'],'fail');self.assertIn('161',c['value']['missing'])

    def test_nonfinite_coordinate(self):
        def change(c):
            i=next(i for i in range(len(c['auth_seq_id'])) if c['auth_seq_id'][i]=='161' and c['label_atom_id'][i]=='CA')
            c['Cartn_x'][i]='NaN'
        r=cif_change(REAL['experimental'],'_atom_site.',change)
        self.assertEqual(verdict(r,'element-coverage')['status'],'fail')

    def test_overlapping_units(self):
        r=copy.deepcopy(REAL['experimental']);r['options']['units'][1]['start']=175
        self.assertEqual(verdict(r,'element-coverage')['status'],'fail')

    def test_terminal_histidine_signal_is_review_not_auto_trim(self):
        def change(c):
            for i,seq in enumerate(c['label_seq_id']):
                if seq and int(seq)<=6: c['label_comp_id'][i]='HIS'
        r=cif_change(REAL['alphafold'],'_atom_site.',change);r['options']['units'][0]={'start':1,'end':10}
        c=verdict(r,'construct-tags');self.assertEqual(c['status'],'fail');self.assertTrue(c['value']['selectedTerminalPolyHis'])
        self.assertEqual(len(inspect(r)['mapping']),142)

    def test_assembly_never_certified_by_high_confidence(self):
        self.assertEqual(verdict(REAL['alphafold'],'assembly-annotation')['status'],'not_evaluable')

    def test_pratt_failure_not_certified_by_pae_pass(self):
        self.assertEqual(verdict(REAL['alphafold'],'interunit-pae')['status'],'pass')
        self.assertEqual(verdict(REAL['alphafold'],'fold-plausibility')['status'],'not_evaluable')

    def test_independent_boundaries_equal_and_disagree(self):
        r=copy.deepcopy(REAL['experimental']);o=r['options']
        o['reference']={'structureSha256':hashlib.sha256(r['structure'].encode()).hexdigest(),'model':1,'chain':'A','frame':o['frame'],'units':copy.deepcopy(o['units']),'tolerance':0,'source':'synthetic development comparator; not reviewed biological truth'}
        self.assertEqual(verdict(r,'unit-boundaries')['status'],'pass')
        o['reference']['units'][0]['end']-=1
        self.assertEqual(verdict(r,'unit-boundaries')['status'],'fail')
        o['reference']['frame']='label_seq_id'
        self.assertFalse(verdict(r,'unit-boundaries')['value']['identityAndFrameMatch'])

    def test_multiblock_cif_refused(self):
        r=copy.deepcopy(REAL['experimental']);r['structure']+='\ndata_extra\n_entry.id OTHER\n'
        with self.assertRaisesRegex(ValueError,'cif-block'): inspect(r)

    def test_malformed_cif_refused(self):
        r=copy.deepcopy(REAL['experimental']);r['structure']='not a cif'
        with self.assertRaises(ValueError): inspect(r)

    def test_limits_and_invalid_intervals(self):
        for bad in ({'start':1,'end':100_000},{'start':1.5,'end':20},{'start':20,'end':1}):
            r=copy.deepcopy(REAL['experimental']);r['options']['units'][0]=bad
            with self.assertRaises(ValueError): inspect(r)

    def test_every_negative_has_value_threshold_reason(self):
        r=copy.deepcopy(REAL['experimental']);r['options']['units'][0]={'start':1,'end':20}
        for c in inspect(r)['checks']:
            if c['status']=='fail':
                self.assertIsNotNone(c['value']);self.assertIsNotNone(c['threshold']);self.assertTrue(c['reason'])

if __name__=='__main__': unittest.main(verbosity=2)
