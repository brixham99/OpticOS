#!/usr/bin/env python3
"""Convert fonts/optic8x8.txt to a 768-byte binary and a sample sheet.

The text file is the source of truth: 96 hand-authored 8x8 bitmaps,
codes 32-127, '#' ink and '.' paper. This script does not invent or
trace glyphs.

Packed layout (the usual 8-byte-per-glyph row format a 32-column
print routine would use): glyph for code C is 8 bytes at
    8 * (C - 32)
Each byte is one row, bit 7 is the leftmost pixel.

Not wired into the ROM. Run from the repo root or from fonts/:

    python3 fonts/make_optic8x8.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
SRC = HERE / "optic8x8.txt"
BIN = HERE / "optic8x8.bin"
PYMOD = HERE / "optic8x8.py"
SHEET = HERE / "optic8x8_sheet.png"

HEADER_RE = re.compile(r"^U\+([0-9A-Fa-f]{4}) \((\d+)\)(?:\s+(.*))?$")


def zx(colour: int, bright: bool = False) -> tuple[int, int, int]:
    """Spectrum palette: colour 0-7, optional bright (0xFF vs 0xD7)."""
    v = 0xFF if bright else 0xD7
    return (
        v if colour & 2 else 0,
        v if colour & 4 else 0,
        v if colour & 1 else 0,
    )


def parse(path: Path) -> dict[int, list[str]]:
    glyphs: dict[int, list[str]] = {}
    lines = path.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip("\n")
        if not line or line.lstrip().startswith("#"):
            i += 1
            continue
        m = HEADER_RE.match(line)
        if not m:
            raise ValueError(f"{path}:{i+1}: expected glyph header, got {line!r}")
        code = int(m.group(2))
        if int(m.group(1), 16) != code:
            raise ValueError(f"{path}:{i+1}: U+ and decimal code disagree")
        rows: list[str] = []
        for r in range(8):
            i += 1
            if i >= len(lines):
                raise ValueError(f"{path}: glyph {code} truncated")
            row = lines[i].strip()
            if len(row) != 8 or any(ch not in "#." for ch in row):
                raise ValueError(
                    f"{path}:{i+1}: glyph {code} row {r} must be 8 of '#'/'.', got {row!r}"
                )
            rows.append(row)
        if code in glyphs:
            raise ValueError(f"duplicate glyph {code}")
        glyphs[code] = rows
        i += 1
    missing = [c for c in range(32, 128) if c not in glyphs]
    extra = sorted(c for c in glyphs if c < 32 or c > 127)
    if missing or extra:
        raise ValueError(f"need codes 32-127; missing={missing} extra={extra}")
    return glyphs


def rows_to_bytes(rows: list[str]) -> bytes:
    out = bytearray(8)
    for r, row in enumerate(rows):
        b = 0
        for ch in row:
            b = (b << 1) | (1 if ch == "#" else 0)
        out[r] = b
    return bytes(out)


def pack(glyphs: dict[int, list[str]]) -> bytes:
    return b"".join(rows_to_bytes(glyphs[c]) for c in range(32, 128))


def validate(glyphs: dict[int, list[str]]) -> list[str]:
    """Soft metric warnings — not errors. Code 127 may fill the cell."""
    notes: list[str] = []
    letters_desc = set("gjpqy")  # two-row descenders (rows 6-7)
    marks_desc = set(",;_")      # punctuation that may use row 7
    descenders = letters_desc | marks_desc
    for code in range(32, 127):
        rows = glyphs[code]
        ch = chr(code)
        if any(row[0] == "#" for row in rows):
            notes.append(f"U+{code:04X} '{ch}' has ink in the left bearing (col 0)")
        if ch not in descenders and rows[7] != "........":
            notes.append(f"U+{code:04X} '{ch}' has ink in row 7 (not a descender)")
        if ch in descenders and rows[7] == "........":
            notes.append(f"U+{code:04X} '{ch}' is a descender but row 7 is empty")
        if ch in letters_desc and rows[6] == "........":
            notes.append(f"U+{code:04X} '{ch}' should use both descender rows 6-7")
        if ch.islower() and ch not in letters_desc:
            if rows[6] != "........" or rows[7] != "........":
                notes.append(f"U+{code:04X} '{ch}' should sit on baseline row 5 (no descender)")
    return notes


def write_pymod(blob: bytes, path: Path) -> None:
    hexes = ", ".join(f"0x{b:02X}" for b in blob)
    # wrap at 16 bytes (one pair of glyphs) per line
    parts = [f"0x{b:02X}" for b in blob]
    lines = []
    for i in range(0, len(parts), 16):
        lines.append("    " + ", ".join(parts[i : i + 16]) + ",")
    body = "\n".join(lines)
    path.write_text(
        f'''\
# Auto-generated from optic8x8.txt — do not edit by hand.
# 96 glyphs, codes 32-127, 8 bytes each (row-major, bit 7 = left).
# Clean-room original artwork. Not a Sinclair font and not for the ROM yet.

FONT = bytes((
{body}
))

assert len(FONT) == 768


def glyph(code: int) -> bytes:
    if not 32 <= code <= 127:
        raise ValueError(f"font covers 32-127, not {{code}}")
    o = 8 * (code - 32)
    return FONT[o : o + 8]


def rows(code: int) -> list[str]:
    out = []
    for b in glyph(code):
        out.append("".join("#" if b & (0x80 >> c) else "." for c in range(8)))
    return out
''',
        encoding="utf-8",
    )


def blit(
    im: Image.Image,
    glyphs: dict[int, list[str]],
    x: int,
    y: int,
    text: str,
    ink: tuple[int, int, int],
    paper: tuple[int, int, int] | None = None,
    scale: int = 1,
    unknown: str = "?",
) -> None:
    """Draw a string of 8x8 glyphs at pixel (x, y) in image space (already 1x)."""
    px, py = x, y
    for ch in text:
        code = ord(ch)
        if not 32 <= code <= 127:
            code = ord(unknown)
        rows = glyphs[code]
        for r, row in enumerate(rows):
            for c, bit in enumerate(row):
                colour = ink if bit == "#" else paper
                if colour is None:
                    continue
                if scale == 1:
                    im.putpixel((px + c, py + r), colour)
                else:
                    for dy in range(scale):
                        for dx in range(scale):
                            im.putpixel((px + c * scale + dx, py + r * scale + dy), colour)
        px += 8 * scale


def fill_rect(im: Image.Image, box, colour) -> None:
    ImageDraw.Draw(im).rectangle(box, fill=colour)



def draw_panel(
    im: Image.Image,
    glyphs: dict[int, list[str]],
    origin: tuple[int, int],
    ink: tuple[int, int, int],
    paper: tuple[int, int, int],
    border: tuple[int, int, int],
    scale: int,
) -> None:
    """One 256x192 Spectrum screen inside a 32x24 border (320x240)."""
    bw, bh = 32, 24
    inner_w, inner_h = 256, 192
    ox, oy = origin

    def S(x, y):
        return ox + x * scale, oy + y * scale

    fill_rect(
        im,
        [
            ox,
            oy,
            ox + (bw * 2 + inner_w) * scale - 1,
            oy + (bh * 2 + inner_h) * scale - 1,
        ],
        border,
    )
    ix, iy = S(bw, bh)
    fill_rect(
        im,
        [ix, iy, ix + inner_w * scale - 1, iy + inner_h * scale - 1],
        paper,
    )

    def text(col, row, s, ink_=ink, paper_=None):
        blit(
            im,
            glyphs,
            ix + col * 8 * scale,
            iy + row * 8 * scale,
            s,
            ink_,
            paper_,
            scale,
        )

    # Row 0: eight Spectrum colours, 4 cells each, with a contrasting
    # 1-pixel outline so blue is visible on blue paper and white is
    # visible on white paper. A nod to the OpticOS boot colour bar.
    outline = ink
    for c in range(8):
        colour = zx(c, bright=False)
        x0 = ix + c * 4 * 8 * scale
        y0 = iy
        x1 = x0 + 4 * 8 * scale - 1
        y1 = y0 + 8 * scale - 1
        fill_rect(im, [x0, y0, x1, y1], outline)
        fill_rect(
            im,
            [x0 + scale, y0 + scale, x1 - scale, y1 - scale],
            colour,
        )

    text(0, 1, "OpticOS 8x8")
    text(0, 2, "codes 32-127  clean-room")

    for gr in range(6):
        start = 32 + gr * 16
        text(0, 4 + gr, f"{start:3d} ")
        text(5, 4 + gr, "".join(chr(start + k) for k in range(16)))

    rule_y = 10 * 8 + 3
    rx, ry = ix, iy + rule_y * scale
    for x in range(inner_w * scale):
        im.putpixel((rx + x, ry), ink)

    samples = [
        (11, "OpticOS 128 BASIC"),
        (12, "The quick brown fox jumps over"),
        (13, "the lazy dog"),
        (14, '10 PRINT "HELLO": GOTO 10'),
        (15, "0123456789 !@#$%^&*()_+-="),
        (16, "[]{}|;':\",./<>? `~"),
        (18, "0O 1Il| 5S 8B  gjpqy"),
        (19, "aeoc  ft  @0O  AH  !@A$"),
    ]
    for row, line in samples:
        text(0, row, line)


def make_sheet(glyphs: dict[int, list[str]], path: Path, scale: int = 3) -> Image.Image:
    """Two 320x240 panels side by side: white on blue, black on white."""
    panel_w, panel_h = 320, 240
    gap = 8
    W = (panel_w * 2 + gap) * scale
    H = panel_h * scale
    im = Image.new("RGB", (W, H), (0x20, 0x20, 0x20))

    draw_panel(
        im,
        glyphs,
        (0, 0),
        ink=zx(7, bright=True),
        paper=zx(1, bright=False),
        border=zx(1, bright=True),
        scale=scale,
    )
    draw_panel(
        im,
        glyphs,
        ((panel_w + gap) * scale, 0),
        ink=zx(0, bright=False),
        paper=zx(7, bright=True),
        border=zx(7, bright=False),
        scale=scale,
    )
    im.save(path)
    return im


def preview_ascii(glyphs: dict[int, list[str]]) -> str:
    lines = []
    for code in range(32, 128):
        name = "cursor/wrap" if code == 127 else chr(code)
        lines.append(f"U+{code:04X} ({code}) {name}")
        lines.extend("  " + r for r in glyphs[code])
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    glyphs = parse(SRC)
    notes = validate(glyphs)
    blob = pack(glyphs)
    if len(blob) != 768:
        raise SystemExit(f"packed size {len(blob)}, expected 768")
    BIN.write_bytes(blob)
    write_pymod(blob, PYMOD)
    make_sheet(glyphs, SHEET, scale=3)
    print(f"source  {SRC}")
    print(f"binary  {BIN}  ({len(blob)} bytes)")
    print(f"module  {PYMOD}")
    print(f"sheet   {SHEET}")
    if notes:
        print("metric notes:")
        for n in notes:
            print("  ", n)
    else:
        print("metrics: left bearing clear; row 7 only on descenders + cursor")
    if "--preview" in argv:
        sys.stdout.write(preview_ascii(glyphs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
