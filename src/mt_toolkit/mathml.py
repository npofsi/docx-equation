from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile

from lxml import etree

from .mtef import (
    BigOperator,
    Expr,
    Fence,
    Fraction,
    Hat,
    Matrix,
    Overbar,
    Pile,
    Sqrt,
    Subscript,
    Subsup,
    Superscript,
    Symbol,
    Text,
    Underbar,
    seq,
)


MATHML_NS = "http://www.w3.org/1998/Math/MathML"


def parse_mathml(data: bytes | str) -> Expr:
    if isinstance(data, str):
        data = data.encode("utf-8")
    parser = etree.XMLParser(resolve_entities=False, recover=True, remove_blank_text=True)
    root = etree.fromstring(data, parser)
    return _parse_element(root)


def parse_mathml_file(path: str | Path) -> Expr:
    return parse_mathml(Path(path).read_bytes())


def render_mathml_files(
    mathml_dir: str | Path,
    output_dir: str | Path,
    chrome_path: str | Path | None = None,
    font_px: int = 38,
) -> int:
    chrome = _find_chrome(chrome_path)
    source_dir = Path(mathml_dir)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(source_dir.glob("equation_*.mml"))
    if not files:
        raise FileNotFoundError(f"No MathML files found in: {source_dir}")

    with tempfile.TemporaryDirectory(prefix="mt_toolkit_mathml_") as tmp:
        tmp_dir = Path(tmp)
        for source in files:
            html_path = tmp_dir / f"{source.stem}.html"
            raw_png = tmp_dir / f"{source.stem}.raw.png"
            final_png = target_dir / f"{source.stem}.png"
            html_path.write_text(_html(source.read_text(encoding="utf-8"), font_px), encoding="utf-8")
            subprocess.run(
                [
                    str(chrome),
                    "--headless=new",
                    "--disable-gpu",
                    "--hide-scrollbars",
                    "--force-device-scale-factor=2",
                    "--window-size=2600,700",
                    f"--screenshot={raw_png}",
                    html_path.resolve().as_uri(),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            _crop_png(raw_png, final_png)
    return len(files)


def _parse_element(element: etree._Element) -> Expr:
    tag = etree.QName(element).localname
    if tag in {"math", "mrow", "mstyle", "mpadded", "semantics"}:
        return _parse_children(element)
    if tag in {"mi", "mn", "mo", "mtext"}:
        return Text(_normalize_text("".join(element.itertext())))
    if tag == "mspace":
        return Text(" ")
    if tag == "msub" and len(element) >= 2:
        return Subscript(_parse_element(element[0]), _parse_element(element[1]))
    if tag == "msup" and len(element) >= 2:
        return Superscript(_parse_element(element[0]), _parse_element(element[1]))
    if tag == "msubsup" and len(element) >= 3:
        return Subsup(_parse_element(element[0]), _parse_element(element[1]), _parse_element(element[2]))
    if tag == "mfrac" and len(element) >= 2:
        slashed = element.get("bevelled") == "true"
        return Fraction(_parse_element(element[0]), _parse_element(element[1]), slashed=slashed)
    if tag == "msqrt":
        return Sqrt(_parse_children(element))
    if tag == "mroot" and len(element) >= 2:
        return Sqrt(_parse_element(element[0]), _parse_element(element[1]))
    if tag == "munder" and len(element) >= 2:
        operator = _big_operator_text(element[0])
        if operator:
            return BigOperator(operator, lower=_parse_element(element[1]))
        if _operator_text(element[1]) in {"\u0332", "\u005f", "\u2015", "\u203e"}:
            return Underbar(_parse_element(element[0]))
        return Subscript(_parse_element(element[0]), _parse_element(element[1]))
    if tag == "mover" and len(element) >= 2:
        operator = _big_operator_text(element[0])
        if operator:
            return BigOperator(operator, upper=_parse_element(element[1]))
        accent = _operator_text(element[1])
        if accent in {"\u00af", "\u203e", "\u0305"}:
            return Overbar(_parse_element(element[0]))
        if accent in {"^", "\u02c6", "\u0302"}:
            return Hat(_parse_element(element[0]), "hat")
        if accent in {"~", "\u02dc", "\u0303"}:
            return Hat(_parse_element(element[0]), "tilde")
        if accent in {"\u2192", "\u20d7"}:
            return Hat(_parse_element(element[0]), "vector")
        return Superscript(_parse_element(element[0]), _parse_element(element[1]))
    if tag == "munderover" and len(element) >= 3:
        operator = _big_operator_text(element[0])
        if operator:
            return BigOperator(operator, lower=_parse_element(element[1]), upper=_parse_element(element[2]))
        return Subsup(_parse_element(element[0]), _parse_element(element[1]), _parse_element(element[2]))
    if tag == "mfenced":
        open_char = element.get("open", "(")
        close_char = element.get("close", ")")
        return Fence(_parse_children(element), open_char, close_char)
    if tag == "mtable":
        rows: list[tuple[Expr, ...]] = []
        for row in element:
            local = etree.QName(row).localname
            if local in {"mtr", "mlabeledtr"}:
                rows.append(tuple(_parse_element(cell) for cell in row if etree.QName(cell).localname == "mtd"))
        return Matrix(tuple(rows)) if rows else Text("")
    if tag in {"mstack", "mlongdiv", "mscarries"}:
        return Pile(tuple(_parse_element(child) for child in element))
    if tag in {"mtr", "mlabeledtr"}:
        cells = []
        for cell in element:
            cells.append(_parse_element(cell))
            cells.append(Symbol(","))
        return seq(cells[:-1] if cells else [])
    if tag == "mtd":
        return _parse_children(element)
    if tag == "menclose":
        notation = element.get("notation", "")
        body = _parse_children(element)
        if "top" in notation or "actuarial" in notation or "overline" in notation:
            return Overbar(body)
        if "bottom" in notation or "underline" in notation:
            return Underbar(body)
        if "box" in notation or "roundedbox" in notation:
            return Fence(body, "[", "]")
        return body
    return _parse_children(element)


def _parse_children(element: etree._Element) -> Expr:
    return seq(_parse_element(child) for child in element if etree.QName(child).localname != "annotation")


def _normalize_text(text: str) -> str:
    return text.replace("\u00a0", " ")


def _operator_text(element: etree._Element) -> str:
    tag = etree.QName(element).localname
    if tag in {"mo", "mi", "mn", "mtext"}:
        return _normalize_text("".join(element.itertext())).strip()
    if len(element) == 1:
        return _operator_text(element[0])
    return ""


def _big_operator_text(element: etree._Element) -> str:
    text = _operator_text(element)
    return text if text in {"\u222b", "\u222c", "\u222d", "\u2211", "\u220f", "\u2210", "\u22c3", "\u22c2"} else ""


def _find_chrome(chrome_path: str | Path | None = None) -> Path:
    if chrome_path:
        candidate = Path(chrome_path)
        if candidate.exists():
            return candidate
        raise FileNotFoundError(f"Chrome executable not found: {candidate}")
    candidates = [
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        shutil.which("microsoft-edge"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return Path(candidate)
    raise FileNotFoundError("No Chrome/Chromium executable was found for MathML rendering.")


def _html(mathml: str, font_px: int) -> str:
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    html, body {{ margin: 0; padding: 0; background: #fff; }}
    .box {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 26px;
      background: #fff;
    }}
    math {{
      font-family: "Times New Roman", "STIX Two Math", "Cambria Math", serif;
      font-size: {font_px}px;
      math-style: normal;
    }}
  </style>
</head>
<body><div class="box">{mathml}</div></body>
</html>
"""


def _crop_png(source: Path, target: Path, padding_px: int = 8) -> None:
    from PIL import Image, ImageChops

    image = Image.open(source).convert("RGB")
    white = Image.new("RGB", image.size, "white")
    diff = ImageChops.difference(image, white)
    mask = diff.convert("L").point(lambda value: 255 if value > 12 else 0)
    bbox = mask.getbbox()
    if bbox is None:
        image.save(target)
        return
    left = max(0, bbox[0] - padding_px)
    top = max(0, bbox[1] - padding_px)
    right = min(image.size[0], bbox[2] + padding_px)
    bottom = min(image.size[1], bbox[3] + padding_px)
    image.crop((left, top, right, bottom)).save(target)
