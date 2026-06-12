from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

from lxml import etree

from docx_equation.mathtype.embed import (
    build_equation_docx as build_mathtype_equation_docx,
    embed_mathml_placeholders as embed_mathtype_mathml_placeholders,
)
from docx_equation.mathtype.legacy import convert_omml_docx_to_mathtype
from docx_equation.mathtype.mtef import encode_mtef
from docx_equation.mathtype.ole import build_mathtype_ole_object
from docx_equation.omml.converter import mathml_to_omml, mathml_to_omml_xml
from docx_equation.omml.embed import (
    build_equation_docx as build_omml_equation_docx,
    embed_mathml_placeholders as embed_omml_mathml_placeholders,
)
from docx_equation.shared.mathml import parse_mathml
from docx_equation.shared.models import (
    ConversionOptions,
    ConversionSummary,
    EquationSpec,
    ExportOptions,
    NumberingOptions,
    OptionsLike,
    normalize_options,
)


def mathml_to_mtef(mathml: bytes | str, options: OptionsLike = None) -> bytes:
    opts = normalize_options(options, target="mathtype")
    return encode_mtef(parse_mathml(mathml), opts.mathtype.mathtype_version)


def mathml_to_mathtype_ole(mathml: bytes | str, options: OptionsLike = None) -> bytes:
    opts = normalize_options(options, target="mathtype")
    return build_mathtype_ole_object(mathml_to_mtef(mathml, opts), opts.mathtype.prog_id)


def embed_mathml_placeholders(
    input_path: str | Path,
    output_path: str | Path,
    equations: list[EquationSpec],
    options: OptionsLike = None,
    work_dir: str | Path | None = None,
) -> ConversionSummary:
    opts = normalize_options(options, target="mathtype")
    if opts.target == "omml":
        return embed_omml_mathml_placeholders(input_path, output_path, equations, opts, work_dir)
    return embed_mathtype_mathml_placeholders(input_path, output_path, equations, opts, work_dir)


def build_equation_docx(
    equations: list[str],
    output_path: str | Path,
    options: OptionsLike = None,
) -> ConversionSummary:
    opts = normalize_options(options, target="mathtype")
    if opts.target == "omml":
        return build_omml_equation_docx(equations, output_path, opts)
    return build_mathtype_equation_docx(equations, output_path, opts)


def convert_docx(
    input_path: str | Path,
    output_path: str | Path,
    options: OptionsLike = None,
) -> ConversionSummary:
    opts = normalize_options(options, target="mathtype")
    mt_opts = opts.mathtype
    legacy_numbering = opts.numbering if opts.numbering != NumberingOptions() else None
    count = convert_omml_docx_to_mathtype(
        input_path,
        output_path,
        inline_height_pt=mt_opts.inline_height_pt,
        display_height_pt=mt_opts.display_height_pt,
        max_width_pt=mt_opts.max_width_pt,
        preview_pt_per_px=mt_opts.preview_pt_per_px,
        display_layout=opts.display_layout,
        mathtype_version=mt_opts.mathtype_version,
        numbering=legacy_numbering,
        style=opts.style,
    )
    return ConversionSummary(found=count, converted=count)


def inspect_docx(path: str | Path) -> dict[str, int]:
    with ZipFile(path) as zf:
        names = zf.namelist()
        document_bytes = zf.read("word/document.xml")
    document = document_bytes.decode("utf-8", errors="ignore")
    root = etree.fromstring(document_bytes)
    namespaces = {
        "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
        "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
    }
    return {
        "embeddings": len([name for name in names if name.startswith("word/embeddings/") and name.endswith(".bin")]),
        "mathml_placeholders": document.count("{{DOCX_EQ_"),
        "alternate_content": len(root.xpath(".//mc:AlternateContent", namespaces=namespaces)),
        "omml_equations": len(root.xpath(".//m:oMath", namespaces=namespaces)),
    }


__all__ = [
    "ConversionOptions",
    "ConversionSummary",
    "EquationSpec",
    "ExportOptions",
    "build_equation_docx",
    "convert_docx",
    "embed_mathml_placeholders",
    "inspect_docx",
    "mathml_to_mathtype_ole",
    "mathml_to_mtef",
    "mathml_to_omml",
    "mathml_to_omml_xml",
]
