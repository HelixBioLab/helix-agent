#!/usr/bin/env python3
"""Run offline F5 development references; never a held-out evaluation."""
import hashlib
import json
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'evaluation/trp/reference/structural-f5'
ENGINE = ROOT/'packages/helix/src/trp/inspect_structure.py.txt'
inspect = runpy.run_path(str(ENGINE))['inspect']

def requests():
    spec=json.loads((ROOT/'evaluation/trp/development/f3-reference-spec.json').read_text())
    options={'format':'mmcif','chain':'A','model':1,'frame':'auth_seq_id','units':spec['units']['value']['ranges']}
    yield 'experimental', {'structure':(BASE/'experimental/2xqh.cif').read_text(),'options':options}
    yield 'alphafold', {'structure':(BASE/'alphafold/afdb.cif').read_text(),
        'options':json.loads((ROOT/'evaluation/trp/development/f5-afdb-options.json').read_text()),
        'api':json.loads((BASE/'alphafold/afdb-api.json').read_text()),'pae':json.loads((BASE/'alphafold/pae.json').read_text())}

if __name__=='__main__':
    records=[]
    for name, request in requests():
        report=inspect(request)
        (BASE/name/'report.json').write_text(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+'\n')
        print(name,json.dumps(report['summary']))
        records.append({'case':name,'parser':report['provenance']['parser'],'summary':report['summary']})
    files=[{'path':p.relative_to(BASE).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
           for p in sorted(BASE.rglob('*')) if p.is_file() and p.name not in ('engineering-reference.json','README.md')]
    record={'phase':'F5','date':'2026-09-15','kind':'development; not R5.4','engineSha256':hashlib.sha256(ENGINE.read_bytes()).hexdigest(),'references':records,'files':files}
    (BASE/'engineering-reference.json').write_text(json.dumps(record,indent=2)+'\n')
