#!/usr/bin/env python3
"""Apply reviewed F3 content to the exact F2 Word revision; write a new DOCX."""
import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
from xml.dom import minidom
from zipfile import ZipFile

EXPECTED = 'b665e59133214ff83144e0c2532fd63226d384ef465ce523f42f54887f81e54b'
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
    content = json.loads((ROOT/'docs/tesis/fase3-documento.json').read_text())
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
        def find(value):
            found = [p for p in body.childNodes if getattr(p,'tagName','')=='w:p' and text(p)==value]
            if len(found)!=1: raise ValueError(f'expected unique paragraph: {value[:100]} ({len(found)})')
            return found[0]
        def paragraph(value,kind='paragraph'):
            node=element('p'); props=element('pPr',parent=node)
            if kind in ('heading','subheading'):
                element('pStyle',{'val':'Heading2' if kind=='heading' else 'Heading3'},props)
                element('keepNext',parent=props)
                element('outlineLvl',{'val':1 if kind=='heading' else 2},props)
            element('spacing',{'before':160 if kind in ('heading','subheading') else 0,'after':120,'line':360,'lineRule':'auto'},props)
            element('jc',{'val':'left' if kind in ('heading','subheading') else 'both'},props)
            run=element('r',parent=node); rp=element('rPr',parent=run)
            element('rFonts',{'ascii':'Times New Roman','hAnsi':'Times New Roman'},rp)
            element('sz',{'val':24},rp)
            element('color',{'val':'FF0000' if kind=='note' else '000000'},rp)
            if kind=='note': element('i',parent=rp)
            if kind in ('heading','subheading'): element('b',parent=rp)
            t=element('t',parent=run); t.appendChild(doc.createTextNode(value))
            return node
        for item in content['replace_sections']:
            start=find(item['heading']); following=start.nextSibling; removed=0
            while removed<item['paragraph_count']:
                if following is None: raise ValueError('section exceeds document')
                next_node=following.nextSibling
                if following.nodeType==following.ELEMENT_NODE:
                    if following.tagName!='w:p': raise ValueError('unexpected non-paragraph within section')
                    body.removeChild(following); removed+=1
                following=next_node
            for block in item['blocks']:
                body.insertBefore(paragraph(block['text'],block.get('kind','paragraph')),following)
        for item in content['replace_paragraphs']:
            previous=find(item['old']); replacement=paragraph(item['new'])
            body.replaceChild(replacement,previous)
        anchor=find('Conclusiones y trabajos futuros')
        for block in content['engineering']:
            body.insertBefore(paragraph(block['text'],block.get('kind','paragraph')),anchor)
        section=next(n for n in body.childNodes if getattr(n,'tagName','')=='w:sectPr')
        for block in content['appendix']:
            body.insertBefore(paragraph(block['text'],block.get('kind','paragraph')),section)
        for node in doc.getElementsByTagName('w:p'):
            styles=node.getElementsByTagName('w:pStyle')
            if not styles: continue
            match=re.fullmatch(r'Heading([1-3])',styles[0].getAttribute('w:val'))
            if not match: continue
            props=node.getElementsByTagName('w:pPr')[0]
            for level in list(props.getElementsByTagName('w:outlineLvl')):props.removeChild(level)
            element('outlineLvl',{'val':int(match.group(1))-1},props)
        with ZipFile(args.output,'w') as output:
            for info in source.infolist():
                data=doc.toxml(encoding='UTF-8') if info.filename=='word/document.xml' else source.read(info.filename)
                output.writestr(copy.copy(info),data)
    print(json.dumps({'output':str(args.output),'sha256':hashlib.sha256(args.output.read_bytes()).hexdigest(),'phase':'F3'},indent=2))

if __name__=='__main__': main()
