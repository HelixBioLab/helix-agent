#!/usr/bin/env python3
"""Audit R3.2 closure against the still-installed F5 document."""
import hashlib
import json
import re
import subprocess
from pathlib import Path
from xml.etree import ElementTree as E
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[2]
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
SOURCE=Path('/home/webiwabou/Projects/Tesis.docx')
NEW=Path('/tmp/tesis-r32/render-v2/Tesis-final.docx')
PDF=NEW.with_suffix('.pdf')

def extract(path):
    with ZipFile(path) as z:
        r=E.fromstring(z.read('word/document.xml')); b=r.find('w:body',NS)
        ps=[''.join(t.text or '' for t in p.findall('.//w:t',NS)) for p in b.findall('w:p',NS)]
        refs=[p for p in ps[ps.index('Referencias')+1:ps.index('Anexos')] if p.strip() and not p.startswith('NOTA PARA EL AUTOR.')]
        images=sorted(hashlib.sha256(z.read(name)).hexdigest() for name in z.namelist() if name.startswith('word/media/'))
        return r,ps,refs,images

def main():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()=='73a40cea0d532c37c0d20ab7e454aa3d0c546f9350aa08017bbde4bdb7479c9e'
    old,oldps,oldrefs,oldimages=extract(SOURCE)
    r,ps,refs,images=extract(NEW)
    assert refs==oldrefs and len(refs)==99
    assert images==oldimages and len(r.findall('.//w:drawing',NS))==4
    assert len(r.findall('.//w:sectPr',NS))==3
    rows=[]
    for row in r.findall('.//w:tr',NS):
        cells=[''.join(t.text or '' for t in cell.findall('.//w:t',NS)) for cell in row.findall('w:tc',NS)]
        if cells and cells[0].startswith('R2.1.'):rows.append(cells)
    assert len(rows)==1 and all(rows[0])
    toc=next(''.join(t.text or '' for t in n.findall('.//w:t',NS)) for n in r.findall('.//w:sdt',NS) if 'Generalidades' in ''.join(t.text or '' for t in n.findall('.//w:t',NS)))
    for i in range(1,21):assert toc.count(f'A.{i}. ')==1
    for chapter in range(1,6):assert f'Capítulo {chapter}.' in toc
    assert 'Capítulo 4. Presentación de los resultados esperados' in toc
    assert 'Capítulo 5. Conclusiones y trabajos futuros' in toc
    for metric in json.loads((ROOT/'evaluation/trp/protocol.json').read_text())['metrics']:assert toc.count(metric['id']+'.')==1
    notes=[]
    for n in r.findall('.//w:p',NS):
        t=''.join(x.text or '' for x in n.findall('.//w:t',NS))
        if not t.startswith('NOTA PARA EL AUTOR.'):continue
        assert 'FF0000' in [c.get('{'+NS['w']+'}val') for c in n.findall('.//w:color',NS)]
        assert n.findall('.//w:i',NS)
        notes.append(t)
    output=NEW.with_suffix('.txt')
    subprocess.run(['pdftotext','-layout',str(PDF),str(output)],check=True)
    text=output.read_text(); pages=text.split('\f')[:-1]
    assert set(re.findall(r'Página \d+ de (\d+)',text))=={str(len(pages))}
    bbox=NEW.with_suffix('.bbox.html')
    subprocess.run(['pdftotext','-bbox-layout',str(PDF),str(bbox)],check=True)
    layout=E.parse(bbox); x={'x':'http://www.w3.org/1999/xhtml'}; footers=0
    for page in layout.findall('.//x:page',x):
        lines=page.findall('.//x:line',x)
        for footer in lines:
            value=' '.join(t.text or '' for t in footer.findall('x:word',x))
            if not re.fullmatch(r'(Página \d+ de \d+|A- \d+)',value):continue
            footers+=1; top=float(footer.get('yMin'))
            assert all(float(line.get('yMax')) < top-2 for line in lines if line is not footer)
    # The expanded TOC changes the number of preliminary pages. Derive the first
    # numbered body page from the actual PDF rather than retaining F5's count.
    blank=sum(not page.strip() for page in pages)
    first_numbered=next(i for i,page in enumerate(pages) if re.search(r'Página \d+ de \d+',page))
    body_blanks=sum(not page.strip() for page in pages[first_numbered:])
    assert footers==len(pages)-first_numbered-body_blanks
    expected=json.loads((ROOT/'docs/tesis/r32-documento.json').read_text())
    for section in expected['replace_sections']:
        for block in section['blocks']:assert block['text'] in ps
    for block in expected['appendix']+expected['engineering']:assert block['text'] in ps
    for item in expected['replace_paragraphs']:assert item['new'] in ps
    record={'phase':'R3.2','source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'docx':{'path':str(SOURCE),'sha256':hashlib.sha256(NEW.read_bytes()).hexdigest()},
        'pdf':{'path':'/home/webiwabou/Projects/Tesis-R3.2.pdf','sha256':hashlib.sha256(PDF.read_bytes()).hexdigest(),'pages':len(pages),'automatic_section_separator_pages':[i+1 for i,p in enumerate(pages) if not p.strip()]},
        'checks':{'bibliography_paragraphs_preserved':99,'active_figures_preserved':4,'sections_preserved':3,'red_italic_author_notes':len(notes),'r21_table_populated_after_render':True,'five_chapters':True,'chapter_4_and_5_titles_correct':True,'toc_has_21_results_once_each':True,'appendix_sections':20,'toc_duplicates':0,'footer_total_matches_pdf':True,'all_R32_sections_and_appendix_blocks_preserved':True},
        'visual_review_pages':[90,134,135], 'footer_layout':{'pages_checked':footers,'preliminary_pages':first_numbered,'text_collisions':0,'method':'PDF bounding boxes after reopening the exported DOCX; visual check of final new sections'}}
    (ROOT/'docs/tesis/evidencia/documento-r32.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(record,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
