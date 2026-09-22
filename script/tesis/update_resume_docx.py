#!/usr/bin/env python3
"""Apply the author-approved search-section removal and measured resumption results.

Preserves every ZIP part except document.xml; refuses unexpected boundaries.
Writes a review copy, never overwrites the input.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import xml.etree.ElementTree as E
import zipfile

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS = {'w':W}
def q(s): return '{'+W+'}'+s
def text(el): return ''.join(x.text or '' for x in el.iter(q('t')))

def main():
    p = argparse.ArgumentParser()
    p.add_argument('source', type=Path)
    p.add_argument('target', type=Path)
    args = p.parse_args()
    if args.target.exists(): raise ValueError('Target exists')
    with zipfile.ZipFile(args.source) as z:
        raw=z.read('word/document.xml')
        for _, pair in E.iterparse(io.BytesIO(raw), events=['start-ns']):
            prefix, uri=pair
            if not prefix.startswith('ns'): E.register_namespace(prefix,uri)
        doc=E.fromstring(raw); body=doc.find('w:body',NS)
        def heading(title):
            matches=[e for e in body if e.tag==q('p') and text(e).strip()==title]
            if len(matches)!=1: raise ValueError('Ambiguous/missing heading: '+title)
            return matches[0]
        start=heading('Cadenas de búsqueda a usar')
        middle=heading('Documentos encontrados')
        criteria=heading('Criterios de inclusión/exclusión')
        end=heading('Formulario de extracción de datos')
        items=list(body); a,b=items.index(start),items.index(end)
        if not a<items.index(middle)<items.index(criteria)<b: raise ValueError('Section order')
        if any(e.find('.//w:sectPr',NS) is not None for e in items[a:b]):
            raise ValueError('Section break in removal range')
        old=[text(e) for e in items[a:b]]
        def paragraph(content, style=None, red=False):
            el=E.Element(q('p'))
            if style:
                pr=E.SubElement(el,q('pPr')); E.SubElement(pr,q('pStyle'),{q('val'):style})
            run=E.SubElement(el,q('r'))
            if red:
                pr=E.SubElement(run,q('rPr')); E.SubElement(pr,q('i'))
                E.SubElement(pr,q('color'),{q('val'):'FF0000'})
            E.SubElement(run,q('t')).text=content
            return el
        for el in items[a:b]: body.remove(el)
        body.insert(a,paragraph('NOTA PARA EL AUTOR. Actualización del 21 de septiembre de 2026: por indicación del autor, se retiró de esta copia el contenido anterior de Cadenas de búsqueda, Documentos encontrados y Criterios de inclusión/exclusión. El autor declara actualizados y cerrados el estado del arte, la problemática y el marco conceptual. Esta nota registra la actualización; no constituye una nueva validación de la revisión bibliográfica.',red=True))
        previous=next(e for e in body if text(e).startswith('R2.3 sigue parcial respecto del dominio completo:'))
        j=list(body).index(previous)
        body.remove(previous)
        body.insert(j,paragraph('R2.3 sigue parcial respecto del dominio completo. La continuación del 21 de septiembre incorpora un preprocesamiento explícito label_seq_id a numeración de autor, comprobado sobre los archivos mmCIF y PDB de 2xqh/A y descrito al cierre del capítulo. Permanecen pendientes la integración automática de este preprocesamiento, UniProt/SIFTS, los casos multicadena y la ejecución sobre modelos predichos. Las incompatibilidades restantes se rechazan. El caso de desarrollo no sustituye a la reserva de evaluación.'))
        concl=heading('Conclusiones y trabajos futuros')
        i=list(body).index(concl)
        root=Path(__file__).resolve().parents[2]
        evidence=json.loads((root/'evaluation/trp/reference/coordinate-20260921/execution.json').read_text())
        if evidence['exit_code']!=0 or not evidence['identical_reference_csv']: raise ValueError('Missing successful evidence')
        paragraphs=[
            paragraph('Continuación de R2.3 y verificación de ejecución', 'Heading2'),
            paragraph('Se implementó un adaptador explícito de intervalos label_seq_id a numeración de autor para la ruta experimental. El adaptador comprueba cada residuo solicitado contra las coordenadas CA del PDB de destino, la identidad de cadena y estructura, el nombre del residuo y el factor de desplazamiento. Rechaza ausencias, ambigüedades, coordenadas distintas y unidades cuya numeración de autor no sea contigua. Los hashes de entrada y salida vinculan el informe a los archivos utilizados.'),
            paragraph(f'En la referencia de desarrollo 2xqh/A, la conversión recuperó {evidence["unit_count"]} unidades y {evidence["mapped_residues"]} residuos. La ejecución real de GeomeTRe con los intervalos convertidos produjo un CSV idéntico byte a byte al de referencia. Ocho pruebas del adaptador incluyeron el caso real y alteraciones controladas; todas resultaron satisfactorias. La regresión del sistema registró 482 pruebas satisfactorias y una referencia omitida por defecto; esta última se ejecutó por separado con Nextflow y reprodujo el CSV esperado. La batería estructural Python conservó sus 35 pruebas satisfactorias.'),
            paragraph('Este resultado acredita la correspondencia mecánica en el caso de desarrollo conservado. No mide generalización, detección de repeticiones ni exactitud biológica. El adaptador es un preprocesamiento explícito: todavía deben integrarse SIFTS/UniProt, la ruta de ejecución sobre modelos predichos y su incorporación al flujo aprobado. Las mediciones reservadas de F6 siguen pendientes de referencias independientes, anotador y configuración de evaluación.'),
        ]
        for offset,el in enumerate(paragraphs): body.insert(i+offset,el)
        # A.21 goes before the final body section properties, preserving the layout boundary.
        appendix=[paragraph('A.21. Correspondencia explícita y reanudación de ejecuciones','Heading2'),
                  paragraph('La evidencia reproducible se conserva en evaluation/trp/reference/coordinate-20260921/: label-units.json, mapping.json, geometry.csv y execution.json. El conversor se ejecuta con script/tesis/map_residue_units.py y la ejecución de referencia con script/tesis/run_mapped_reference.py. El mapeo registra ambos hashes, modelo, cadena, marcos de origen y destino y cada par de residuos.'),
                  paragraph('La referencia y sus perturbaciones pertenecen al conjunto de desarrollo y no pueden incorporarse a la reserva de F6. La comparación conserva 12 unidades, las inserciones declaradas de la referencia y los parámetros científicos originales. Los ensayos no sustituyen al juicio de un anotador independiente.')]
        pos=next((j for j,e in enumerate(body) if e.tag==q('sectPr')),len(body))
        for offset,el in enumerate(appendix): body.insert(pos+offset,el)
        updated=E.tostring(doc,encoding='utf-8',xml_declaration=True)
        args.target.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(args.target,'x',zipfile.ZIP_DEFLATED) as out:
            for info in z.infolist(): out.writestr(info,updated if info.filename=='word/document.xml' else z.read(info.filename))
    audit={'sourceSha256':hashlib.sha256(args.source.read_bytes()).hexdigest(),
           'targetSha256':hashlib.sha256(args.target.read_bytes()).hexdigest(),
           'removedSections':['Cadenas de búsqueda a usar','Documentos encontrados','Criterios de inclusión/exclusión'],
           'removedBodyElements':len(old),'addedAppendix':'A.21','onlyModifiedZipPart':'word/document.xml'}
    args.target.with_suffix('.audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps(audit,indent=2))

if __name__=='__main__': main()
