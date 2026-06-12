from __future__ import annotations

import argparse
from pathlib import Path

import olefile

from mt_toolkit.application import (
    build_equation_docx,
    convert_docx,
    inspect_docx,
    mathml_to_mathtype_ole,
    mathml_to_mtef,
)
from mt_toolkit.docx_embed import build_demo_docx
from mt_toolkit.domain.models import ConversionOptions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MathType-compatible equation tools.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    mathml = subparsers.add_parser("mathml", help="Generate MTEF/OLE artifacts from MathML.")
    mathml.add_argument("input", type=Path, help="MathML input file.")
    mathml.add_argument("--ole", type=Path, help="Output OLE object path.")
    mathml.add_argument("--mtef", type=Path, help="Output raw MTEF path.")
    _add_common_options(mathml)

    demo = subparsers.add_parser("demo", help="Build a simple DOCX from MathML files.")
    demo.add_argument("mathml", type=Path, nargs="+", help="One or more MathML files.")
    demo.add_argument("-o", "--output", type=Path, required=True, help="Output DOCX path.")
    _add_common_options(demo)

    latex_demo = subparsers.add_parser("latex-demo", help="Build the legacy LaTeX demo DOCX.")
    latex_demo.add_argument("formula", help="Formula in the supported LaTeX subset.")
    latex_demo.add_argument("-o", "--output", type=Path, required=True, help="Output DOCX path.")
    _add_common_options(latex_demo)

    convert = subparsers.add_parser("convert", help="Convert OMML equations in a DOCX for compatibility.")
    convert.add_argument("input", type=Path, help="Input DOCX path.")
    convert.add_argument("-o", "--output", type=Path, required=True, help="Output DOCX path.")
    convert.add_argument("--display-layout", choices=["preserve", "tabbed"], default="tabbed")
    _add_common_options(convert)

    inspect = subparsers.add_parser("inspect", help="Inspect DOCX MathType/OMML counts.")
    inspect.add_argument("input", type=Path, help="Input DOCX path.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "mathml":
        options = _options(args)
        mathml = args.input.read_text(encoding="utf-8")
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
        if not args.mtef and not args.ole:
            raise SystemExit("--mtef or --ole is required for the mathml command.")
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
        options = _options(args, display_layout=args.display_layout)
        summary = convert_docx(args.input, args.output, options)
        print(f"Converted DOCX written to: {args.output}")
        print(f"Equations: {summary.converted}/{summary.found}")
        return

    if args.command == "inspect":
        for key, value in inspect_docx(args.input).items():
            print(f"{key}: {value}")


def _add_common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--mathtype-version", choices=["DSMT4", "DSMT6"], default="DSMT4")
    parser.add_argument("--embed-mode", choices=["alternate-content", "png-preview"], default="alternate-content")


def _options(args: argparse.Namespace, display_layout: str = "tabbed") -> ConversionOptions:
    return ConversionOptions(
        embed_mode=args.embed_mode,
        mathtype_version=args.mathtype_version,
        display_layout=display_layout,
    )


def _inspect_ole(path: Path) -> tuple[list[str], int]:
    ole = olefile.OleFileIO(str(path))
    try:
        streams = ["/".join(item) for item in ole.listdir(streams=True, storages=False)]
        native = ole.openstream(["Equation Native"]).read()
        return streams, len(native)
    finally:
        ole.close()
