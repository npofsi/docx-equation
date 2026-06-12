from __future__ import annotations

from zipfile import ZipFile

from lxml import etree
import olefile

from mt_toolkit.docx_embed import NS, build_demo_docx, make_display_equation_paragraph
from mt_toolkit.latex import parse_latex_subset
from mt_toolkit.mathml import parse_mathml
from mt_toolkit.mtef import encode_mtef
from mt_toolkit.ole import build_mathtype_ole_object


def test_ole_contains_mathtype_streams(tmp_path):
    expr = parse_latex_subset(r"\frac{4}{5}=0.8")
    ole_path = tmp_path / "oleObject1.bin"
    ole_path.write_bytes(build_mathtype_ole_object(encode_mtef(expr)))

    ole = olefile.OleFileIO(str(ole_path))
    try:
        streams = {"/".join(item) for item in ole.listdir(streams=True, storages=False)}
        assert "\x01CompObj" in streams
        assert "\x01Ole" in streams
        assert "\x03ObjInfo" in streams
        assert "Equation Native" in streams
        native = ole.openstream(["Equation Native"]).read()
        assert native[28] == 5
    finally:
        ole.close()


def test_demo_docx_contains_equation_dsmt4_object(tmp_path):
    docx_path = tmp_path / "demo.docx"
    build_demo_docx(r"F_n=F_{n-1}+F_{n-2}", docx_path)

    with ZipFile(docx_path) as zf:
        names = set(zf.namelist())
        document_xml = zf.read("word/document.xml").decode("utf-8")
        rels_xml = zf.read("word/_rels/document.xml.rels").decode("utf-8")
        assert "word/embeddings/oleObject1.bin" in names
        assert "word/media/mathtype_preview_001.png" in names
        assert 'ProgID="Equation.DSMT4"' in document_xml
        assert "relationships/oleObject" in rels_xml


def test_mathml_parser_supports_section_formula_subset():
    expr = parse_mathml(
        b"""<math xmlns="http://www.w3.org/1998/Math/MathML">
        <msubsup><mi>P</mi><mrow><mi>e</mi><mi>s</mi></mrow><mrow><mi>c</mi><mi>h</mi></mrow></msubsup>
        <mo>(</mo><mi>t</mi><mo>)</mo><mo>=</mo>
        <mfrac><mrow><mn>1</mn></mrow><mrow><mn>1</mn><mo>+</mo><mi>\xcf\x84</mi><mi>s</mi></mrow></mfrac>
        </math>"""
    )
    mtef = encode_mtef(expr)
    assert mtef.startswith(b"\x05\x01\x00\x06")
    assert b"DSMT6" in mtef


def test_latex_parser_supports_big_operator_and_decoration():
    expr = parse_latex_subset(r"\sum_{i=1}^{n} \overline{x_i}+\int_0^T p(t)")
    mtef = encode_mtef(expr)
    assert mtef.startswith(b"\x05\x01\x00\x06")
    assert b"\x10" in mtef
    assert b"\x0f" in mtef


def test_mathml_parser_supports_matrix_and_limits():
    expr = parse_mathml(
        b"""<math xmlns="http://www.w3.org/1998/Math/MathML">
        <munderover><mo>&#x2211;</mo><mrow><mi>i</mi><mo>=</mo><mn>1</mn></mrow><mi>n</mi></munderover>
        <mtable><mtr><mtd><mi>a</mi></mtd><mtd><mi>b</mi></mtd></mtr><mtr><mtd><mi>c</mi></mtd><mtd><mi>d</mi></mtd></mtr></mtable>
        </math>"""
    )
    mtef = encode_mtef(expr)
    assert mtef.startswith(b"\x05\x01\x00\x06")
    assert b"\x05\x00" in mtef


def test_display_equation_paragraph_uses_center_and_right_tabs():
    object_run = etree.Element(f"{{{NS['w']}}}r", nsmap=NS)
    paragraph = make_display_equation_paragraph(object_run, "(4-1)", 8958)
    tabs = paragraph.xpath(".//w:tab[@w:val]", namespaces=NS)
    assert [tab.get(f"{{{NS['w']}}}val") for tab in tabs] == ["center", "right"]
    assert [tab.get(f"{{{NS['w']}}}pos") for tab in tabs] == ["4479", "8958"]
    assert "(4-1)" in "".join(paragraph.xpath(".//w:t/text()", namespaces=NS))
