from __future__ import annotations

import struct

from .cfb import write_cfb


def build_mathtype_ole_object(mtef: bytes) -> bytes:
    return write_cfb(
        {
            "\x01CompObj": _compobj_stream(),
            "\x01Ole": _ole_stream(),
            "\x03ObjInfo": _obj_info_stream(),
            "Equation Native": _equation_native_stream(mtef),
        }
    )


def _equation_native_stream(mtef: bytes) -> bytes:
    header = bytearray.fromhex(
        "1c 00 00 00 02 00 32 c3"
        "00 00 00 00"
        "34 0b aa 00 00 c7 54 00 00 00 00 00 f4 0a aa 00"
    )
    header[8:12] = struct.pack("<I", len(mtef))
    return bytes(header) + mtef


def _ole_stream() -> bytes:
    return bytes.fromhex("01 00 00 02 08 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00")


def _obj_info_stream() -> bytes:
    return bytes.fromhex("00 00 03 00 01 00")


def _compobj_stream() -> bytes:
    return b"".join(
        [
            bytes.fromhex("01 00 fe ff 03 0a 00 00 ff ff ff ff"),
            bytes.fromhex("03 ce 02 00 00 00 00 00 c0 00 00 00 00 00 00 46"),
            _ansi_string("MathType 6.0 Equation"),
            _ansi_string("MathType EF"),
            _ansi_string("Equation.DSMT4"),
            bytes.fromhex("f4 39 b2 71 00 00 00 00 00 00 00 00 00 00 00 00"),
        ]
    )


def _ansi_string(value: str) -> bytes:
    data = value.encode("ascii") + b"\x00"
    return struct.pack("<I", len(data)) + data
