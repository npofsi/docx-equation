from __future__ import annotations

import argparse
from pathlib import Path

import olefile

from .convert_docx import convert_omml_docx_to_mathtype
from .docx_embed import build_demo_docx
from .latex import parse_latex_subset
from .mtef import encode_mtef
from .ole import build_mathtype_ole_object


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate MathType-compatible Equation.DSMT4 objects.")
    parser.add_argument("formula", nargs="?", help="Formula in the supported LaTeX subset.")
    parser.add_argument("--out", type=Path, default=Path("mt_toolkit_output"), help="Output directory.")
    parser.add_argument("--ole", type=Path, help="Optional output path for oleObject.bin.")
    parser.add_argument("--mtef", type=Path, help="Optional output path for raw MTEF bytes.")
    parser.add_argument("--docx", type=Path, help="Optional output path for a demo DOCX containing the generated OLE object.")
    parser.add_argument("--convert-docx", type=Path, help="Input DOCX whose OMML equations should be replaced by legacy MathType OLE objects.")
    parser.add_argument("--converted-docx", type=Path, help="Output DOCX for --convert-docx.")
    parser.add_argument("--work-dir", type=Path, help="Keep intermediate MathML, preview PNG, and OLE files in this directory.")
    parser.add_argument("--inline-height-pt", type=float, default=12.5, help="Target height for inline equation previews.")
    parser.add_argument("--display-height-pt", type=float, default=21.0, help="Target height for display equation previews.")
    parser.add_argument("--max-width-pt", type=float, default=360.0, help="Maximum width for equation previews.")
    parser.add_argument(
        "--preview-pt-per-px",
        type=float,
        default=0.15,
        help="Uniform Word point scale for rendered MathML previews; use a negative value to fall back to fixed-height sizing.",
    )
    parser.add_argument(
        "--display-layout",
        choices=["preserve", "tabbed"],
        default="preserve",
        help="Use 'tabbed' to replace three-cell display-equation tables with MathType-style center/right tab stops.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    if args.convert_docx:
        if not args.converted_docx:
            raise SystemExit("--converted-docx is required when --convert-docx is used.")
        count = convert_omml_docx_to_mathtype(
            args.convert_docx,
            args.converted_docx,
            work_dir=args.work_dir or args.out / "docx_convert",
            inline_height_pt=args.inline_height_pt,
            display_height_pt=args.display_height_pt,
            max_width_pt=args.max_width_pt,
            preview_pt_per_px=args.preview_pt_per_px if args.preview_pt_per_px >= 0 else None,
            display_layout=args.display_layout,
        )
        print(f"Converted DOCX written to: {args.converted_docx}")
        print(f"Converted equations: {count}")
        return

    if not args.formula:
        raise SystemExit("A formula is required unless --convert-docx is used.")

    expr = parse_latex_subset(args.formula)
    mtef = encode_mtef(expr)
    ole = build_mathtype_ole_object(mtef)

    mtef_path = args.mtef or args.out / "equation.mtef"
    ole_path = args.ole or args.out / "oleObject1.bin"
    docx_path = args.docx
    mtef_path.parent.mkdir(parents=True, exist_ok=True)
    ole_path.parent.mkdir(parents=True, exist_ok=True)
    mtef_path.write_bytes(mtef)
    ole_path.write_bytes(ole)

    streams, native_len = _inspect_ole(ole_path)
    print(f"MTEF written to: {mtef_path}")
    print(f"OLE object written to: {ole_path}")
    print(f"OLE streams: {', '.join(streams)}")
    print(f"Equation Native length: {native_len}")

    if docx_path:
        build_demo_docx(args.formula, docx_path)
        print(f"Demo DOCX written to: {docx_path}")


def _inspect_ole(path: Path) -> tuple[list[str], int]:
    ole = olefile.OleFileIO(str(path))
    try:
        streams = ["/".join(item) for item in ole.listdir(streams=True, storages=False)]
        native = ole.openstream(["Equation Native"]).read()
        return streams, len(native)
    finally:
        ole.close()
