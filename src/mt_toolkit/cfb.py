from __future__ import annotations

from dataclasses import dataclass
from math import ceil
import struct


FREESECT = 0xFFFFFFFF
ENDOFCHAIN = 0xFFFFFFFE
FATSECT = 0xFFFFFFFD
NOSTREAM = 0xFFFFFFFF

SECTOR_SIZE = 512
MINI_SECTOR_SIZE = 64
MINI_STREAM_CUTOFF = 4096


@dataclass(frozen=True)
class Stream:
    name: str
    data: bytes
    start_mini_sector: int


def write_cfb(streams: dict[str, bytes]) -> bytes:
    ordered = [
        Stream(name, data, 0)
        for name, data in streams.items()
    ]
    mini_stream = bytearray()
    updated: list[Stream] = []
    mini_fat_entries: list[int] = []

    for stream in ordered:
        start = len(mini_stream) // MINI_SECTOR_SIZE
        sectors = max(1, ceil(len(stream.data) / MINI_SECTOR_SIZE))
        padded = stream.data + b"\x00" * (sectors * MINI_SECTOR_SIZE - len(stream.data))
        mini_stream.extend(padded)
        for offset in range(sectors):
            if offset == sectors - 1:
                mini_fat_entries.append(ENDOFCHAIN)
            else:
                mini_fat_entries.append(start + offset + 1)
        updated.append(Stream(stream.name, stream.data, start))

    mini_stream_bytes = _pad(bytes(mini_stream), SECTOR_SIZE)
    mini_stream_sector_count = len(mini_stream_bytes) // SECTOR_SIZE
    mini_fat_bytes = _pack_sector_entries(mini_fat_entries)
    mini_fat_sector_count = len(mini_fat_bytes) // SECTOR_SIZE

    directory_bytes = _directory_stream(updated, root_start_sector=0, root_size=len(mini_stream))
    directory_sector_count = len(directory_bytes) // SECTOR_SIZE

    fat_sector_index = 0
    directory_start = 1
    mini_stream_start = directory_start + directory_sector_count
    mini_fat_start = mini_stream_start + mini_stream_sector_count
    sector_count = 1 + directory_sector_count + mini_stream_sector_count + mini_fat_sector_count
    directory_bytes = _directory_stream(updated, root_start_sector=mini_stream_start, root_size=len(mini_stream))

    fat_entries = [FREESECT] * (ceil(sector_count / 128) * 128)
    fat_entries[fat_sector_index] = FATSECT
    for index in range(directory_sector_count):
        sector = directory_start + index
        fat_entries[sector] = directory_start + index + 1 if index < directory_sector_count - 1 else ENDOFCHAIN
    for index in range(mini_stream_sector_count):
        sector = mini_stream_start + index
        fat_entries[sector] = mini_stream_start + index + 1 if index < mini_stream_sector_count - 1 else ENDOFCHAIN
    for index in range(mini_fat_sector_count):
        sector = mini_fat_start + index
        fat_entries[sector] = mini_fat_start + index + 1 if index < mini_fat_sector_count - 1 else ENDOFCHAIN

    fat_bytes = _pack_sector_entries(fat_entries[:128])
    header = _header(
        fat_sector_index=fat_sector_index,
        directory_start=directory_start,
        mini_fat_start=mini_fat_start,
        mini_fat_sector_count=mini_fat_sector_count,
    )

    return b"".join([header, fat_bytes, directory_bytes, mini_stream_bytes, mini_fat_bytes])


def _header(
    fat_sector_index: int,
    directory_start: int,
    mini_fat_start: int,
    mini_fat_sector_count: int,
) -> bytes:
    header = bytearray(SECTOR_SIZE)
    header[0:8] = bytes.fromhex("d0 cf 11 e0 a1 b1 1a e1")
    header[24:26] = struct.pack("<H", 0x003E)
    header[26:28] = struct.pack("<H", 0x0003)
    header[28:30] = struct.pack("<H", 0xFFFE)
    header[30:32] = struct.pack("<H", 9)
    header[32:34] = struct.pack("<H", 6)
    header[40:44] = struct.pack("<I", 0)
    header[44:48] = struct.pack("<I", 1)
    header[48:52] = struct.pack("<I", directory_start)
    header[52:56] = struct.pack("<I", 0)
    header[56:60] = struct.pack("<I", MINI_STREAM_CUTOFF)
    header[60:64] = struct.pack("<I", mini_fat_start)
    header[64:68] = struct.pack("<I", mini_fat_sector_count)
    header[68:72] = struct.pack("<I", ENDOFCHAIN)
    header[72:76] = struct.pack("<I", 0)
    header[76:80] = struct.pack("<I", fat_sector_index)
    for offset in range(80, SECTOR_SIZE, 4):
        header[offset:offset + 4] = struct.pack("<I", FREESECT)
    return bytes(header)


def _directory_stream(streams: list[Stream], root_start_sector: int, root_size: int) -> bytes:
    entries = [
        _directory_entry(
            "Root Entry",
            object_type=5,
            color=1,
            left=NOSTREAM,
            right=NOSTREAM,
            child=1 if streams else NOSTREAM,
            start_sector=root_start_sector,
            stream_size=root_size,
        )
    ]
    for index, stream in enumerate(streams, 1):
        right = index + 1 if index < len(streams) else NOSTREAM
        entries.append(
            _directory_entry(
                stream.name,
                object_type=2,
                color=1,
                left=NOSTREAM,
                right=right,
                child=NOSTREAM,
                start_sector=stream.start_mini_sector,
                stream_size=len(stream.data),
            )
        )
    while len(entries) % 4 != 0:
        entries.append(bytes(128))
    return b"".join(entries)


def _directory_entry(
    name: str,
    object_type: int,
    color: int,
    left: int,
    right: int,
    child: int,
    start_sector: int,
    stream_size: int,
) -> bytes:
    entry = bytearray(128)
    encoded_name = name.encode("utf-16le") + b"\x00\x00"
    if len(encoded_name) > 64:
        raise ValueError(f"CFB directory name is too long: {name!r}")
    entry[0:len(encoded_name)] = encoded_name
    entry[64:66] = struct.pack("<H", len(encoded_name))
    entry[66] = object_type
    entry[67] = color
    entry[68:72] = struct.pack("<I", left)
    entry[72:76] = struct.pack("<I", right)
    entry[76:80] = struct.pack("<I", child)
    entry[116:120] = struct.pack("<I", start_sector)
    entry[120:128] = struct.pack("<Q", stream_size)
    return bytes(entry)


def _pack_sector_entries(entries: list[int]) -> bytes:
    padded = list(entries)
    while len(padded) % 128 != 0:
        padded.append(FREESECT)
    return b"".join(struct.pack("<I", entry) for entry in padded)


def _pad(data: bytes, size: int) -> bytes:
    remainder = len(data) % size
    if remainder == 0:
        return data
    return data + b"\x00" * (size - remainder)
