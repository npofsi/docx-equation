from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

from mt_toolkit.convert_docx import convert_omml_docx_to_mathtype
from mt_toolkit.domain.models import ConversionOptions, ConversionSummary, EquationSpec
from mt_toolkit.infrastructure.ooxml.embed_mathml import (
    build_equation_docx,
    embed_mathml_placeholders,
)
from mt_toolkit.mathml import parse_mathml
from mt_toolkit.mtef import encode_mtef
from mt_toolkit.ole import build_mathtype_ole_object


def mathml_to_mtef(mathml: bytes | str, options: ConversionOptions | None = None) -> bytes:
    opts = options or ConversionOptions()
    return encode_mtef(parse_mathml(mathml), opts.mathtype_version)


def mathml_to_mathtype_ole(mathml: bytes | str, options: ConversionOptions | None = None) -> bytes:
    opts = options or ConversionOptions()
    return build_mathtype_ole_object(mathml_to_mtef(mathml, opts), opts.prog_id)


def convert_docx(
    input_path: str | Path,
    output_path: str | Path,
    options: ConversionOptions | None = None,
) -> ConversionSummary:
    opts = options or ConversionOptions()
    count = convert_omml_docx_to_mathtype(
        input_path,
        output_path,
        inline_height_pt=opts.inline_height_pt,
        display_height_pt=opts.display_height_pt,
        max_width_pt=opts.max_width_pt,
        preview_pt_per_px=opts.preview_pt_per_px,
        display_layout=opts.display_layout,
        mathtype_version=opts.mathtype_version,
    )
    return ConversionSummary(found=count, converted=count)


def inspect_docx(path: str | Path) -> dict[str, int]:
    with ZipFile(path) as zf:
        names = zf.namelist()
        document = zf.read("word/document.xml").decode("utf-8", errors="ignore")
    return {
        "embeddings": len([name for name in names if name.startswith("word/embeddings/") and name.endswith(".bin")]),
        "mathml_placeholders": document.count("{{MT_EQ_"),
        "alternate_content": document.count("AlternateContent"),
        "omml_equations": document.count("<m:oMath"),
    }


__all__ = [
    "ConversionOptions",
    "ConversionSummary",
    "EquationSpec",
    "build_equation_docx",
    "convert_docx",
    "embed_mathml_placeholders",
    "inspect_docx",
    "mathml_to_mathtype_ole",
    "mathml_to_mtef",
]
