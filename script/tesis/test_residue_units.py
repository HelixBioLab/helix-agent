"""Development tests using deposited 2xqh coordinates and labelled perturbations."""
import json
from pathlib import Path
import unittest
import gemmi
from map_residue_units import convert

ROOT = Path(__file__).resolve().parents[2]
CIF = (ROOT/'evaluation/trp/reference/structural-f5/experimental/2xqh.cif').read_text()
PDB = (ROOT/'evaluation/trp/reference/geometre/2xqh.pdb').read_text()
UNITS = json.loads((ROOT/'evaluation/trp/development/f3-reference-spec.json').read_text())['units']['value']['ranges']
REPORT = json.loads((ROOT/'evaluation/trp/reference/structural-f5/experimental/report.json').read_text())
BY_AUTH = {int(r['auth']): r['label'] for r in REPORT['mapping']}
LABELS = [{'start': BY_AUTH[u['start']], 'end': BY_AUTH[u['end']]} for u in UNITS]


class ResidueUnits(unittest.TestCase):
    def test_real_mapping_recovers_all_supplied_units(self):
        result = convert(CIF, PDB, 'A', 1, LABELS)
        self.assertEqual(result['units'], UNITS)
        self.assertEqual(len(result['mapping']), sum(u['end']-u['start']+1 for u in UNITS))

    def test_same_numbers_in_wrong_frame_rejected(self):
        with self.assertRaises(ValueError):
            convert(CIF, PDB, 'A', 1, UNITS)

    def test_same_entry_but_changed_coordinates_rejected(self):
        lines = PDB.splitlines()
        for i, line in enumerate(lines):
            if line.startswith('ATOM  ') and line[12:16].strip() == 'CA' and line[22:26].strip() == str(UNITS[0]['start']):
                lines[i] = line[:30] + f'{999.0:8.3f}' + line[38:]
                break
        with self.assertRaisesRegex(ValueError, 'coordinate-mismatch'):
            convert(CIF, '\n'.join(lines)+'\n', 'A', 1, LABELS)

    def test_wrong_entry_rejected(self):
        lines = PDB.splitlines()
        lines = [l[:62]+'9ZZZ'+l[66:] if l.startswith('HEADER') else l for l in lines]
        with self.assertRaisesRegex(ValueError, 'entry-mismatch'):
            convert(CIF, '\n'.join(lines)+'\n', 'A', 1, LABELS)

    def test_missing_interior_residue_rejected(self):
        missing = str(UNITS[0]['start']+1)
        altered = '\n'.join(l for l in PDB.splitlines() if not (l.startswith('ATOM  ') and l[22:26].strip()==missing))+'\n'
        with self.assertRaisesRegex(ValueError, 'missing-or-ambiguous'):
            convert(CIF, altered, 'A', 1, LABELS)

    def test_duplicate_residue_rejected(self):
        line = next(l for l in PDB.splitlines() if l.startswith('ATOM  ') and l[12:16].strip()=='CA' and l[22:26].strip()==str(UNITS[0]['start']))
        with self.assertRaisesRegex(ValueError, 'missing-or-ambiguous'):
            convert(CIF, PDB.replace(line, line+'\n'+line), 'A', 1, LABELS)

    def test_wrong_chain_rejected(self):
        with self.assertRaises(ValueError):
            convert(CIF, PDB, 'Z', 1, LABELS)

    def test_noncontiguous_author_numbering_rejected(self):
        doc = gemmi.cif.read_string(CIF)
        block = doc.sole_block()
        atoms = block.get_mmcif_category('_atom_site.')
        author = str(UNITS[0]['start']+1)
        for i, value in enumerate(atoms['auth_seq_id']):
            if value == author and atoms['auth_asym_id'][i] == 'A':
                atoms['auth_seq_id'][i] = '999'
        block.set_mmcif_category('_atom_site.', atoms)
        lines = [l[:22]+f'{999:4d}'+l[26:] if l.startswith('ATOM  ') and l[22:26].strip()==author and l[21]=='A' else l for l in PDB.splitlines()]
        with self.assertRaisesRegex(ValueError, 'noncontiguous-author-unit'):
            convert(doc.as_string(), '\n'.join(lines)+'\n', 'A', 1, LABELS)


if __name__ == '__main__':
    unittest.main()
