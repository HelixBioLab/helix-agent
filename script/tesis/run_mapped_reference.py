#!/usr/bin/env python3
"""Run GeomeTRe with intervals produced by the explicit coordinate adapter."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import uuid

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'evaluation/trp/reference/coordinate-20260921'
mapping = json.loads((OUT/'mapping.json').read_text())
assert hashlib.sha256((OUT/'2xqh.pdb').read_bytes()).hexdigest() == mapping['targetSha256']
image = 'sha256:1dd91e70acb153a0bd9a51346fc001dd5025f851c9598697cdd37f07d9490b0a'
units = ','.join(f"{u['start']}_{u['end']}" for u in mapping['units'])
name = 'thesis-mapped-' + uuid.uuid4().hex
cmd = ['docker','run','--rm','--name',name,'--network','none','--read-only',
       '--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128',
       '--cpus','2','--memory','2g','--tmpfs','/tmp','--user',f'{os.getuid()}:{os.getgid()}',
       '--mount',f'type=bind,src={OUT},dst=/work',image,'single','/work/2xqh.pdb',
       mapping['chain'],'/work/geometry.csv',units,'-ins_def','351_372']
if (OUT/'geometry.csv').exists():
    raise SystemExit('Refusing to reuse previous geometry output')
try:
    run = subprocess.run(cmd, capture_output=True, timeout=120)
except subprocess.TimeoutExpired:
    subprocess.run(['docker','stop','--time','2',name], capture_output=True, timeout=10)
    raise
(OUT/'stdout.log').write_bytes(run.stdout)
(OUT/'stderr.log').write_bytes(run.stderr)
actual = (OUT/'geometry.csv').read_bytes() if (OUT/'geometry.csv').exists() else None
expected = (ROOT/'evaluation/trp/reference/geometre/geometry.csv').read_bytes()
record = {'date':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'kind':'development; same 2xqh family; not held-out evaluation',
          'command':cmd,'exit_code':run.returncode,'identical_reference_csv':actual == expected,
          'unit_count':len(mapping['units']),'mapped_residues':len(mapping['mapping']),
          'files':[{'path':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
                   for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='execution.json']}
(OUT/'execution.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k not in ('files','command')},indent=2))
raise SystemExit(0 if run.returncode==0 and actual==expected else 1)
