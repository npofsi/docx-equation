from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED

from lxml import etree
from PIL import Image

from docx_equation.mathtype.ooxml import (
    IMAGE_REL,
    OLE_REL,
    _add_relationship,
    _ensure_default,
    make_display_equation_paragraph,
    make_object_run,
)
from docx_equation.shared.mathml import parse_mathml, render_mathml_files
from docx_equation.mathtype.mtef import encode_mtef
from docx_equation.mathtype.ole import build_mathtype_ole_object
from docx_equation.shared.models import EquationStyle, NumberingOptions


OMML_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
DEFAULT_OMML2MATHML = Path("/Applications/Microsoft Word.app/Contents/Resources/omml2mathml.xsl")

NS = {
    "m": OMML_NS,
    "w": W_NS,
}


@dataclass(frozen=True)
class MathTarget:
    replace_node: etree._Element
    omath_node: etree._Element
    is_display: bool
    equation_number: str | None = None
    equation_sequence: int | None = None


def convert_omml_docx_to_mathtype(
    input_docx: str | Path,
    output_docx: str | Path,
    work_dir: str | Path | None = None,
    omml2mathml_xsl: str | Path = DEFAULT_OMML2MATHML,
    inline_height_pt: float = 12.5,
    display_height_pt: float = 21.0,
    max_width_pt: float = 360.0,
    preview_pt_per_px: float | None = 0.15,
    display_layout: str = "preserve",
    mathtype_version: str = "DSMT4",
    numbering: NumberingOptions | None = None,
    style: EquationStyle | None = None,
) -> int:
    source = Path(input_docx)
    target = Path(output_docx)
    target.parent.mkdir(parents=True, exist_ok=True)

    if work_dir is None:
        with tempfile.TemporaryDirectory(prefix="docx_equation_convert_") as tmp:
            return _convert(
                source,
                target,
                Path(tmp),
                Path(omml2mathml_xsl),
                inline_height_pt,
                display_height_pt,
                max_width_pt,
                preview_pt_per_px,
                display_layout,
                mathtype_version,
                numbering,
                style,
            )
    return _convert(
        source,
        target,
        Path(work_dir),
        Path(omml2mathml_xsl),
        inline_height_pt,
        display_height_pt,
        max_width_pt,
        preview_pt_per_px,
        display_layout,
        mathtype_version,
        numbering,
        style,
    )


def _convert(
    source: Path,
    target: Path,
    work_dir: Path,
    xsl_path: Path,
    inline_height_pt: float,
    display_height_pt: float,
    max_width_pt: float,
    preview_pt_per_px: float | None,
    display_layout: str,
    mathtype_version: str,
    numbering: NumberingOptions | None,
    style: EquationStyle | None,
) -> int:
    work_dir.mkdir(parents=True, exist_ok=True)
    mathml_dir = work_dir / "mathml"
    preview_dir = work_dir / "preview_png"
    ole_dir = work_dir / "ole"
    for directory in (mathml_dir, preview_dir, ole_dir):
        directory.mkdir(parents=True, exist_ok=True)

    transform = _load_transform(xsl_path)
    parser = etree.XMLParser(resolve_entities=False, recover=True, remove_blank_text=False)

    with ZipFile(source) as zin:
        document_root = etree.fromstring(zin.read("word/document.xml"), parser)
        targets = _math_targets(document_root, display_layout=display_layout)
        text_width_dxa = _text_width_dxa(document_root)
        mathml_files: list[Path] = []
        for index, target_info in enumerate(targets, 1):
            mathml = transform(etree.fromstring(etree.tostring(target_info.omath_node)))
            mathml_path = mathml_dir / f"equation_{index:03d}.mml"
            mathml_path.write_bytes(etree.tostring(mathml, encoding="utf-8", pretty_print=True, xml_declaration=True))
            mathml_files.append(mathml_path)

        render_mathml_files(mathml_dir, preview_dir)

        rels_root = etree.fromstring(zin.read("word/_rels/document.xml.rels"), parser)
        content_types_root = etree.fromstring(zin.read("[Content_Types].xml"), parser)
        _ensure_default(content_types_root, "png", "image/png")
        _ensure_default(content_types_root, "bin", "application/vnd.openxmlformats-officedocument.oleObject")

        media_entries: list[tuple[str, bytes]] = []
        ole_entries: list[tuple[str, bytes]] = []

        for index, (target_info, mathml_path) in enumerate(zip(targets, mathml_files), 1):
            preview_path = preview_dir / f"equation_{index:03d}.png"
            image_name = f"mathtype_preview_{index:03d}.png"
            ole_name = f"oleObjectMathType{index:03d}.bin"
            image_rel_id = _add_relationship(rels_root, IMAGE_REL, f"media/{image_name}")
            ole_rel_id = _add_relationship(rels_root, OLE_REL, f"embeddings/{ole_name}")

            expr = parse_mathml(mathml_path.read_bytes())
            prog_id = f"Equation.{mathtype_version}"
            ole_bytes = build_mathtype_ole_object(encode_mtef(expr, mathtype_version), prog_id)
            (ole_dir / ole_name).write_bytes(ole_bytes)
            ole_entries.append((f"word/embeddings/{ole_name}", ole_bytes))
            media_entries.append((f"word/media/{image_name}", preview_path.read_bytes()))

            width_px, height_px = Image.open(preview_path).size
            replacement = make_object_run(
                image_rel_id,
                ole_rel_id,
                width_px,
                height_px,
                index=index,
                display=target_info.is_display,
                inline_height_pt=inline_height_pt,
                display_height_pt=display_height_pt,
                max_width_pt=max_width_pt,
                preview_pt_per_px=preview_pt_per_px,
                vertical_align="middle" if target_info.is_display and target_info.equation_number else None,
                prog_id=prog_id,
            )
            if target_info.is_display and target_info.equation_number and display_layout == "tabbed":
                number: int | str = target_info.equation_number
                if numbering is not None and target_info.equation_sequence is not None:
                    number = target_info.equation_sequence
                replacement = make_display_equation_paragraph(
                    replacement,
                    number,
                    text_width_dxa,
                    numbering=numbering,
                    style=style,
                )
            replacement.tail = target_info.replace_node.tail
            parent = target_info.replace_node.getparent()
            if parent is not None:
                parent.replace(target_info.replace_node, replacement)

        document_xml = etree.tostring(document_root, encoding="utf-8", xml_declaration=True, standalone=True)
        rels_xml = etree.tostring(rels_root, encoding="utf-8", xml_declaration=True, standalone=True)
        content_types_xml = etree.tostring(content_types_root, encoding="utf-8", xml_declaration=True, standalone=True)

        with ZipFile(target, "w", ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                if info.filename == "word/document.xml":
                    zout.writestr(info, document_xml)
                elif info.filename == "word/_rels/document.xml.rels":
                    zout.writestr(info, rels_xml)
                elif info.filename == "[Content_Types].xml":
                    zout.writestr(info, content_types_xml)
                else:
                    zout.writestr(info, zin.read(info.filename))
            for name, data in media_entries + ole_entries:
                zout.writestr(name, data)

    return len(targets)


def _load_transform(xsl_path: Path) -> etree.XSLT:
    if not xsl_path.exists():
        raise FileNotFoundError(f"OMML to MathML XSL file not found: {xsl_path}")
    return etree.XSLT(etree.parse(str(xsl_path)))


def _math_targets(root: etree._Element, display_layout: str = "preserve") -> list[MathTarget]:
    math_para_tag = f"{{{OMML_NS}}}oMathPara"
    omath_tag = f"{{{OMML_NS}}}oMath"
    targets: list[MathTarget] = []
    seen_tables: set[int] = set()
    for element in root.iter():
        if element.tag == math_para_tag:
            if display_layout == "tabbed":
                table = _formula_table_for_display(element)
                if table is not None and id(table) not in seen_tables:
                    seen_tables.add(id(table))
                    number = _extract_formula_number(table)
                    targets.append(
                        MathTarget(
                            table,
                            _omath_for_target(element, True),
                            True,
                            number,
                            _formula_sequence(number),
                        )
                    )
                    continue
            targets.append(MathTarget(element, _omath_for_target(element, True), True))
        elif element.tag == omath_tag and not _is_descendant_of(element, math_para_tag):
            targets.append(MathTarget(element, element, False))
    return targets


def _omath_for_target(element: etree._Element, is_display: bool) -> etree._Element:
    if not is_display:
        return element
    matches = element.xpath(".//m:oMath", namespaces=NS)
    if not matches:
        raise ValueError("Display equation did not contain an m:oMath element.")
    return matches[0]


def _is_descendant_of(element: etree._Element, tag: str) -> bool:
    parent = element.getparent()
    while parent is not None:
        if parent.tag == tag:
            return True
        parent = parent.getparent()
    return False


def _formula_table_for_display(element: etree._Element) -> etree._Element | None:
    table = _ancestor(element, f"{{{W_NS}}}tbl")
    if table is None:
        return None
    rows = table.xpath("./w:tr", namespaces=NS)
    if len(rows) != 1:
        return None
    cells = rows[0].xpath("./w:tc", namespaces=NS)
    if len(cells) != 3:
        return None
    if element not in cells[1].xpath(".//m:oMathPara", namespaces=NS):
        return None
    number = _extract_formula_number(table)
    return table if number else None


def _extract_formula_number(table: etree._Element) -> str | None:
    cells = table.xpath("./w:tr[1]/w:tc", namespaces=NS)
    if len(cells) != 3:
        return None
    text = "".join(cells[2].xpath(".//w:t/text()", namespaces=NS)).strip()
    if _formula_sequence(text) is not None:
        return text
    return None


def _formula_sequence(text: str | None) -> int | None:
    if not text:
        return None
    stripped = text.strip()
    if not stripped.startswith("(") or not stripped.endswith(")"):
        return None
    numbers = re.findall(r"\d+", stripped[1:-1])
    if not numbers:
        return None
    return int(numbers[-1])


def _ancestor(element: etree._Element, tag: str) -> etree._Element | None:
    parent = element.getparent()
    while parent is not None:
        if parent.tag == tag:
            return parent
        parent = parent.getparent()
    return None


def _text_width_dxa(root: etree._Element) -> int:
    sections = root.xpath("//w:sectPr", namespaces=NS)
    if not sections:
        return 9360
    section = sections[-1]
    page_width = section.xpath("./w:pgSz/@w:w", namespaces=NS)
    left = section.xpath("./w:pgMar/@w:left", namespaces=NS)
    right = section.xpath("./w:pgMar/@w:right", namespaces=NS)
    try:
        return int(page_width[0]) - int(left[0]) - int(right[0])
    except (IndexError, TypeError, ValueError):
        return 9360
