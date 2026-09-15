#!/usr/bin/env python3
"""Inventory downloaded Pratt supplements, preserving sparse spreadsheet columns."""
import hashlib
import json
import re
from pathlib import Path
from xml.etree import ElementTree as E
from zipfile import ZipFile
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'evaluation/trp/reference/structural-f5/pratt'

def main():
    with ZipFile(BASE/'mmc2.xlsx') as z:
        ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        strings=[''.join(x.itertext()) for x in E.fromstring(z.read('xl/sharedStrings.xml'))]
        rows=[]
        for row in E.fromstring(z.read('xl/worksheets/sheet1.xml')).findall('.//s:row',ns):
            cells={}
            for cell in row:
                column=re.match('[A-Z]+',cell.get('r')).group()
                v=cell.find('s:v',ns); value=v.text if v is not None else ''
                cells[column]=strings[int(value)] if cell.get('t')=='s' and value else value
            if row.get('r')=='1': continue
            if not cells.get('A'): continue
            rows.append({'sheetRow':int(row.get('r')),'identifier':cells.get('A'),'repeatSequence':cells.get('B'),
                         'publishedAF2pLDDT':float(cells['E']),'publishedAF2Fold':cells.get('F'),
                         'coordinatesInDownloadedSupplements':False,'paeInDownloadedSupplements':False,
                         'screeningStatus':'not_evaluable','reason':'Published metadata do not supply the exact original coordinate and PAE bytes; no new prediction substitutes them.'})
    with ZipFile(BASE/'mmc1.docx') as z:
        r=E.fromstring(z.read('word/document.xml'));ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        paragraphs=[''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in r.findall('.//w:p',ns)]
        (BASE/'supplement-text.txt').write_text('\n'.join(paragraphs)+'\n')
        links=[]
        for name in z.namelist():
            if name.endswith('.rels'):
                links.extend(n.get('Target') for n in E.fromstring(z.read(name)) if n.get('TargetMode')=='External')
        embedded=[name for name in z.namelist() if name.startswith('word/embeddings/')]
    inventory=json.loads((BASE/'supplement-inventory.json').read_text())
    coordinate_files=[f['path'] for f in inventory if f['path'].lower().endswith(('.pdb','.cif','.mmcif','.json','.zip','.tar','.gz'))]
    assert not coordinate_files and not embedded
    record={'date':'2026-09-15','doi':'10.1016/j.csbj.2025.01.016','license':'CC BY 4.0',
            'retrieval':'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC11795689/supplementaryFiles',
            'metadataRows':len(rows),'downloadedCoordinateFiles':coordinate_files,'embeddedObjects':embedded,'docxExternalLinks':links,
            'modelsEvaluated':0,'sensitivity':None,'specificity':None,
            'scope':'Recoverability audit of the downloaded public article/supplement package only; not proof that author-held data do not exist. Rows are predictions, not 78 independently verified failure labels.',
            'nextStep':'Obtain original published model/PAE files and independent failure labels before T-STRUCT evaluation. No messages to authors sent.',
            'sources':[{'path':name,'sha256':hashlib.sha256((BASE/name).read_bytes()).hexdigest()} for name in ('pratt.xml','mmc1.docx','mmc2.xlsx','supplement-inventory.json')],
            'cases':rows}
    (BASE/'recoverability.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({k:record[k] for k in ('metadataRows','modelsEvaluated','downloadedCoordinateFiles','sensitivity','specificity')}))

if __name__=='__main__': main()
