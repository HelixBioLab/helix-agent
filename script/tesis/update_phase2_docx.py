#!/usr/bin/env python3
"""Apply F2 to the reviewed F1 Word, preserving document parts and all sections.

Writes a separate file. Fill table cells through valid w:p/w:r/w:t, then render and
verify the exported DOCX/PDF before installing it over the user's working document.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
from xml.dom import minidom
from zipfile import ZipFile

EXPECTED = '51f2d7e91a7befa1985da111e90ecdb5a15173c0708bc906dd77db3f0b5dcda6'
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
ROOT = Path(__file__).resolve().parents[2]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if hashlib.sha256(args.source.read_bytes()).hexdigest() != EXPECTED:
        parser.error('unexpected source revision; inspect before editing')
    if args.output.exists() or args.output.resolve() == args.source.resolve():
        parser.error('output must be a new file')
    content = json.loads((ROOT/'docs/tesis/fase2-documento.json').read_text())
    with ZipFile(args.source) as source:
        doc = minidom.parseString(source.read('word/document.xml'))
        body = doc.getElementsByTagName('w:body')[0]
        def text(node):
            return ''.join(t.firstChild.data for t in node.getElementsByTagName('w:t') if t.firstChild)
        def element(name, attrs=None, parent=None):
            node = doc.createElementNS(W, 'w:'+name)
            for key,value in (attrs or {}).items(): node.setAttributeNS(W,'w:'+key,str(value))
            if parent is not None: parent.appendChild(node)
            return node
        def paragraphs():
            return [p for p in body.childNodes if p.nodeType==p.ELEMENT_NODE and p.tagName=='w:p']
        def find(value):
            found = [p for p in paragraphs() if text(p)==value]
            if len(found)!=1: raise ValueError(f'expected unique paragraph: {value[:100]} ({len(found)})')
            return found[0]
        def replace(node,value):
            for child in list(node.childNodes):
                if child.nodeType==child.ELEMENT_NODE and child.tagName=='w:pPr': continue
                node.removeChild(child)
            run=element('r',parent=node)
            props=element('rPr',parent=run)
            element('rFonts',{'ascii':'Times New Roman','hAnsi':'Times New Roman'},props)
            element('sz',{'val':24},props)
            element('color',{'val':'000000'},props)
            t=element('t',parent=run); t.appendChild(doc.createTextNode(value))
            return node
        def paragraph(value,kind='paragraph',size=24):
            node=element('p'); props=element('pPr',parent=node)
            if kind in ('heading','subheading'):
                element('pStyle',{'val':'Heading2' if kind=='heading' else 'Heading3'},props)
                element('keepNext',parent=props)
                element('outlineLvl',{'val':1 if kind=='heading' else 2},props)
            element('spacing',{'before':160 if kind in ('heading','subheading') else 0,'after':120,'line':360,'lineRule':'auto'},props)
            element('jc',{'val':'left' if kind in ('heading','subheading') else 'both'},props)
            run=element('r',parent=node); rp=element('rPr',parent=run)
            element('rFonts',{'ascii':'Times New Roman','hAnsi':'Times New Roman'},rp)
            element('sz',{'val':size},rp)
            element('color',{'val':'FF0000' if kind=='note' else '000000'},rp)
            if kind=='note': element('i',parent=rp)
            if kind in ('heading','subheading'): element('b',parent=rp)
            t=element('t',parent=run); t.appendChild(doc.createTextNode(value))
            return node
        for item in content['replace_sections']:
            start=find(item['heading'])
            following=start.nextSibling
            removed=0
            while removed<item['paragraph_count']:
                next_node=following.nextSibling
                if following.nodeType==following.ELEMENT_NODE:
                    if following.tagName!='w:p': raise ValueError('unexpected non-paragraph within section')
                    body.removeChild(following); removed+=1
                following=next_node
            for block in item['blocks']:
                body.insertBefore(paragraph(block['text'],block.get('kind','paragraph')),following)
        for item in content['replace_paragraphs']:
            replace(find(item['old']),item['new'])
        # Repair the empty R2.1 cells with valid OOXML; F1 inserted runs directly in cells.
        matched=0
        for row in doc.getElementsByTagName('w:tr'):
            cells=[c for c in row.childNodes if c.nodeType==c.ELEMENT_NODE and c.tagName=='w:tc']
            if cells and text(cells[0]).startswith('R2.1.'):
                if len(cells)!=3: raise ValueError('unexpected R2.1 table width')
                for cell,value in zip(cells[1:],content['r21_cells']):
                    for child in list(cell.childNodes):
                        if child.nodeType==child.ELEMENT_NODE and child.tagName=='w:tcPr':continue
                        cell.removeChild(child)
                    cell.appendChild(paragraph(value,size=20))
                matched+=1
        if matched!=1:raise ValueError('R2.1 table row not found uniquely')
        anchor=find('Conclusiones y trabajos futuros')
        for block in content['engineering']:
            body.insertBefore(paragraph(block['text'],block.get('kind','paragraph')),anchor)
        section=next(n for n in body.childNodes if n.nodeType==n.ELEMENT_NODE and n.tagName=='w:sectPr')
        for block in content['appendix']:
            body.insertBefore(paragraph(block['text'],block.get('kind','paragraph')),section)
        # Include all 21 operational definitions in the Word, not just a repository link.
        protocol=json.loads((ROOT/'evaluation/trp/protocol.json').read_text())
        for metric in protocol['metrics']:
            body.insertBefore(paragraph(metric['id']+'. '+metric['measurement']),section)
            value=re.sub(r'\*\*(.*?)\*\*',r'\1',metric['acceptance']).replace('`','')
            body.insertBefore(paragraph('Criterio de aceptación: '+value),section)
        for block in content['appendix_after_metrics']:
            body.insertBefore(paragraph(block['text'],block.get('kind','paragraph')),section)
        # Writer's previous round-trip kept explicit TOC style mappings but removed
        # direct outline levels from older headings. Restore one consistent source.
        for node in doc.getElementsByTagName('w:p'):
            styles=node.getElementsByTagName('w:pStyle')
            if not styles: continue
            match=re.fullmatch(r'Heading([1-3])',styles[0].getAttribute('w:val'))
            if not match: continue
            props=node.getElementsByTagName('w:pPr')[0]
            levels=props.getElementsByTagName('w:outlineLvl')
            level=levels[0] if levels else element('outlineLvl',parent=props)
            level.setAttributeNS(W,'w:val',str(int(match.group(1))-1))
        # Preserve all original ZIP parts except document.xml; protect ZipInfo offsets.
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with ZipFile(args.output,'w') as output:
            for info in source.infolist():
                data=doc.toxml(encoding='UTF-8') if info.filename=='word/document.xml' else source.read(info.filename)
                output.writestr(copy.copy(info),data)
    with ZipFile(args.output) as output:
        written=minidom.parseString(output.read('word/document.xml'))
        for cell in written.getElementsByTagName('w:tc'):
            assert not any(c.nodeType==c.ELEMENT_NODE and c.tagName in ('w:r','w:t') for c in cell.childNodes)
        assert len(written.getElementsByTagName('w:sectPr'))==3
    print(json.dumps({'output':str(args.output),'sha256':hashlib.sha256(args.output.read_bytes()).hexdigest(),'protocol_metrics':len(protocol['metrics']),'r21_rows_filled':matched}))

if __name__=='__main__':
    main()
