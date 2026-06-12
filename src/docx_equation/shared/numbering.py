"""OOXML helpers for centered display equations with right-aligned labels."""

from __future__ import annotations

from lxml import etree

from docx_equation.shared.models import EquationStyle, NumberingOptions
from docx_equation.shared.ooxml import NS, q


def make_tabbed_equation_paragraph(
    equation_node: etree._Element,
    number: int | str | None,
    text_width_dxa: int,
    *,
    numbering: NumberingOptions | None = None,
    style: EquationStyle | None = None,
) -> etree._Element:
    """Create a paragraph with center and right tab stops for an equation."""
    opts = numbering or NumberingOptions()
    equation_style = style or EquationStyle()
    effective_width = opts.text_width_dxa or text_width_dxa
    paragraph = etree.Element(q("w:p"), nsmap=NS)
    ppr = etree.SubElement(paragraph, q("w:pPr"))
    tabs = etree.SubElement(ppr, q("w:tabs"))
    center_pos = int(effective_width * opts.center_tab_ratio)
    etree.SubElement(tabs, q("w:tab"), {q("w:val"): "center", q("w:pos"): str(center_pos)})
    etree.SubElement(tabs, q("w:tab"), {q("w:val"): "right", q("w:pos"): str(effective_width)})
    etree.SubElement(ppr, q("w:jc"), {q("w:val"): "left"})
    etree.SubElement(ppr, q("w:spacing"), {q("w:before"): str(opts.before_dxa), q("w:after"): str(opts.after_dxa)})
    paragraph.append(make_tab_run(equation_style))
    paragraph.append(equation_node)
    if opts.enabled and number is not None:
        paragraph.append(make_tab_run(equation_style))
        for run in make_number_runs(number, opts, equation_style):
            paragraph.append(run)
    return paragraph


def make_tab_run(style: EquationStyle | None = None) -> etree._Element:
    run = etree.Element(q("w:r"), nsmap=NS)
    run.append(make_run_properties(style or EquationStyle()))
    etree.SubElement(run, q("w:tab"))
    return run


def make_number_runs(number: int | str, opts: NumberingOptions, style: EquationStyle) -> list[etree._Element]:
    """Create Word runs for a display-equation number."""
    if isinstance(number, int):
        if opts.number_format == "(1SEP1)" and opts.chapter is not None:
            if opts.use_seq_field:
                return [
                    make_text_run(f"({opts.chapter}{opts.separator}", style),
                    *make_seq_field_runs(number, opts, style),
                    make_text_run(")", style),
                ]
            return [make_text_run(f"({opts.chapter}{opts.separator}{number})", style)]
        if opts.use_seq_field:
            return [
                make_text_run("(", style),
                *make_seq_field_runs(number, opts, style),
                make_text_run(")", style),
            ]
        return [make_text_run(f"({number})", style)]
    text = str(number)
    if not text.startswith("("):
        text = f"({text})"
    return [make_text_run(text, style)]


def make_seq_field_runs(number: int, opts: NumberingOptions, style: EquationStyle) -> list[etree._Element]:
    instr = f" SEQ {opts.sequence_name} \\* ARABIC "
    if opts.restart_at_first and number == 1:
        instr = f" SEQ {opts.sequence_name} \\r 1 \\* ARABIC "
    runs: list[etree._Element] = []
    for fld_type, text in (
        ("begin", None),
        (None, instr),
        ("separate", None),
        (None, str(number)),
        ("end", None),
    ):
        run = etree.Element(q("w:r"), nsmap=NS)
        run.append(make_run_properties(style))
        if fld_type:
            fld = etree.SubElement(run, q("w:fldChar"))
            fld.set(q("w:fldCharType"), fld_type)
        elif text == instr:
            instr_text = etree.SubElement(run, q("w:instrText"))
            instr_text.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            instr_text.text = text
        else:
            result = etree.SubElement(run, q("w:t"))
            result.text = text
        runs.append(run)
    return runs


def make_text_run(text: str, style: EquationStyle | None = None) -> etree._Element:
    effective = style or EquationStyle()
    run = etree.Element(q("w:r"), nsmap=NS)
    run.append(make_run_properties(effective))
    text_el = etree.SubElement(run, q("w:t"))
    text_el.text = text
    return run


def make_run_properties(style: EquationStyle) -> etree._Element:
    rpr = etree.Element(q("w:rPr"), nsmap=NS)
    etree.SubElement(
        rpr,
        q("w:rFonts"),
        {
            q("w:ascii"): style.font_family,
            q("w:hAnsi"): style.font_family,
            q("w:cs"): style.font_family,
            q("w:eastAsia"): style.east_asia_font,
        },
    )
    size = str(round(style.number_font_size_pt * 2))
    etree.SubElement(rpr, q("w:sz"), {q("w:val"): size})
    etree.SubElement(rpr, q("w:szCs"), {q("w:val"): size})
    etree.SubElement(rpr, q("w:color"), {q("w:val"): style.color})
    return rpr
