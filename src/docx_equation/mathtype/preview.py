from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def make_preview_png(label: str, output_path: str | Path, font_size: int = 36) -> tuple[int, int]:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    font = _font(font_size)
    text = _latex_preview_text(label)
    probe = Image.new("RGB", (10, 10), "white")
    draw = ImageDraw.Draw(probe)
    bbox = draw.textbbox((0, 0), text, font=font)
    width = max(80, bbox[2] - bbox[0] + 28)
    height = max(34, bbox[3] - bbox[1] + 22)
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((14, 9 - bbox[1]), text, fill="black", font=font)
    image.save(target)
    return width, height


def _latex_preview_text(source: str) -> str:
    result: list[str] = []
    index = 0
    while index < len(source):
        char = source[index]
        if source.startswith(r"\frac", index):
            numerator, index = _read_group(source, index + 5)
            denominator, index = _read_group(source, index)
            result.append(f"({_latex_preview_text(numerator)})/({_latex_preview_text(denominator)})")
        elif source.startswith(r"\sqrt", index):
            radicand, index = _read_group(source, index + 5)
            result.append(f"sqrt({_latex_preview_text(radicand)})")
        elif source.startswith(r"\times", index):
            result.append("\u00d7")
            index += 6
        elif source.startswith(r"\div", index):
            result.append("\u00f7")
            index += 4
        elif char in "_^":
            group, index = _read_script(source, index + 1)
            if len(group) == 1:
                result.append(f"{char}{_latex_preview_text(group)}")
            else:
                result.append(f"{char}({_latex_preview_text(group)})")
        elif char == "\\":
            name, index = _read_command(source, index + 1)
            result.append(name)
        elif char in "{}":
            index += 1
        else:
            result.append(char)
            index += 1
    return "".join(result)


def _read_script(source: str, index: int) -> tuple[str, int]:
    while index < len(source) and source[index].isspace():
        index += 1
    if index < len(source) and source[index] == "{":
        return _read_group(source, index)
    if index >= len(source):
        return "", index
    return source[index], index + 1


def _read_group(source: str, index: int) -> tuple[str, int]:
    while index < len(source) and source[index].isspace():
        index += 1
    if index >= len(source) or source[index] != "{":
        return "", index
    depth = 0
    start = index + 1
    while index < len(source):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index], index + 1
        index += 1
    return source[start:], len(source)


def _read_command(source: str, index: int) -> tuple[str, int]:
    start = index
    while index < len(source) and source[index].isalpha():
        index += 1
    if index == start and index < len(source):
        index += 1
    return source[start:index], index


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/Library/Fonts/Times New Roman.ttf",
        "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()
