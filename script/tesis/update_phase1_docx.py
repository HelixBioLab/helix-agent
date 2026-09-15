#!/usr/bin/env python3
"""Apply the reviewed phase-one content to the known thesis source, preserving OOXML parts.

Writes a separate output; refuses an unexpected source revision or an existing output.
Changes document.xml, settings.xml and heading styles. Figures and annotations survive
the patch; the rendering pass separately refreshes fields through LibreOffice.
"""

import argparse
import copy
import hashlib
import json
from pathlib import Path
from xml.dom import minidom
from zipfile import ZipFile

EXPECTED = "c95fe37a10be7593be2eb2587d8805d7f72a37f0942395841098a796778a0341"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if hashlib.sha256(args.source.read_bytes()).hexdigest() != EXPECTED:
        parser.error("source revision differs; review the new document before applying this phase")
    if args.output.exists() or args.output.resolve() == args.source.resolve():
        parser.error("choose a new output file; this script never overwrites a document")
    content = json.loads((Path(__file__).resolve().parents[2] / "docs/tesis/fase1-documento.json").read_text())

    with ZipFile(args.source) as source:
        doc = minidom.parseString(source.read("word/document.xml"))
        body = doc.getElementsByTagName("w:body")[0]
        blocks = [node for node in body.childNodes if node.nodeType == node.ELEMENT_NODE]
        assert len(blocks) == 519

        def element(name, attrs=None, parent=None):
            node = doc.createElementNS(W, "w:" + name)
            for key, value in (attrs or {}).items():
                node.setAttributeNS(W, "w:" + key, str(value))
            if parent is not None:
                parent.appendChild(node)
            return node

        def text(node):
            return "".join(t.firstChild.nodeValue for t in node.getElementsByTagName("w:t") if t.firstChild)

        def replace_text(node, value):
            runs = node.getElementsByTagName("w:t")
            if not runs:
                run = element("r", parent=node)
                runs = [element("t", parent=run)]
            for item in runs:
                for child in list(item.childNodes):
                    item.removeChild(child)
            runs[0].appendChild(doc.createTextNode(value))
            runs[0].setAttribute("xml:space", "preserve")

        def properties(node):
            found = [x for x in node.childNodes if x.nodeType == x.ELEMENT_NODE and x.tagName == "w:pPr"]
            if found:
                return found[0]
            props = element("pPr")
            node.insertBefore(props, node.firstChild)
            return props

        def property_value(props, tag, value):
            found = props.getElementsByTagName("w:" + tag)
            if found:
                found[0].setAttributeNS(W, "w:val", str(value))
                return
            item = element(tag, {"val": value})
            # pStyle must precede all other paragraph properties.
            if tag == "pStyle":
                props.insertBefore(item, props.firstChild)
            else:
                props.appendChild(item)

        def paragraph(value, kind="paragraph", level=1, size=24):
            node = element("p")
            props = element("pPr", parent=node)
            if kind == "heading":
                element("pStyle", {"val": "Heading" + str(level + 1)}, props)
                element("keepNext", parent=props)
                numbers = element("numPr", parent=props)
                element("ilvl", {"val": level}, numbers)
                element("numId", {"val": 16}, numbers)
            element("spacing", {"before": 160 if kind == "heading" else 0, "after": 120, "line": 360, "lineRule": "auto"}, props)
            element("jc", {"val": "left" if kind == "heading" else "both"}, props)
            if kind == "heading":
                element("outlineLvl", {"val": level}, props)
            run = element("r", parent=node)
            run_props = element("rPr", parent=run)
            element("rFonts", {"ascii": "Times New Roman", "hAnsi": "Times New Roman"}, run_props)
            if kind == "heading":
                element("b", parent=run_props)
            if kind == "note":
                element("i", parent=run_props)
            element("color", {"val": "FF0000" if kind == "note" else "000000"}, run_props)
            element("sz", {"val": size}, run_props)
            item = element("t", parent=run)
            item.setAttribute("xml:space", "preserve")
            item.appendChild(doc.createTextNode(value))
            return node

        def make_table(block):
            node = element("tbl")
            props = element("tblPr", parent=node)
            element("tblW", {"w": 8200, "type": "dxa"}, props)
            borders = element("tblBorders", parent=props)
            for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
                element(side, {"val": "single", "sz": 4, "color": "777777"}, borders)
            element("tblLayout", {"type": "fixed"}, props)
            widths = block.get("widths") or [8200 // len(block["headers"])] * len(block["headers"])
            grid = element("tblGrid", parent=node)
            for width in widths:
                element("gridCol", {"w": width}, grid)
            for index, values in enumerate([block["headers"]] + block["rows"]):
                row = element("tr", parent=node)
                row_props = element("trPr", parent=row)
                element("cantSplit", parent=row_props)
                if index == 0:
                    element("tblHeader", parent=row_props)
                for value, width in zip(values, widths):
                    cell = element("tc", parent=row)
                    cell_props = element("tcPr", parent=cell)
                    element("tcW", {"w": width, "type": "dxa"}, cell_props)
                    if index == 0:
                        element("shd", {"fill": "E8EDF2"}, cell_props)
                    para = paragraph(str(value), size=20)
                    spacing = para.getElementsByTagName("w:spacing")[0]
                    spacing.setAttributeNS(W, "w:line", "240")
                    para.getElementsByTagName("w:jc")[0].setAttributeNS(W, "w:val", "left")
                    if index == 0:
                        element("b", parent=para.getElementsByTagName("w:rPr")[0])
                    cell.appendChild(para)
            return node

        def render(block):
            if block["kind"] == "table":
                return make_table(block)
            return paragraph(block["text"], block["kind"], block.get("level", 1))

        def replace_range(start, stop, replacement):
            anchor = blocks[stop]
            sections = [s.cloneNode(True) for old in blocks[start:stop] for s in old.getElementsByTagName("w:sectPr")]
            inserted = []
            for block in replacement:
                node = render(block)
                body.insertBefore(node, anchor)
                inserted.append(node)
            # Section properties belong to the final paragraph of the preceding section.
            # Discarding a template paragraph must not apply the annex footer to the whole thesis.
            for section in sections:
                node = inserted[-1] if inserted and inserted[-1].tagName == "w:p" else paragraph("")
                if node.parentNode is None:
                    body.insertBefore(node, anchor)
                properties(node).appendChild(section)
            for node in blocks[start:stop]:
                if node.parentNode is body:
                    body.removeChild(node)

        # Fill the title in an existing blank paragraph without changing the university seal.
        replace_text(blocks[8], content["title"])
        body.insertBefore(blocks[8], blocks[3])
        title_props = properties(blocks[8])
        property_value(title_props, "keepNext", 1)
        title_run = next(r for r in blocks[8].getElementsByTagName("w:r") if r.getElementsByTagName("w:t"))
        title_existing = title_run.getElementsByTagName("w:rPr")
        title_rpr = title_existing[0] if title_existing else element("rPr")
        if not title_existing:
            title_run.insertBefore(title_rpr, title_run.firstChild)
        element("b", parent=title_rpr)
        element("sz", {"val": 28}, title_rpr)
        replace_text(blocks[3], "Tesis para optar por el título profesional en Ingeniería Informática")
        replace_text(blocks[12], "Lima, septiembre de 2026")
        replace_range(17, 28, content["summary"])
        replace_range(28, 36, [])
        property_value(properties(blocks[36]), "pageBreakBefore", 1)
        replace_range(37, 38, content["topic"])

        # Correct the actual list hierarchy, so conclusions become chapter five.
        level = blocks[337].getElementsByTagName("w:ilvl")[0]
        level.setAttributeNS(W, "w:val", "0")
        for index in (337, 340):
            for br in list(blocks[index].getElementsByTagName("w:br")):
                if br.getAttribute("w:type") == "page":
                    br.parentNode.removeChild(br)
            property_value(properties(blocks[index]), "pageBreakBefore", 1)
        replace_range(338, 340, content["chapter4"])
        replace_range(343, 344, [])
        for block in content["chapter5_conclusions"]:
            body.insertBefore(render(block), blocks[342])
        for block in content["chapter5_future"]:
            body.insertBefore(render(block), blocks[344])
        replace_range(448, 450, content["annex_intro"])

        sections = [(451,460),(460,464),(464,466),(466,468),(468,477),(477,479),(479,487),(487,492),(492,495),(495,497),(497,499),(499,501),(501,503),(503,505),(505,518)]
        for number, (start, stop) in enumerate(sections, 1):
            name = text(blocks[start]).strip()
            assert name in content["annex"], name
            replace_range(start + 1, stop, content["annex"][name])
            props = properties(blocks[start])
            for nums in list(props.getElementsByTagName("w:numPr")):
                props.removeChild(nums)
            replace_text(blocks[start], f"A.{number}. {name}")
            property_value(props, "pStyle", "Heading2")
            property_value(props, "outlineLvl", 1)
            property_value(props, "keepNext", 1)

        # Repair known errata and retire their now-obsolete red notes.
        replace_text(blocks[70], text(blocks[70]).replace("D e extremo", "De extremo").replace("e n su propio", "en su propio"))
        replace_text(blocks[85], text(blocks[85]).replace("máquina, Recoge", "máquina. Recoge"))
        for index in (71, 86):
            body.removeChild(blocks[index])

        # The missing cells in R2.1 are in the original objective-two verification table.
        for row in blocks[116].getElementsByTagName("w:tr"):
            cells = row.getElementsByTagName("w:tc")
            if cells and "R2.1." in text(cells[0]):
                assert len(cells) == 3
                replace_text(cells[1], "Protocolo fechado y versionado; historial de revisiones y enmiendas anterior a la campaña de evaluación")
                replace_text(cells[2], "100% de los indicadores tienen umbral, denominador y regla de reporte declarados antes de la medición; 100% de las modificaciones posteriores quedan fechadas y justificadas")

        method_note = paragraph("NOTA PARA EL AUTOR. Los procedimientos de esta sección son compromisos de construcción y evaluación; su redacción no acredita que estén todos implementados. El Capítulo 4 distingue componentes existentes, implementación pendiente y mediciones aún no obtenidas; el Anexo A organiza su ejecución. La aprobación de una especificación no impide que un agente general continúe conversando: la frontera determinista debe comprobarse en la ruta integrada de ejecución.", "note")
        body.insertBefore(method_note, blocks[125])
        body.insertBefore(paragraph("NOTA PARA EL AUTOR. Revisar la expresión «verificar la corrección»: los artefactos permiten establecer qué se ejecutó, comprobar su integridad y conocer los controles aplicados. No garantizan por sí solos corrección biológica. La afirmación universal «no existe una vía» requiere delimitarse al corpus y a los criterios de la revisión del Capítulo 3.", "note"), blocks[70])
        body.insertBefore(paragraph("NOTA PARA EL AUTOR. Este cierre de la revisión contiene una tensión: reconoce que los agentes recorren el trayecto desde lenguaje natural y luego afirma que ninguno acepta preguntas de la disciplina. En F7 contrastar esa última afirmación con la tabla de extracción y acotarla a los requisitos TRP efectivamente evaluados. No usar ausencia en el corpus como prueba universal de inexistencia.", "note"), blocks[337])

        # Expose existing numbered headings to Word's navigation and TOC, retaining direct formatting.
        for para in body.childNodes:
            if para.nodeType != para.ELEMENT_NODE or para.tagName != "w:p":
                continue
            nums = para.getElementsByTagName("w:numPr")
            if nums and nums[0].getElementsByTagName("w:numId")[0].getAttribute("w:val") == "16":
                depth = int(nums[0].getElementsByTagName("w:ilvl")[0].getAttribute("w:val"))
                props = properties(para)
                property_value(props, "pStyle", "Heading" + str(depth + 1))
                property_value(props, "outlineLvl", depth)
        for index in (16, 36, 344, 447, 450):
            property_value(properties(blocks[index]), "outlineLvl", 0)
        property_value(properties(blocks[450]), "pageBreakBefore", 1)

        # Front matter (including the refreshed TOC), body and annex have separate numbering.
        sections = list(doc.getElementsByTagName("w:sectPr"))
        assert len(sections) == 3
        sections[0].parentNode.removeChild(sections[0])
        properties(blocks[40]).appendChild(sections[0])
        property_value(properties(blocks[38]), "pageBreakBefore", 1)
        for section, fmt in zip(sections, ("lowerRoman", "decimal", "decimal")):
            number = section.getElementsByTagName("w:pgNumType")
            if not number:
                number = [element("pgNumType", parent=section)]
            number[0].setAttributeNS(W, "w:fmt", fmt)
            number[0].setAttributeNS(W, "w:start", "1")

        settings = minidom.parseString(source.read("word/settings.xml"))
        updates = settings.getElementsByTagName("w:updateFields")
        if not updates:
            updates = [settings.createElementNS(W, "w:updateFields")]
            settings.documentElement.appendChild(updates[0])
        updates[0].setAttributeNS(W, "w:val", "true")

        styles = minidom.parseString(source.read("word/styles.xml"))
        for style in styles.getElementsByTagName("w:style"):
            if style.getAttribute("w:styleId") not in ("Heading1", "Heading2", "Heading3"):
                continue
            existing = style.getElementsByTagName("w:rPr")
            props = existing[0] if existing else styles.createElementNS(W, "w:rPr")
            if not existing:
                style.appendChild(props)
            for tag, attrs in (("rFonts", {"ascii":"Times New Roman", "hAnsi":"Times New Roman", "cs":"Times New Roman", "eastAsia":"Times New Roman"}), ("color", {"val":"000000"}), ("b", {"val":"1"}), ("sz", {"val":"28" if style.getAttribute("w:styleId") == "Heading1" else "24"})):
                for old in list(props.getElementsByTagName("w:" + tag)):
                    old.parentNode.removeChild(old)
                item = styles.createElementNS(W, "w:" + tag)
                for key, value in attrs.items():
                    item.setAttributeNS(W, "w:" + key, value)
                props.appendChild(item)

        changed = {"word/document.xml": doc.toxml(encoding="UTF-8"), "word/settings.xml": settings.toxml(encoding="UTF-8"), "word/styles.xml": styles.toxml(encoding="UTF-8")}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(args.output, "x") as output:
            for entry in source.infolist():
                output.writestr(copy.copy(entry), changed.get(entry.filename, source.read(entry.filename)))
        with ZipFile(args.output) as output:
            assert output.testzip() is None
            for name in source.namelist():
                if name not in changed:
                    assert source.read(name) == output.read(name), name
        print(json.dumps({"source_sha256": EXPECTED, "output_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(), "changed_parts": list(changed), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
