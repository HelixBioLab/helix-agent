#!/usr/bin/env python3
"""Collect available technical freeze artifacts; never finalize a campaign."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'evaluation/trp/f6-readiness-20260921/technical-draft'

def dump(name,value):
    p=OUT/name;p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');return p

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    catalog=json.loads((ROOT/'packages/helix/src/trp/catalog.json').read_text())
    draft=json.loads((ROOT/'evaluation/trp/freeze.template.json').read_text())
    draft.update(status='draft_not_frozen',catalog_version=catalog['version'],
                 code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    memory=next(line for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemTotal:'))
    hardware=dump('hardware.json',{'observed_at':now,'platform':platform.platform(),
                  'logical_cpus':os.cpu_count(),'memory_total_bytes':int(memory.split()[1])*1024,
                  'workspace_free_bytes':shutil.disk_usage(ROOT).free,
                  'kind':'local workstation observation; not an exclusive reservation or cluster'})
    images=[]
    for name in ['tesis/geometre:nextflow-f3','tesis/strpsearch:candidate-f3']:
        raw=json.loads(subprocess.check_output(['docker','image','inspect',name],text=True))[0]
        images.append({'name':name,'id':raw['Id'],'architecture':raw['Architecture'],
                       'repo_digests':raw['RepoDigests'],'identity_kind':'observed local image digest'})
    image_file=dump('images.json',{'observed_at':now,'images':images})
    licenses=dump('catalog-sources.json',{'catalog_version':catalog['version'],
        'entries':[{'id':e['id'],'status':e['status'],'source':e['source']} for e in catalog['entries']],
        'scope':'Catalog artifacts only; held-out corpus sources must be added before freezing'})
    dependency=dump('dependencies.json',{'files':[{'path':p,'sha256':hashlib.sha256((ROOT/p).read_bytes()).hexdigest()}
        for p in ('bun.lock','script/tesis/requirements-structural.txt','packages/helix/package.json')],
        'scope':'Lock files and inspected images; full evaluated environment remains subject to final freeze'})
    artifacts={'protocol_sha256':ROOT/'evaluation/trp/protocol.json',
               'catalog_sha256':ROOT/'packages/helix/src/trp/catalog.json',
               'annotation_guide_sha256':ROOT/'evaluation/trp/ANNOTATION.md',
               'hardware_inventory_sha256':hardware,'image_manifest_sha256':image_file,
               'dependency_lock_sha256':dependency,'source_and_license_manifest_sha256':licenses}
    for key,p in artifacts.items():draft[key]=hashlib.sha256(p.read_bytes()).hexdigest()
    dump('freeze.draft.json',draft)
    dump('artifacts.json',{k:str(p.relative_to(ROOT)) for k,p in artifacts.items()})
    print(json.dumps({'status':draft['status'],'technical_artifacts_recorded':len(artifacts),
                      'still_required':['held-out corpus and partitions','scientific corpus review',
                        'independent annotation where applicable','model and API budget for language',
                        'final committed configuration and freeze approval']},indent=2))

if __name__=='__main__':main()
