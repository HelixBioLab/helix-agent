#!/usr/bin/env python3
"""Explicit mmCIF label-to-author mapping for the existing PDB geometry route.

Offline preprocessing, not automatic detector admission or SIFTS alignment.
Checks every residue (not just endpoints) and binds the map to both inputs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / 'packages/helix/src/trp/inspect_structure.py.txt'


def convert(cif, pdb, chain, model, units):
    engine = runpy.run_path(str(ENGINE))
    options = {'format': 'mmcif', 'chain': chain, 'model': model,
               'frame': 'label_seq_id', 'units': units}
    report = engine['inspect']({'structure': cif, 'options': options})
    if not report['summary']['mechanicalAdmission']:
        raise ValueError('mmcif-not-admitted:' + ','.join(report['summary']['blocking']))
    if report['provenance']['confidenceScale'] != 'Bfactor_A2':
        raise ValueError('experimental-route-only')
    snapshot = engine['pdb_snapshot'](pdb, options)
    if snapshot['entry'].lower() != report['provenance']['entry'].lower():
        raise ValueError('entry-mismatch')
    targets = {}
    for row in snapshot['rows']:
        targets.setdefault(row['auth'], []).append(row)
    labels = {row['label']: row for row in report['mapping']}
    converted, audit = [], []
    for unit in units:
        authors = []
        for label in range(unit['start'], unit['end'] + 1):
            row = labels[label]
            try:
                author = int(row['auth'])
            except ValueError:
                raise ValueError('noninteger-author') from None
            if author <= 0:
                raise ValueError('nonpositive-author')
            matches = targets.get(row['auth'], [])
            if len(matches) != 1:
                raise ValueError('missing-or-ambiguous-pdb-residue')
            target = matches[0]
            if target['alt'] or target['insertion'] or target['name'] != row['name']:
                raise ValueError('pdb-residue-identity-mismatch')
            if any(x is None or y is None or abs(x-y) > 0.0011
                   for x, y in zip(row['xyz'], target['xyz'])):
                raise ValueError('pdb-coordinate-mismatch')
            if row['b'] is None or target['b'] is None or abs(row['b']-target['b']) > 0.011:
                raise ValueError('pdb-displacement-mismatch')
            authors.append(author)
            audit.append({'label': label, 'author': author, 'chain': chain,
                          'residue': row['name']})
        if authors != list(range(authors[0], authors[-1]+1)):
            raise ValueError('noncontiguous-author-unit')
        converted.append({'start': authors[0], 'end': authors[-1]})
    output_options = {**options, 'format': 'pdb', 'frame': 'auth_seq_id', 'units': converted}
    target_report = engine['inspect']({'structure': pdb, 'options': output_options})
    if not target_report['summary']['mechanicalAdmission']:
        raise ValueError('pdb-not-admitted')
    return {'version': 'trp-coordinate-adapter/1.0.0',
            'sourceSha256': hashlib.sha256(cif.encode()).hexdigest(),
            'targetSha256': hashlib.sha256(pdb.encode()).hexdigest(),
            'engineSha256': hashlib.sha256(ENGINE.read_bytes()).hexdigest(),
            'chain': chain, 'model': model, 'sourceFrame': 'label_seq_id',
            'targetFrame': 'pdb-author', 'inputUnits': units, 'units': converted,
            'mapping': audit, 'biologicalValidity': 'not_established',
            'limitations': ['Experimental PDB route only', 'No SIFTS/UniProt inference',
                            'All requested residues must have unique matching CA coordinates']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('cif', type=Path)
    p.add_argument('pdb', type=Path)
    p.add_argument('units', type=Path, help='JSON array in label_seq_id coordinates')
    p.add_argument('output', type=Path)
    p.add_argument('--chain', required=True)
    p.add_argument('--model', type=int, default=1)
    args = p.parse_args()
    result = convert(args.cif.read_text(), args.pdb.read_text(), args.chain,
                     args.model, json.loads(args.units.read_text()))
    with args.output.open('x') as f:
        json.dump(result, f, indent=2, allow_nan=False)
        f.write('\n')


if __name__ == '__main__':
    main()
