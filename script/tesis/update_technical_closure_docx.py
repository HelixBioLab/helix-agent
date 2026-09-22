#!/usr/bin/env python3
"""Update measured results only, preserving author-closed chapters verbatim."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import xml.etree.ElementTree as E
import zipfile

ROOT=Path(__file__).resolve().parents[2]
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
def q(s):return '{'+W+'}'+s
def text(e):return ''.join(x.text or '' for x in e.iter(q('t')))
def paragraph(value,style=None,red=False):
    e=E.Element(q('p'))
    if style:E.SubElement(E.SubElement(e,q('pPr')),q('pStyle'),{q('val'):style})
    r=E.SubElement(e,q('r'))
    if red:
        pr=E.SubElement(r,q('rPr'));E.SubElement(pr,q('i'));E.SubElement(pr,q('color'),{q('val'):'FF0000'})
    E.SubElement(r,q('t')).text=value
    return e

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('target',type=Path)
    a=p.parse_args()
    if a.target.exists():raise ValueError('Target already exists')
    report=json.loads((ROOT/'docs/tesis/evidencia/cierre-tecnico-20260921.json').read_text())
    if not report['checksPassed']:raise ValueError('Evidence not verified')
    with zipfile.ZipFile(a.source) as z:
        raw=z.read('word/document.xml')
        for _,(prefix,uri) in E.iterparse(io.BytesIO(raw),events=['start-ns']):
            if not prefix.startswith('ns'):E.register_namespace(prefix,uri)
        doc=E.fromstring(raw);body=doc.find(q('body'))
        def heading(title):
            matches=[e for e in body if e.tag==q('p') and text(e).strip()==title]
            if len(matches)!=1:raise ValueError('Missing or ambiguous heading '+title)
            return matches[0]
        def replace_section(title,values):
            h=heading(title);items=list(body);start=items.index(h)+1;end=start
            while end<len(items):
                style=items[end].find(q('pPr')+'/'+q('pStyle'))
                if style is not None and style.get(q('val'),'').startswith('Heading'):break
                if items[end].tag==q('sectPr'):break
                end+=1
            for item in items[start:end]:body.remove(item)
            for offset,value in enumerate(values):body.insert(start+offset,paragraph(value))
        replace_section('R1.1. Catálogo declarativo del dominio',[
            'El catálogo TRP 1.2.0 conserva seis recursos auditados y admite tres operaciones: recuperación RCSB, geometría GeomeTRe y detección STRPsearch mediante un adaptador controlado. ReUPred y RepeatsDB continúan candidatos y RepeatsDB-lite permanece como comparador web. La admisión documenta contratos y referencias de ejecución; no acredita exactitud de detección en familias reservadas.',
            'STRPsearch usa una imagen local identificada por digest y un entorno explícito conservado. El adaptador selecciona una cadena proteica canónica, retira únicamente componentes no proteicos registrados y rechaza numeración discontinua, inserciones, conformaciones alternativas y valores no finitos. Comprueba el diagnóstico y las anotaciones, pues un código de proceso cero puede acompañar errores científicos. La ausencia de predicción se reporta como resultado indeterminado, no como etiqueta biológica negativa.',
            'La herramienta trp_detect incorpora dos confirmaciones mediante el servicio de preguntas: preprocesamiento acotado y ejecución del plan identificado por hash. Las entradas y el programa se vuelven a comprobar, las aprobaciones no se aceptan como parámetros del modelo y se conservan decisiones, resultados y fallos. Cada etapa limita Docker a 2 CPU, 8 GiB y 300 segundos; el almacenamiento persistente no dispone de cuota dura y esta ruta no hereda las garantías de recursos de trp_run.',
            'Las referencias reales con mmCIF y PDB de 2xqh/A produjeron una región 162–269 con siete unidades predichas y reviewed=false. La familia está en la base incorporada: son comprobaciones de ingeniería, no sensibilidad ni generalización. La imagen está fijada por identidad; la receta histórica por sí sola no garantiza una reconstrucción idéntica. ReUPred requiere aún entorno compatible y referencia validada. El sitio actual de RepeatsDB declara CC BY 4.0; el alcance específico de ese aviso para la API y el marco de numeración de sus loci requieren confirmación antes de admitir la conversión.'])
        replace_section('R2.3. Correspondencia de identificadores y numeración',[
            'La preparación integra la conversión explícita de intervalos label_seq_id y UniProt a numeración de autor. Los intervalos UniProt requieren un archivo XML SIFTS a nivel de residuo, con hash y accesión declarados. El sistema comprueba identidad de estructura, cadena, modelo y residuo; no deduce desplazamientos a partir de los extremos de un segmento.',
            'Cada residuo solicitado se contrasta entre mmCIF y PDB, incluidas coordenadas CA y factor de desplazamiento. Se rechazan ausencias, ambigüedades, inserciones y conversiones que no producen unidades contiguas. Los originales, los pares de correspondencia, el programa y el informe quedan vinculados al contenido aprobado; una modificación posterior invalida la preparación.',
            'La referencia integrada 2xqh/A, accesión Q9MCI8, transformó 206 residuos de 12 unidades y completó trp_prepare, aprobación de prueba identificada como sintética, trp_run y Nextflow. El CSV fue idéntico byte a byte al de referencia. La copia de evidencia pasó la verificación Python independiente. Son datos de desarrollo; la cobertura sobre correspondencias independientes permanece para F6.',
            'La geometría de modelos predichos se verificó en una ruta CLI separada, con identidad AFDB y pLDDT conservados, descrita en la continuación técnica de este capítulo. Esa ruta aún no está integrada a trp_prepare/trp_run. Los casos multicadena y la ampliación completa del dominio conservan límites explícitos.'])
        # Replace the obsolete F5 note only, retaining the historical control descriptions.
        old=next(e for e in body if text(e).startswith('NOTA PARA EL AUTOR. La ruta de ejecución GeomeTRe continúa limitada'))
        i=list(body).index(old);body.remove(old)
        body.insert(i,paragraph('NOTA PARA EL AUTOR. La preparación experimental incorpora ya SIFTS y la conversión label/autor. La nueva ejecución de geometría AFDB es una ruta CLI acotada y separada de la herramienta del agente. La confianza favorable no certifica plausibilidad física; siguen pendientes controles independientes de constructos, ensamblaje y fallos publicados.',red=True))
        # Historical continuation remains an explicitly dated step; replace its stale remaining-work paragraph.
        old=next(e for e in body if text(e).startswith('Este resultado acredita la correspondencia mecánica en el caso de desarrollo conservado.'))
        i=list(body).index(old);body.remove(old)
        body.insert(i,paragraph('Este ensayo inicial acredita correspondencia mecánica en desarrollo. La continuación técnica integra después el adaptador y SIFTS en la preparación del agente. Las ejecuciones no miden generalización ni exactitud biológica; las mediciones reservadas de F6 conservan sus dependencias independientes.'))
        i=list(body).index(heading('Conclusiones y trabajos futuros'))
        values=[
            paragraph('Continuación técnica: detectores, mapeos y preparación de F6','Heading2'),
            paragraph(f'La regresión integrada registró {report["regressionPass"]} pruebas satisfactorias, {report["regressionSkip"]} referencias omitidas por defecto y cero fallos. La referencia real con mapeo SIFTS se ejecutó por separado. Las pruebas Python de controles, adaptadores, detector y preparación de F6 sumaron {report["pythonPass"]} casos satisfactorios. El chequeo de tipos del paquete también terminó sin errores. Los registros se conservan en docs/tesis/evidencia/cierre-tecnico-20260921/.'),
            paragraph('Para modelos predichos, el adaptador prepara una propuesta identificada por hash con mmCIF, respuesta API, PAE y programa. Exporta coordenadas CA a un PDB de transporte sin EXPDTA ni identificador PDB ficticio; el código afdb de la salida se vincula expresamente a AF-P69905-F1. El campo B conserva pLDDT 0–100 y el informe no lo interpreta como desplazamiento experimental. La salida geométrica no prueba que los segmentos constituyan repeticiones.'),
            paragraph('La primera ejecución con dos segmentos falló en el ajuste del círculo de GeomeTRe y se conservó. Se añadió el requisito de al menos tres unidades antes de ejecutar. La segunda ejecución particionó la misma región 10–30 de hemoglobina en tres segmentos de siete residuos, manteniendo los umbrales de confianza: produjo tres filas geométricas y dos de resumen. Son segmentos artificiales de desarrollo, excluidos de T-STRUCT; no se informa sensibilidad a partir de ellos.'),
            paragraph('El comprobador de preparación de F6 distingue campañas de lenguaje, grafos, recursos, trazas y estructuras. Se recopilaron siete artefactos técnicos con hashes: protocolo, catálogo, guía, inventario, imágenes, dependencias y fuentes del catálogo. El registro permanece como borrador, sin congelación final. Corpus reservado, particiones, revisión científica y referencias externas deben completarse antes de medir; modelo y presupuesto de API afectan a la campaña de lenguaje y la dependencia de clúster solo aplica si se mantiene esa afirmación.'),
            paragraph('La recuperación pública de Pratt no proporcionó coordenadas ni PAE originales. Una descarga de suplementos desde BioStudies presentó contenidos ajenos al artículo pese al identificador del registro; se descartó y se conservaron URL, hashes e indicios de la discrepancia. Los suplementos anteriormente verificados se mantienen. Se siguen reportando cero modelos originales ejecutados y sensibilidad/especificidad sin calcular.'),
        ]
        for offset,value in enumerate(values):body.insert(i+offset,value)
        # Add a current conclusion after chapter-5 conclusion heading, not chapter-3 conclusions.
        ch5=list(body).index(heading('Conclusiones y trabajos futuros'))
        conclusion=next(j for j in range(ch5+1,len(body)) if text(body[j]).strip()=='Conclusiones')
        body.insert(conclusion+1,paragraph('La continuación técnica amplía el alcance verificable: incorpora detección STRPsearch con control explícito de aprobación y errores científicos, mapeo SIFTS por residuo integrado a Nextflow y una demostración acotada de geometría sobre modelos predichos. Estos resultados sustentan la implementación de las rutas descritas; la comparación reservada, el acuerdo humano y la sensibilidad estructural permanecen pendientes.'))
        appendix=[paragraph('A.22. Cierre técnico y preparación de evaluación','Heading2'),
            paragraph('Plan: docs/tesis/PLAN-CIERRE-TECNICO.md. Los 21 resultados se registran en docs/tesis/trazabilidad.json y su vista trazabilidad.md. El verificador script/tesis/audit_thesis_traceability.py comprueba identificadores únicos y existencia de código, pruebas y evidencia; no infiere cumplimiento empírico.'),
            paragraph('Referencias: evaluation/trp/reference/coordinate-integrated-20260921/ conserva SIFTS, la ejecución completa y su verificación; detector-20260921/ conserva las dos entradas y las siete unidades predichas; predicted-geometry-20260921/ conserva el fallo y predicted-geometry-20260921-corrected/ el ensayo corregido. Cada conjunto es desarrollo, con su alcance y limitaciones.'),
            paragraph('Preparación de F6: script/tesis/prepare_f6_draft.py recopila artefactos técnicos y script/tesis/check_f6_readiness.py comprueba dependencias por campaña. evaluation/trp/f6-readiness-20260921/ conserva el informe y el borrador de congelación. La disponibilidad de hashes no sustituye la revisión de corpus ni confirma participación humana. Los umbrales de F2 permanecen intactos.')]
        i=next((j for j,e in enumerate(body) if e.tag==q('sectPr')),len(body))
        for offset,value in enumerate(appendix):body.insert(i+offset,value)
        updated=E.tostring(doc,encoding='utf-8',xml_declaration=True)
        a.target.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(a.target,'x',zipfile.ZIP_DEFLATED) as out:
            for info in z.infolist():out.writestr(info,updated if info.filename=='word/document.xml' else z.read(info.filename))
    print(json.dumps({'sourceSha256':hashlib.sha256(a.source.read_bytes()).hexdigest(),'targetSha256':hashlib.sha256(a.target.read_bytes()).hexdigest(),'appendix':'A.22'},indent=2))

if __name__=='__main__':main()
