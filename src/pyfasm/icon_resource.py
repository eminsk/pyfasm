"""
Portable PE64 icon resource (``.rsrc``) generation for PyFASM.

The classic FASM ``icon`` macro (``include/macro/resource.inc``) reads the
``.ico`` file at assembly time via ``file icon_file:offset,size``. That couples
the generated assembly to the location of the icon on disk and relies on the
host FASM build supporting offset reads; the bundled macOS FASM build fails
with ``error reading file.`` on exactly that construct.

This module parses the ``.ico`` container in Python and emits the ``RT_ICON``
and ``RT_GROUP_ICON`` resources as inline ``db``/``dw``/``dd`` data. The
resulting assembly is self-contained, identical on every host OS, and needs no
external icon file at assembly time.
"""
from __future__ import annotations

import struct
from pathlib import Path
from typing import List, Tuple, Union

# (width, height, color_count, reserved, planes, bit_count, image_bytes)
IconImage = Tuple[int, int, int, int, int, int, bytes]

_ICO_HEADER = struct.Struct("<HHH")
_ICO_ENTRY = struct.Struct("<BBBBHHII")
_BYTES_PER_LINE = 32


def parse_ico(data: bytes) -> List[IconImage]:
    """Parses an ``.ico`` container and returns its valid images.

    Entries whose image data lies outside the file are skipped. Returns an
    empty list if ``data`` is not an icon container.
    """
    if len(data) < _ICO_HEADER.size:
        return []
    reserved, res_type, count = _ICO_HEADER.unpack_from(data, 0)
    if reserved != 0 or res_type != 1 or count == 0:
        return []
    images: List[IconImage] = []
    for i in range(count):
        entry_off = _ICO_HEADER.size + i * _ICO_ENTRY.size
        if entry_off + _ICO_ENTRY.size > len(data):
            break
        w, h, colors, res, planes, bpp, size, offset = _ICO_ENTRY.unpack_from(data, entry_off)
        if size == 0 or offset + size > len(data):
            continue
        images.append((w, h, colors, res, planes, bpp, data[offset:offset + size]))
    return images


def _db_lines(blob: bytes) -> List[str]:
    return [
        "    db " + ",".join(str(b) for b in blob[i:i + _BYTES_PER_LINE])
        for i in range(0, len(blob), _BYTES_PER_LINE)
    ]


def build_icon_rsrc_section(icon: Union[str, Path, bytes, None], prefix: str = "_pyfasm") -> str:
    """Builds a complete FASM ``.rsrc`` section embedding the given icon.

    ``icon`` may be a path to an ``.ico`` file or the raw file bytes.
    Returns an empty string if the icon is missing or not a valid ``.ico``.
    """
    if icon is None:
        return ""
    if isinstance(icon, (bytes, bytearray)):
        data = bytes(icon)
    else:
        try:
            data = Path(icon).read_bytes()
        except OSError:
            return ""
    images = parse_ico(data)
    if not images:
        return ""

    count = len(images)
    icon_ids = ", ".join(f"{i}, 0, {prefix}_icon_data_{i}" for i in range(1, count + 1))
    lines: List[str] = [
        "include 'macro/resource.inc'",
        "",
        "section '.rsrc' resource data readable",
        "",
        f"directory 3, {prefix}_icons, 14, {prefix}_group_icons",
        "",
        f"resource {prefix}_icons, {icon_ids}",
        f"resource {prefix}_group_icons, 1, 0, {prefix}_main_icon",
        "",
        f"; icon {prefix}_main_icon: {count} image(s) embedded inline (no external .ico needed at assembly time)",
    ]
    for i, (_w, _h, _c, _r, _p, _b, blob) in enumerate(images, start=1):
        lines.append(f"{prefix}_icon_data_{i} dd RVA {prefix}_icon_bits_{i}, {len(blob)}, 0, 0")
        lines.append(f"{prefix}_icon_bits_{i}:")
        lines.extend(_db_lines(blob))
        lines.append("    align 4")

    lines.append(f"{prefix}_main_icon dd RVA {prefix}_icon_group_hdr, {6 + count * 14}, 0, 0")
    lines.append(f"{prefix}_icon_group_hdr:")
    lines.append(f"    dw 0, 1, {count}")
    for i, (w, h, colors, res, planes, bpp, blob) in enumerate(images, start=1):
        lines.append(f"    db {w}, {h}, {colors}, {res}")
        lines.append(f"    dw {planes}, {bpp}")
        lines.append(f"    dd {len(blob)}")
        lines.append(f"    dw {i}")
    lines.append("    align 4")
    lines.append("")
    return "\n".join(lines)
