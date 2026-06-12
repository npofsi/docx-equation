from __future__ import annotations

from dataclasses import dataclass
import unicodedata
from typing import Iterable, Protocol


class Expr(Protocol):
    def encode(self) -> bytes: ...


@dataclass(frozen=True)
class Sequence:
    items: tuple[Expr, ...]

    def encode(self) -> bytes:
        return b"".join(item.encode() for item in self.items)


@dataclass(frozen=True)
class Text:
    value: str

    def encode(self) -> bytes:
        return b"".join(_encode_char(char) for char in self.value)


@dataclass(frozen=True)
class Symbol:
    value: str

    def encode(self) -> bytes:
        return _encode_char(self.value)


@dataclass(frozen=True)
class Fraction:
    numerator: Expr
    denominator: Expr
    slashed: bool = False

    def encode(self) -> bytes:
        variation = 0x02 if self.slashed else 0x00
        return _template(0x0B, variation, 0) + _line(self.numerator) + _line(self.denominator) + b"\x00"


@dataclass(frozen=True)
class Sqrt:
    radicand: Expr
    index: Expr | None = None

    def encode(self) -> bytes:
        variation = 0x01 if self.index is not None else 0x00
        return _template(0x0A, variation, 0) + _line(self.radicand) + _maybe_line(self.index) + b"\x00"


@dataclass(frozen=True)
class Fence:
    body: Expr
    left: str = "("
    right: str = ")"

    def encode(self) -> bytes:
        selector = _FENCE_SELECTOR.get((self.left, self.right))
        if selector is None:
            return seq([Symbol(self.left), self.body, Symbol(self.right)]).encode()
        return _template(selector, 0x03, 0) + _line(self.body) + Symbol(self.left).encode() + Symbol(self.right).encode() + b"\x00"


@dataclass(frozen=True)
class Overbar:
    body: Expr

    def encode(self) -> bytes:
        return _template(0x0D, 0, 0) + _line(self.body) + b"\x00"


@dataclass(frozen=True)
class Underbar:
    body: Expr

    def encode(self) -> bytes:
        return _template(0x0C, 0, 0) + _line(self.body) + b"\x00"


@dataclass(frozen=True)
class Hat:
    body: Expr
    kind: str = "hat"

    def encode(self) -> bytes:
        selector = {"vector": 0x1F, "tilde": 0x20, "hat": 0x21}.get(self.kind, 0x21)
        variation = 0x02 if self.kind == "vector" else 0x00
        return _template(selector, variation, 0) + _line(self.body) + b"\x00"


@dataclass(frozen=True)
class Matrix:
    rows: tuple[tuple[Expr, ...], ...]

    def encode(self) -> bytes:
        row_count = len(self.rows)
        col_count = max((len(row) for row in self.rows), default=0)
        row_parts = _partition_bytes(row_count + 1)
        col_parts = _partition_bytes(col_count + 1)
        data = bytearray([0x05, 0x00, 0x03, 0x02, 0x03, row_count, col_count])
        data.extend(row_parts)
        data.extend(col_parts)
        for row in self.rows:
            padded = list(row) + [Text("")] * (col_count - len(row))
            for cell in padded:
                data.extend(_line(cell))
        data.append(0)
        return bytes(data)


@dataclass(frozen=True)
class Pile:
    lines: tuple[Expr, ...]

    def encode(self) -> bytes:
        data = bytearray([0x04, 0x00, 0x02, 0x01])
        for line in self.lines:
            data.extend(_line(line))
        data.append(0)
        return bytes(data)


@dataclass(frozen=True)
class Subscript:
    base: Expr
    subscript: Expr

    def encode(self) -> bytes:
        return self.base.encode() + b"\x03\x00\x1b\x00\x00\x0b" + _line(self.subscript) + _empty_line() + b"\x0a"


@dataclass(frozen=True)
class Superscript:
    base: Expr
    superscript: Expr

    def encode(self) -> bytes:
        return self.base.encode() + b"\x03\x00\x1c\x00\x00\x0b" + _empty_line() + _line(self.superscript) + b"\x00\x0a"


@dataclass(frozen=True)
class Subsup:
    base: Expr
    subscript: Expr
    superscript: Expr

    def encode(self) -> bytes:
        return self.base.encode() + _template(0x1D, 0, 0) + b"\x0b" + _line(self.subscript) + _line(self.superscript) + b"\x00\x0a"


@dataclass(frozen=True)
class BigOperator:
    operator: str
    body: Expr = Text("")
    lower: Expr | None = None
    upper: Expr | None = None

    def encode(self) -> bytes:
        selector, base_variation = _BIG_OPERATOR_TEMPLATE.get(self.operator, (0x16, 0x40))
        variation = base_variation
        if self.lower is not None:
            variation |= 0x01
        if self.upper is not None:
            variation |= 0x02
        return (
            _template(selector, variation, 0)
            + _line(self.body)
            + _maybe_line(self.upper)
            + _maybe_line(self.lower)
            + Symbol(self.operator).encode()
            + b"\x00"
        )


def seq(items: Iterable[Expr]) -> Expr:
    flattened: list[Expr] = []
    for item in items:
        if isinstance(item, Sequence):
            flattened.extend(item.items)
        else:
            flattened.append(item)
    if len(flattened) == 1:
        return flattened[0]
    return Sequence(tuple(flattened))


def encode_mtef(expr: Expr, mathtype_version: str = "DSMT4") -> bytes:
    return _preamble(mathtype_version) + b"\x0a" + _line(expr) + b"\x00"


def _line(expr: Expr) -> bytes:
    return b"\x01\x00" + expr.encode() + b"\x00"


def _empty_line() -> bytes:
    return b"\x01\x01\x00"


def _maybe_line(expr: Expr | None) -> bytes:
    return _line(expr) if expr is not None else _empty_line()


def _template(selector: int, variation: int, options: int) -> bytes:
    if variation >= 0x80:
        variation_bytes = bytes([(variation & 0x7F) | 0x80, variation >> 7])
    else:
        variation_bytes = bytes([variation])
    return bytes([0x03, 0x00, selector]) + variation_bytes + bytes([options])


def _partition_bytes(count: int) -> bytes:
    return bytes((count * 2 + 7) // 8)


def _preamble(mathtype_version: str) -> bytes:
    version = mathtype_version.upper()
    if version not in {"DSMT4", "DSMT6"}:
        raise ValueError(f"Unsupported MathType version: {mathtype_version}")
    return b"".join(
        [
            b"\x05\x01\x00\x06\x09" + version.encode("ascii") + b"\x00\x01",
            b"\x13WinAllBasicCodePages\x00",
            _font_def(5, "Arial"),
            _font_def(3, "Symbol"),
            _font_def(5, "Courier New"),
            _font_def(5, "Times New Roman"),
            _font_def(4, "MT Extra Tiger"),
            _equation_preferences(),
        ]
    )


def _font_def(style: int, name: str) -> bytes:
    return bytes([0x11, style]) + name.encode("ascii") + b"\x00"


def _equation_preferences() -> bytes:
    return bytes.fromhex(
        "12 00 08 21 2f 45 8f 44 2f 41 50 f4 10 0f 47 5f"
        "41 50 f2 1f 1e 41 00 f4 10 0f 42 00 f4 45 f4 25"
        "f4 8f 42 5f 41 00 f4 10 0f 43 5f 41 00 f2 1f 20"
        "a5 f2 0a 25 f4 8f 21 f4 10 0f 41 00 f4 0f 48 f4"
        "17 f4 8f 41 00 f2 1a 5f 44 5f 45 f4 5f 45 f4 5f"
        "41 0f 0c 01 00 01 00 01 02 02 02 02 00 02 00 01"
        "01 01 00 03 00 04 00 05 00 00"
    )


_OPERATOR_CODE = {
    "+": (0x002B, 0x2B),
    "=": (0x003D, 0x3D),
    "*": (0x002A, 0x2A),
    "/": (0x002F, 0x2F),
    ">": (0x003E, 0x3E),
    "<": (0x003C, 0x3C),
    "-": (0x2212, 0x2D),
    "\u2212": (0x2212, 0x2D),
    "\u00d7": (0x00D7, 0xB4),
    "\u00f7": (0x00F7, 0xB8),
}

_FENCE_SELECTOR = {
    ("(", ")"): 0x01,
    ("{", "}"): 0x02,
    ("[", "]"): 0x03,
    ("|", "|"): 0x04,
    ("||", "||"): 0x05,
    ("\u230a", "\u230b"): 0x06,
    ("\u2308", "\u2309"): 0x07,
}

_BIG_OPERATOR_TEMPLATE = {
    "\u222b": (0x0F, 0x01),
    "\u222c": (0x0F, 0x02),
    "\u222d": (0x0F, 0x03),
    "\u2211": (0x10, 0x40),
    "\u220f": (0x11, 0x40),
    "\u2210": (0x12, 0x40),
    "\u22c3": (0x13, 0x40),
    "\u22c2": (0x14, 0x40),
}


def _encode_char(char: str) -> bytes:
    if len(char) != 1:
        return b"".join(_encode_char(item) for item in char)
    if char == "\u00a0":
        char = " "
    if char in _OPERATOR_CODE:
        unicode_code, mt_code = _OPERATOR_CODE[char]
        return bytes([0x02, 0x04, 0x86]) + unicode_code.to_bytes(2, "little") + bytes([mt_code])
    if char.isdigit():
        typeface = 0x88
    elif char.isalpha():
        typeface = 0x83
    elif char in "()[]{}.,;:":
        typeface = 0x82
    elif char.isspace():
        typeface = 0x86
    elif unicodedata.category(char).startswith(("S", "M")):
        typeface = 0x86
    else:
        typeface = 0x83
    code_point = ord(char)
    if code_point > 0xFFFF:
        raise ValueError(f"Character outside BMP is not supported yet: {char!r}")
    return bytes([0x02, 0x00, typeface]) + code_point.to_bytes(2, "little")
