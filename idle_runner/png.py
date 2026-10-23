"""Minimal PNG writer (stdlib only) for debug frame dumps."""
import struct
import zlib
from pathlib import Path

import numpy as np


def _chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))


def write_png(path: Path, rgb: np.ndarray) -> None:
    """Write an (h, w, 3) uint8 RGB array as an 8-bit truecolor PNG."""
    height, width, _ = rgb.shape
    # Each scanline starts with filter type 0 (none).
    raw = b"".join(b"\x00" + rgb[y].tobytes() for y in range(height))
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", header) + _chunk(b"IDAT", zlib.compress(raw, 6)) + _chunk(b"IEND", b"")
    path.write_bytes(png)
