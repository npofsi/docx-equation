from __future__ import annotations

import struct

from .cfb import write_cfb


def build_mathtype_ole_object(mtef: bytes, prog_id: str = "Equation.DSMT4") -> bytes:
    return write_cfb(
        {
            "\x01CompObj": _compobj_stream(prog_id),
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


def _compobj_stream(prog_id: str) -> bytes:
    version_label = "MathType 6.0 Equation" if prog_id.endswith("DSMT6") else "MathType Equation"
    return b"".join(
        [
            bytes.fromhex("01 00 fe ff 03 0a 00 00 ff ff ff ff"),
            bytes.fromhex("03 ce 02 00 00 00 00 00 c0 00 00 00 00 00 00 46"),
            _ansi_string(version_label),
            _ansi_string("MathType EF"),
            _ansi_string(prog_id),
            bytes.fromhex("f4 39 b2 71 00 00 00 00 00 00 00 00 00 00 00 00"),
        ]
    )


def _ansi_string(value: str) -> bytes:
    data = value.encode("ascii") + b"\x00"
    return struct.pack("<I", len(data)) + data
