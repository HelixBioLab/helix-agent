#!/usr/bin/env python3
"""Check a copied TRP bundle and inject per-artifact faults using the trusted repo verifier."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[2]
VERIFY = ROOT / 'packages/bioinformatica/src/trp/verify_bundle.py.txt'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    # Trusted repository implementation; never import code supplied in the bundle.
    namespace = {'__name__': 'trusted_verifier'}
    exec(compile(VERIFY.read_text(), str(VERIFY), 'exec'), namespace)
    verify = namespace['verify']
    anchor = hashlib.sha256((args.bundle / 'manifest.json').read_bytes()).hexdigest()
    checks = []
    def rejected(name, action):
        try:
            action()
        except (OSError, ValueError, KeyError, TypeError, RecursionError):
            checks.append({'case': name, 'detected': True})
        else:
            checks.append({'case': name, 'detected': False})
    with tempfile.TemporaryDirectory(prefix='trp-cold-audit-') as temp:
        copy = Path(temp) / 'copied'
        shutil.copytree(args.bundle, copy)
        baseline = verify(copy, anchor)
        manifest_bytes = (copy/'manifest.json').read_bytes()
        manifest = json.loads(manifest_bytes)
        for entry in manifest['files']:
            target = copy / entry['path']
            raw = target.read_bytes()
            target.unlink()
            rejected('missing:' + entry['path'], lambda: verify(copy, anchor))
            target.write_bytes(bytes([raw[0] ^ 1]) + raw[1:] if raw else b'altered')
            rejected('changed:' + entry['path'], lambda: verify(copy, anchor))
            target.write_bytes(raw)
        for name in ['../escape', '/tmp/escape', 'run/../escape', 'C:\\escape', 'run//source.pdb']:
            changed = json.loads(manifest_bytes)
            changed['files'][0]['path'] = name
            (copy/'manifest.json').write_text(json.dumps(changed))
            rejected('path:' + name, lambda: verify(copy))
        (copy/'manifest.json').write_bytes(manifest_bytes)
        (copy/'unlisted.txt').write_text('unexpected')
        rejected('unlisted-file', lambda: verify(copy, anchor))
        (copy/'unlisted.txt').unlink()
        target = copy/'run/source.pdb'; raw = target.read_bytes(); target.unlink()
        target.symlink_to(args.bundle.resolve()/'run/source.pdb')
        rejected('external-symlink', lambda: verify(copy, anchor))
        target.unlink(); target.write_bytes(raw)
        rejected('wrong-anchor', lambda: verify(copy, '0'*64))
        restored = verify(copy, anchor)
    report = {'kind': 'engineering-fault-injection; not held-out evaluation',
              'baseline': baseline, 'restored': restored, 'injected': len(checks),
              'detected': sum(c['detected'] for c in checks), 'checks': checks,
              'verifierSha256': hashlib.sha256(VERIFY.read_bytes()).hexdigest()}
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'checks'}, indent=2))
    return 0 if all(c['detected'] for c in checks) else 1


if __name__ == '__main__':
    raise SystemExit(main())
