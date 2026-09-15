#!/usr/bin/env python3
"""Run the upstream 2xqh/A example and record bytes, environment and exit status."""
import argparse
import csv
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid

UNITS = '161_175,176_189,190_203,204_217,218_233,234_249,250_263,264_276,305_326,327_350,373_392,393_416'
REVISION = '8bb0c50bb0bf73c16cc22e7bd4e3991a326841c9'
INPUT_SHA256 = 'f674267d0ef4752a3d4da00497947bfc09f441a5c36d39593b72bc2ba390df0b'

def digest(path):
    return {'file': path.name, 'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--work', required=True, type=Path)
    parser.add_argument('--image', default='tesis/geometre:1.0-frozen')
    args = parser.parse_args()
    revision = subprocess.check_output(['git', '-C', str(args.source), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != REVISION:
        parser.error('source checkout does not match the reference revision')
    if subprocess.check_output(['git', '-C', str(args.source), 'status', '--porcelain'], text=True).strip():
        parser.error('source checkout must be clean')
    if hashlib.sha256(args.input.read_bytes()).hexdigest() != INPUT_SHA256:
        parser.error('input differs from the pinned 2xqh reference; review it as a new case')
    args.work.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(args.input, args.work / '2xqh.pdb')
    (args.work / 'units.json').write_text(json.dumps({'pdb': '2xqh', 'chain': 'A', 'units': UNITS, 'insertions': '351_372', 'frame': 'pdb-author-residue-number', 'source': f'https://github.com/BioComputingUP/GeomeTRe/blob/{REVISION}/README.md'}, indent=2) + '\n')
    inspect = json.loads(subprocess.check_output(['docker', 'image', 'inspect', args.image]))[0]
    image_id = inspect['Id']
    container = 'thesis-geometre-' + uuid.uuid4().hex
    command = ['docker', 'run', '--rm', '--name', container, '--network', 'none', '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--pids-limit', '128', '--cpus', '2', '--memory', '2g', '--tmpfs', '/tmp', '--user', f'{os.getuid()}:{os.getgid()}', '--mount', f'type=bind,src={args.work.resolve()},dst=/work', image_id, 'single', '/work/2xqh.pdb', 'A', '/work/geometry.csv', UNITS, '-ins_def', '351_372']
    record = {'schema_version': 1, 'operation': 'geometre.geometry', 'revision': revision, 'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'command': command, 'image': {'id': image_id, 'identity_kind': 'local-docker-image-id', 'repo_digests': inspect['RepoDigests'], 'architecture': inspect['Architecture'], 'os': inspect['Os']}, 'inputs': [digest(args.work / name) for name in ('2xqh.pdb', 'units.json')]}
    started = time.monotonic()
    try:
        result = subprocess.run(command, capture_output=True, timeout=120)
        record['exit_code'] = result.returncode
        (args.work / 'stdout.log').write_bytes(result.stdout)
        (args.work / 'stderr.log').write_bytes(result.stderr)
    except subprocess.TimeoutExpired as error:
        cleanup = subprocess.run(['docker', 'rm', '-f', container], capture_output=True, timeout=30)
        record.update(exit_code=None, error='timeout after 120 seconds')
        record['timeout_cleanup_exit_code'] = cleanup.returncode
        (args.work / 'stdout.log').write_bytes(error.stdout or b'')
        (args.work / 'stderr.log').write_bytes(error.stderr or b'')
    record['elapsed_seconds'] = round(time.monotonic() - started, 6)
    freeze = subprocess.check_output(['docker', 'run', '--rm', '--network', 'none', '--entrypoint', 'cat', image_id, '/opt/geometre-freeze.txt'])
    (args.work / 'environment.txt').write_bytes(freeze)
    errors = []
    try:
        rows = list(csv.DictReader((args.work / 'geometry.csv').open()))
        expected = [tuple(unit.split('_')) for unit in UNITS.split(',')]
        if [(row['unit_start'], row['unit_end']) for row in rows[:-2]] != expected:
            errors.append('unit boundaries or count changed')
        if [row['unit_start'] for row in rows[-2:]] != ['mean', 'std']:
            errors.append('summary rows missing')
        for row in rows:
            if row['pdb_id'] != '2xqh' or row['chain'] != 'A': errors.append('identity changed')
            for field in ('curvature', 'twist', 'pitch', 'yaw', 'tmscore'):
                if not math.isfinite(float(row[field])): errors.append(f'non-finite {field}')
            if not 0 <= float(row['tmscore']) <= 1: errors.append('TM-score outside [0,1]')
        record['unit_rows'] = len(rows) - 2
        record['summary_rows'] = 2
    except (OSError, ValueError, KeyError) as error:
        errors.append(str(error))
    record['validation_errors'] = errors
    record['passed'] = record.get('exit_code') == 0 and not errors
    record['outputs'] = [digest(path) for path in sorted(args.work.iterdir()) if path.name not in ('2xqh.pdb', 'units.json')]
    (args.work / 'reference.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))
    return 0 if record['passed'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
