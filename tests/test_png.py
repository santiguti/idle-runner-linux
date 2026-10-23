import struct
import zlib

import numpy as np

from idle_runner.png import write_png


def test_write_png_roundtrip_from_a_reversed_view(tmp_path) -> None:
    bgr = np.array([[[0, 0, 255], [0, 255, 0], [255, 0, 0]],
                    [[3, 2, 1], [6, 5, 4], [9, 8, 7]]], dtype=np.uint8)
    rgb = bgr[:, :, ::-1]  # a non-contiguous view, like X11Backend.grab() returns
    path = tmp_path / "x.png"

    write_png(path, rgb)

    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">IIBB", data[16:26]) == (3, 2, 8, 2)  # width, height, bit depth, RGB
    idat_length = struct.unpack(">I", data[33:37])[0]
    raw = zlib.decompress(data[41:41 + idat_length])
    expected = np.ascontiguousarray(rgb)
    assert raw == b"\x00" + expected[0].tobytes() + b"\x00" + expected[1].tobytes()
