from __future__ import annotations

import argparse
from pathlib import Path

import olefile

from docx_equation.api import (
    build_equation_docx,
    convert_docx,
    inspect_docx,
    mathml_to_mathtype_ole,
    mathml_to_mtef,
    mathml_to_omml_xml,
)
from docx_equation.mathtype.ooxml import build_demo_docx
from docx_equation.shared.models import EquationStyle, ExportOptions, MathTypeOptions, NumberingOptions, OmmlOptions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DOCX equation generation tools.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    mathml = subparsers.add_parser("mathml", help="Generate OMML, MTEF, or MathType OLE artifacts from MathML.")
    mathml.add_argument("input", type=Path, help="MathML input file.")
    mathml.add_argument("--omml", type=Path, help="Output OMML XML path.")
    mathml.add_argument("--ole", type=Path, help="Output OLE object path.")
    mathml.add_argument("--mtef", type=Path, help="Output raw MTEF path.")
    _add_common_options(mathml)

    demo = subparsers.add_parser("demo", help="Build a DOCX from MathML files.")
    demo.add_argument("mathml", type=Path, nargs="+", help="One or more MathML files.")
    demo.add_argument("-o", "--output", type=Path, required=True, help="Output DOCX path.")
    _add_common_options(demo)

    latex_demo = subparsers.add_parser("latex-demo", help="Build the legacy LaTeX demo DOCX.")
    latex_demo.add_argument("formula", help="Formula in the supported LaTeX subset.")
    latex_demo.add_argument("-o", "--output", type=Path, required=True, help="Output DOCX path.")
    latex_demo.add_argument("--mathtype-version", choices=["DSMT4", "DSMT6"], default="DSMT4")

    convert = subparsers.add_parser("convert", help="Convert OMML equations in a DOCX for MathType compatibility.")
    convert.add_argument("input", type=Path, help="Input DOCX path.")
    convert.add_argument("-o", "--output", type=Path, required=True, help="Output DOCX path.")
    convert.add_argument("--display-layout", choices=["preserve", "tabbed"], default="tabbed")
    _add_common_options(convert, include_target=False)

    inspect = subparsers.add_parser("inspect", help="Inspect DOCX MathType/OMML counts.")
    inspect.add_argument("input", type=Path, help="Input DOCX path.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "mathml":
        options = _options(args)
        mathml = args.input.read_text(encoding="utf-8")
        if args.omml:
            args.omml.parent.mkdir(parents=True, exist_ok=True)
            args.omml.write_bytes(mathml_to_omml_xml(mathml, display=True, options=options.omml))
            print(f"OMML written to: {args.omml}")
        if args.mtef:
            args.mtef.parent.mkdir(parents=True, exist_ok=True)
            args.mtef.write_bytes(mathml_to_mtef(mathml, options))
            print(f"MTEF written to: {args.mtef}")
        if args.ole:
            args.ole.parent.mkdir(parents=True, exist_ok=True)
            args.ole.write_bytes(mathml_to_mathtype_ole(mathml, options))
            streams, native_len = _inspect_ole(args.ole)
            print(f"OLE object written to: {args.ole}")
            print(f"OLE streams: {', '.join(streams)}")
            print(f"Equation Native length: {native_len}")
        if not args.omml and not args.mtef and not args.ole:
            raise SystemExit("--omml, --mtef, or --ole is required for the mathml command.")
        return

    if args.command == "demo":
        options = _options(args)
        equations = [path.read_text(encoding="utf-8") for path in args.mathml]
        summary = build_equation_docx(equations, args.output, options)
        print(f"DOCX written to: {args.output}")
        print(f"Equations: {summary.converted}/{summary.found}")
        return

    if args.command == "latex-demo":
        build_demo_docx(args.formula, args.output, args.mathtype_version)
        print(f"Demo DOCX written to: {args.output}")
        return

    if args.command == "convert":
        options = _options(args, target="mathtype", display_layout=args.display_layout)
        summary = convert_docx(args.input, args.output, options)
        print(f"Converted DOCX written to: {args.output}")
        print(f"Equations: {summary.converted}/{summary.found}")
        return

    if args.command == "inspect":
        for key, value in inspect_docx(args.input).items():
            print(f"{key}: {value}")


def _add_common_options(parser: argparse.ArgumentParser, *, include_target: bool = True) -> None:
    if include_target:
        parser.add_argument("--target", choices=["omml", "mathtype"], default="mathtype")
    parser.add_argument("--mathtype-version", choices=["DSMT4", "DSMT6"], default="DSMT4")
    parser.add_argument("--embed-mode", choices=["alternate-content", "png-preview"], default="alternate-content")
    parser.add_argument("--font-family", default="Times New Roman")
    parser.add_argument("--east-asia-font", default="SimSun")
    parser.add_argument("--font-size", type=float, default=10.5)
    parser.add_argument("--number-font-size", type=float, default=10.5)
    parser.add_argument("--chapter", type=int)
    parser.add_argument("--number-format", choices=["(1)", "(1SEP1)"], default="(1SEP1)")
    parser.add_argument("--number-separator", default="-")
    parser.add_argument("--inline-height", type=float, default=12.5)
    parser.add_argument("--display-height", type=float, default=21.0)
    parser.add_argument("--max-width", type=float, default=360.0)
    parser.add_argument("--preview-font-px", type=int, default=38)


def _options(args: argparse.Namespace, *, target: str | None = None, display_layout: str = "tabbed") -> ExportOptions:
    style = EquationStyle(
        font_family=args.font_family,
        east_asia_font=args.east_asia_font,
        font_size_pt=args.font_size,
        number_font_size_pt=args.number_font_size,
    )
    numbering = NumberingOptions(
        chapter=getattr(args, "chapter", None),
        number_format=args.number_format,
        separator=args.number_separator,
    )
    mathtype = MathTypeOptions(
        embed_mode=args.embed_mode,
        mathtype_version=args.mathtype_version,
        inline_height_pt=args.inline_height,
        display_height_pt=args.display_height,
        max_width_pt=args.max_width,
        preview_font_px=args.preview_font_px,
    )
    omml = OmmlOptions(font_family=args.font_family, east_asia_font=args.east_asia_font)
    return ExportOptions(
        target=target or getattr(args, "target", "mathtype"),
        display_layout=display_layout,
        style=style,
        numbering=numbering,
        omml=omml,
        mathtype=mathtype,
    )


def _inspect_ole(path: Path) -> tuple[list[str], int]:
    ole = olefile.OleFileIO(str(path))
    try:
        streams = ["/".join(item) for item in ole.listdir(streams=True, storages=False)]
        native = ole.openstream(["Equation Native"]).read()
        return streams, len(native)
    finally:
        ole.close()


__all__ = ["build_parser", "main"]
