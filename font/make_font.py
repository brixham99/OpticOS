#!/usr/bin/env python3
"""
OpticOS 4x8 condensed font and boot-screen mock-up.

Clean-room original artwork, drawn on a 3-pixel-wide grid with a fourth
blank column (except the cursor/wrap block at code 127, which fills the
whole nibble). Inspired by the *idea* of a 64-column Tasword Two display,
not copied from Tasword or the Sinclair ROM.

Layout (as in the OpticOS specification):
  - 96 glyphs, codes 32-127
  - row 0 is blank line-spacing (except the cursor block)
  - capitals and digits use rows 1-5
  - lower case has a 4-row x-height on rows 2-5
  - ascenders use row 1; descenders use rows 6-7
  - code 127 is a solid 4x8 editor cursor / wrap mark; there is no (c) glyph

Packed form: two glyphs per byte-row, even code in the high nibble, odd
code in the low nibble. 48 pairs x 8 bytes = 384 bytes, destined for
$3E80-$3FFF.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

# Each glyph is 8 strings of 4 characters: '#' = ink, '.' = paper.
# Column 3 is the inter-character gap and is '.' for every printable glyph.

GLYPHS: dict[str, tuple[str, ...]] = {
    " ": (
        "....",
        "....",
        "....",
        "....",
        "....",
        "....",
        "....",
        "....",
    ),
    "!": (
        "....",
        ".#..",
        ".#..",
        ".#..",
        "....",
        ".#..",
        "....",
        "....",
    ),
    '"': (
        "....",
        "#.#.",
        "#.#.",
        "....",
        "....",
        "....",
        "....",
        "....",
    ),
    "#": (
        "....",
        "#.#.",
        "###.",
        "#.#.",
        "###.",
        "#.#.",
        "....",
        "....",
    ),
    "$": (
        "....",
        "###.",
        "##..",
        ".#..",
        ".##.",
        "###.",
        "....",
        "....",
    ),
    "%": (
        "....",
        "#...",
        "#.#.",
        ".#..",
        "#.#.",
        "..#.",
        "....",
        "....",
    ),
    "&": (
        "....",
        ".#..",
        "#.#.",
        ".#..",
        "#.#.",
        ".##.",
        "....",
        "....",
    ),
    "'": (
        "....",
        ".#..",
        ".#..",
        "....",
        "....",
        "....",
        "....",
        "....",
    ),
    "(": (
        "....",
        "..#.",
        ".#..",
        ".#..",
        ".#..",
        "..#.",
        "....",
        "....",
    ),
    ")": (
        "....",
        "#...",
        ".#..",
        ".#..",
        ".#..",
        "#...",
        "....",
        "....",
    ),
    "*": (
        "....",
        "#.#.",
        ".#..",
        "###.",
        ".#..",
        "#.#.",
        "....",
        "....",
    ),
    "+": (
        "....",
        "....",
        ".#..",
        "###.",
        ".#..",
        "....",
        "....",
        "....",
    ),
    ",": (
        "....",
        "....",
        "....",
        "....",
        "....",
        ".#..",
        ".#..",
        "#...",
    ),
    "-": (
        "....",
        "....",
        "....",
        "###.",
        "....",
        "....",
        "....",
        "....",
    ),
    ".": (
        "....",
        "....",
        "....",
        "....",
        "....",
        ".#..",
        "....",
        "....",
    ),
    "/": (
        "....",
        "..#.",
        "..#.",
        ".#..",
        "#...",
        "#...",
        "....",
        "....",
    ),
    "0": (
        "....",
        "###.",
        "#.#.",
        "#.#.",
        "#.#.",
        "###.",
        "....",
        "....",
    ),
    "1": (
        "....",
        ".#..",
        "##..",
        ".#..",
        ".#..",
        "###.",
        "....",
        "....",
    ),
    "2": (
        "....",
        "###.",
        "..#.",
        "###.",
        "#...",
        "###.",
        "....",
        "....",
    ),
    "3": (
        "....",
        "###.",
        "..#.",
        ".##.",
        "..#.",
        "###.",
        "....",
        "....",
    ),
    "4": (
        "....",
        "#.#.",
        "#.#.",
        "###.",
        "..#.",
        "..#.",
        "....",
        "....",
    ),
    "5": (
        "....",
        "###.",
        "#...",
        "###.",
        "..#.",
        "###.",
        "....",
        "....",
    ),
    "6": (
        "....",
        "###.",
        "#...",
        "###.",
        "#.#.",
        "###.",
        "....",
        "....",
    ),
    "7": (
        "....",
        "###.",
        "..#.",
        ".#..",
        ".#..",
        ".#..",
        "....",
        "....",
    ),
    "8": (
        "....",
        "###.",
        "#.#.",
        "###.",
        "#.#.",
        "###.",
        "....",
        "....",
    ),
    "9": (
        "....",
        "###.",
        "#.#.",
        "###.",
        "..#.",
        "###.",
        "....",
        "....",
    ),
    ":": (
        "....",
        "....",
        ".#..",
        "....",
        ".#..",
        "....",
        "....",
        "....",
    ),
    ";": (
        "....",
        "....",
        ".#..",
        "....",
        ".#..",
        ".#..",
        "#...",
        "....",
    ),
    "<": (
        "....",
        "..#.",
        ".#..",
        "#...",
        ".#..",
        "..#.",
        "....",
        "....",
    ),
    "=": (
        "....",
        "....",
        "###.",
        "....",
        "###.",
        "....",
        "....",
        "....",
    ),
    ">": (
        "....",
        "#...",
        ".#..",
        "..#.",
        ".#..",
        "#...",
        "....",
        "....",
    ),
    "?": (
        "....",
        "###.",
        "..#.",
        ".#..",
        "....",
        ".#..",
        "....",
        "....",
    ),
    "@": (
        "....",
        ".##.",
        "#.#.",
        "#.#.",
        "#...",
        ".##.",
        "....",
        "....",
    ),
    "A": (
        "....",
        ".#..",
        "#.#.",
        "###.",
        "#.#.",
        "#.#.",
        "....",
        "....",
    ),
    "B": (
        "....",
        "##..",
        "#.#.",
        "##..",
        "#.#.",
        "##..",
        "....",
        "....",
    ),
    "C": (
        "....",
        ".##.",
        "#...",
        "#...",
        "#...",
        ".##.",
        "....",
        "....",
    ),
    "D": (
        "....",
        "##..",
        "#.#.",
        "#.#.",
        "#.#.",
        "##..",
        "....",
        "....",
    ),
    "E": (
        "....",
        "###.",
        "#...",
        "##..",
        "#...",
        "###.",
        "....",
        "....",
    ),
    "F": (
        "....",
        "###.",
        "#...",
        "##..",
        "#...",
        "#...",
        "....",
        "....",
    ),
    "G": (
        "....",
        ".##.",
        "#...",
        "#.#.",
        "#.#.",
        ".##.",
        "....",
        "....",
    ),
    "H": (
        "....",
        "#.#.",
        "#.#.",
        "###.",
        "#.#.",
        "#.#.",
        "....",
        "....",
    ),
    "I": (
        "....",
        "###.",
        ".#..",
        ".#..",
        ".#..",
        "###.",
        "....",
        "....",
    ),
    "J": (
        "....",
        "###.",
        "..#.",
        "..#.",
        "#.#.",
        ".#..",
        "....",
        "....",
    ),
    "K": (
        "....",
        "#.#.",
        "#.#.",
        "##..",
        "#.#.",
        "#.#.",
        "....",
        "....",
    ),
    "L": (
        "....",
        "#...",
        "#...",
        "#...",
        "#...",
        "###.",
        "....",
        "....",
    ),
    "M": (
        "....",
        "#.#.",
        "###.",
        "#.#.",
        "#.#.",
        "#.#.",
        "....",
        "....",
    ),
    "N": (
        "....",
        "##..",
        "#.#.",
        "#.#.",
        "#.#.",
        "#.#.",
        "....",
        "....",
    ),
    "O": (
        "....",
        ".#..",
        "#.#.",
        "#.#.",
        "#.#.",
        ".#..",
        "....",
        "....",
    ),
    "P": (
        "....",
        "##..",
        "#.#.",
        "##..",
        "#...",
        "#...",
        "....",
        "....",
    ),
    "Q": (
        "....",
        ".#..",
        "#.#.",
        "#.#.",
        "#.#.",
        ".##.",
        "....",
        "....",
    ),
    "R": (
        "....",
        "##..",
        "#.#.",
        "##..",
        "#.#.",
        "#.#.",
        "....",
        "....",
    ),
    "S": (
        "....",
        ".##.",
        "#...",
        ".##.",
        "..#.",
        "##..",
        "....",
        "....",
    ),
    "T": (
        "....",
        "###.",
        ".#..",
        ".#..",
        ".#..",
        ".#..",
        "....",
        "....",
    ),
    "U": (
        "....",
        "#.#.",
        "#.#.",
        "#.#.",
        "#.#.",
        "###.",
        "....",
        "....",
    ),
    "V": (
        "....",
        "#.#.",
        "#.#.",
        "#.#.",
        "#.#.",
        ".#..",
        "....",
        "....",
    ),
    "W": (
        "....",
        "#.#.",
        "#.#.",
        "#.#.",
        "###.",
        "#.#.",
        "....",
        "....",
    ),
    "X": (
        "....",
        "#.#.",
        "#.#.",
        ".#..",
        "#.#.",
        "#.#.",
        "....",
        "....",
    ),
    "Y": (
        "....",
        "#.#.",
        "#.#.",
        ".#..",
        ".#..",
        ".#..",
        "....",
        "....",
    ),
    "Z": (
        "....",
        "###.",
        "..#.",
        ".#..",
        "#...",
        "###.",
        "....",
        "....",
    ),
    "[": (
        "....",
        "###.",
        "#...",
        "#...",
        "#...",
        "###.",
        "....",
        "....",
    ),
    "\\": (
        "....",
        "#...",
        "#...",
        ".#..",
        "..#.",
        "..#.",
        "....",
        "....",
    ),
    "]": (
        "....",
        "###.",
        "..#.",
        "..#.",
        "..#.",
        "###.",
        "....",
        "....",
    ),
    "^": (
        "....",
        ".#..",
        "#.#.",
        "....",
        "....",
        "....",
        "....",
        "....",
    ),
    "_": (
        "....",
        "....",
        "....",
        "....",
        "....",
        "....",
        "....",
        "###.",
    ),
    "`": (
        "....",
        "#...",
        ".#..",
        "....",
        "....",
        "....",
        "....",
        "....",
    ),
    "a": (
        "....",
        "....",
        ".##.",
        "#.#.",
        "###.",
        "#.#.",
        "....",
        "....",
    ),
    "b": (
        "....",
        "#...",
        "##..",
        "#.#.",
        "#.#.",
        "##..",
        "....",
        "....",
    ),
    "c": (
        "....",
        "....",
        ".##.",
        "#...",
        "#...",
        ".##.",
        "....",
        "....",
    ),
    "d": (
        "....",
        "..#.",
        ".##.",
        "#.#.",
        "#.#.",
        ".##.",
        "....",
        "....",
    ),
    "e": (
        "....",
        "....",
        ".##.",
        "###.",
        "#...",
        ".##.",
        "....",
        "....",
    ),
    "f": (
        "....",
        ".##.",
        ".#..",
        "###.",
        ".#..",
        ".#..",
        "....",
        "....",
    ),
    "g": (
        "....",
        "....",
        ".##.",
        "#.#.",
        ".##.",
        "..#.",
        ".##.",
        "....",
    ),
    "h": (
        "....",
        "#...",
        "##..",
        "#.#.",
        "#.#.",
        "#.#.",
        "....",
        "....",
    ),
    "i": (
        "....",
        ".#..",
        "....",
        ".#..",
        ".#..",
        ".#..",
        "....",
        "....",
    ),
    "j": (
        "....",
        "..#.",
        "....",
        "..#.",
        "..#.",
        "..#.",
        "..#.",
        ".#..",
    ),
    "k": (
        "....",
        "#...",
        "#.#.",
        "##..",
        "#.#.",
        "#.#.",
        "....",
        "....",
    ),
    "l": (
        "....",
        ".#..",
        ".#..",
        ".#..",
        ".#..",
        ".##.",
        "....",
        "....",
    ),
    "m": (
        "....",
        "....",
        "###.",
        "#.#.",
        "#.#.",
        "#.#.",
        "....",
        "....",
    ),
    "n": (
        "....",
        "....",
        "##..",
        "#.#.",
        "#.#.",
        "#.#.",
        "....",
        "....",
    ),
    "o": (
        "....",
        "....",
        ".#..",
        "#.#.",
        "#.#.",
        ".#..",
        "....",
        "....",
    ),
    "p": (
        "....",
        "....",
        "##..",
        "#.#.",
        "#.#.",
        "##..",
        "#...",
        "....",
    ),
    "q": (
        "....",
        "....",
        ".##.",
        "#.#.",
        "#.#.",
        ".##.",
        "..#.",
        "....",
    ),
    "r": (
        "....",
        "....",
        "#.#.",
        "##..",
        "#...",
        "#...",
        "....",
        "....",
    ),
    "s": (
        "....",
        "....",
        ".##.",
        "##..",
        ".##.",
        "##..",
        "....",
        "....",
    ),
    "t": (
        "....",
        ".#..",
        "###.",
        ".#..",
        ".#..",
        ".##.",
        "....",
        "....",
    ),
    "u": (
        "....",
        "....",
        "#.#.",
        "#.#.",
        "#.#.",
        "###.",
        "....",
        "....",
    ),
    "v": (
        "....",
        "....",
        "#.#.",
        "#.#.",
        "#.#.",
        ".#..",
        "....",
        "....",
    ),
    "w": (
        "....",
        "....",
        "#.#.",
        "#.#.",
        "###.",
        "#.#.",
        "....",
        "....",
    ),
    "x": (
        "....",
        "....",
        "#.#.",
        ".#..",
        ".#..",
        "#.#.",
        "....",
        "....",
    ),
    "y": (
        "....",
        "....",
        "#.#.",
        "#.#.",
        ".##.",
        "..#.",
        ".##.",
        "....",
    ),
    "z": (
        "....",
        "....",
        "###.",
        "..#.",
        "#...",
        "###.",
        "....",
        "....",
    ),
    "{": (
        "....",
        ".##.",
        ".#..",
        "##..",
        ".#..",
        ".##.",
        "....",
        "....",
    ),
    "|": (
        "....",
        ".#..",
        ".#..",
        ".#..",
        ".#..",
        ".#..",
        ".#..",
        "....",
    ),
    "}": (
        "....",
        "##..",
        ".#..",
        ".##.",
        ".#..",
        "##..",
        "....",
        "....",
    ),
    "~": (
        "....",
        "....",
        "#.#.",
        ".#..",
        "....",
        "....",
        "....",
        "....",
    ),
    # Code 127: solid 4x8 cursor / wrap block. Fills the whole nibble.
    "\x7f": (
        "####",
        "####",
        "####",
        "####",
        "####",
        "####",
        "####",
        "####",
    ),
}


def validate() -> None:
    expected = [chr(c) for c in range(32, 128)]
    missing = [c for c in expected if c not in GLYPHS]
    extra = [c for c in GLYPHS if c not in expected]
    if missing or extra:
        raise SystemExit(f"glyph set mismatch: missing={missing!r} extra={extra!r}")
    for ch, rows in GLYPHS.items():
        if len(rows) != 8:
            raise SystemExit(f"{ch!r} has {len(rows)} rows")
        for i, row in enumerate(rows):
            if len(row) != 4 or any(p not in ".#" for p in row):
                raise SystemExit(f"{ch!r} row {i} is {row!r}")
            if ch != "\x7f" and row[3] != ".":
                raise SystemExit(f"{ch!r} row {i} uses the gap column: {row!r}")
            if ch != "\x7f" and i == 0 and row != "....":
                raise SystemExit(f"{ch!r} does not keep row 0 blank: {row!r}")


def nibble(row: str) -> int:
    n = 0
    for i, p in enumerate(row):
        if p == "#":
            n |= 1 << (3 - i)
    return n


def packed_bytes() -> bytes:
    """384-byte ROM image: even glyph in high nibble, odd in low nibble."""
    out = bytearray()
    for pair in range(48):
        even = GLYPHS[chr(32 + 2 * pair)]
        odd = GLYPHS[chr(33 + 2 * pair)]
        for r in range(8):
            out.append((nibble(even[r]) << 4) | nibble(odd[r]))
    assert len(out) == 384
    return bytes(out)


def write_font4_txt(path: Path) -> None:
    lines = [
        "OpticOS 4x8 condensed font (clean-room original artwork)",
        "96 glyphs, codes 32-127. Each cell is 4 pixels wide (3 ink + 1 gap)",
        "by 8 rows. Row 0 is line spacing. Capitals and digits use rows 1-5.",
        "Lower case has a 4-row x-height on rows 2-5, with ascenders on row 1",
        "and descenders on rows 6-7. Code 127 is a solid cursor/wrap block.",
        "There is no copyright glyph; the boot banner uses ASCII (c).",
        "",
    ]
    for code in range(32, 128):
        ch = chr(code)
        label = "cursor/wrap" if code == 127 else ch
        lines.append(f"U+00{code:02X} ({code}) {label}")
        for row in GLYPHS[ch]:
            lines.append("  " + row.replace(".", "·").replace("#", "█"))
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_font4x8_py(path: Path, blob: bytes) -> None:
    hex_rows = []
    for i in range(0, 384, 16):
        chunk = ", ".join(f"0x{b:02X}" for b in blob[i : i + 16])
        hex_rows.append(f"    {chunk},")
    body = "\n".join(hex_rows)
    glyphs_literal = "{\n"
    for code in range(32, 128):
        ch = chr(code)
        rows = ", ".join(repr(r) for r in GLYPHS[ch])
        glyphs_literal += f"    {ch!r}: ({rows}),\n"
    glyphs_literal += "}\n"
    path.write_text(
        f'''"""OpticOS 4x8 condensed font (clean-room original artwork).

96 glyphs (codes 32-127), 4 pixels wide by 8 rows. Packed form is 384
bytes, two glyphs per byte-row: even code in the high nibble, odd code
in the low nibble. Destined for $3E80-$3FFF in the 16K ROM.

Row 0 is line spacing. Capitals and digits use rows 1-5. Lower case has
a 4-row x-height on rows 2-5. Code 127 is the editor cursor / wrap block.
There is no copyright glyph; banners use ASCII (c).
"""
from __future__ import annotations

GLYPHS: dict[str, tuple[str, ...]] = {glyphs_literal}

# 384-byte packed font, ready to assemble at $3E80.
FONT_BIN = bytes([
{body}
])

assert len(FONT_BIN) == 384


def nibble(row: str) -> int:
    n = 0
    for i, p in enumerate(row):
        if p == "#":
            n |= 1 << (3 - i)
    return n


def glyph_rows(code: int) -> tuple[str, ...]:
    if not 32 <= code <= 127:
        raise ValueError(f"font covers 32-127, not {{code}}")
    return GLYPHS[chr(code)]
''',
        encoding="utf-8",
    )


# Spectrum ULA colours, bright off.
PAPER = (0x00, 0x00, 0x00)
INK = (0xD7, 0xD7, 0xD7)
BORDER = (0x00, 0x00, 0x00)

SCREEN_W, SCREEN_H = 256, 192
BORDER_X, BORDER_Y = 32, 32  # 320x256 inclusive of the border
FRAME_W, FRAME_H = SCREEN_W + 2 * BORDER_X, SCREEN_H + 2 * BORDER_Y

BANNER = "OpticOS (c) 2026 Optica Technology"
BANNER_ROW = 0
BANNER_COL = 0
CURSOR_ROW = 1
CURSOR_COL = 0


def blit_glyph(px: list[list[tuple[int, int, int]]], col: int, row: int, ch: str) -> None:
    if not 0 <= col < 64 or not 0 <= row < 24:
        raise ValueError(f"print position out of range: col={col} row={row}")
    x0 = col * 4
    y0 = row * 8
    for r, bits in enumerate(GLYPHS[ch]):
        for c, p in enumerate(bits):
            if p == "#":
                px[y0 + r][x0 + c] = INK


def render_screen() -> list[list[tuple[int, int, int]]]:
    px = [[PAPER for _ in range(SCREEN_W)] for _ in range(SCREEN_H)]
    for i, ch in enumerate(BANNER):
        blit_glyph(px, BANNER_COL + i, BANNER_ROW, ch)
    blit_glyph(px, CURSOR_COL, CURSOR_ROW, "\x7f")
    return px


def compose_frame(px: list[list[tuple[int, int, int]]]) -> Image.Image:
    im = Image.new("RGB", (FRAME_W, FRAME_H), BORDER)
    for y, row in enumerate(px):
        for x, colour in enumerate(row):
            im.putpixel((x + BORDER_X, y + BORDER_Y), colour)
    return im


def render_font_sheet() -> Image.Image:
    """16x6 grid of all 96 glyphs, with labels, for review."""
    cell_w, cell_h = 12, 20
    cols, rows = 16, 6
    pad = 8
    im = Image.new("RGB", (pad * 2 + cols * cell_w, pad * 2 + rows * cell_h + 16), (16, 16, 16))
    # Draw on a working buffer at 1x glyph size, then we just stamp pixels.
    for i in range(96):
        code = 32 + i
        ch = chr(code)
        cx = pad + (i % cols) * cell_w
        cy = pad + 12 + (i // cols) * cell_h
        # tiny code label as raw pixels is hard; skip text, just boxes
        for r, bits in enumerate(GLYPHS[ch]):
            for c, p in enumerate(bits):
                colour = INK if p == "#" else (40, 40, 40)
                # 2x stamp for review
                for dy in range(2):
                    for dx in range(2):
                        im.putpixel((cx + c * 2 + dx, cy + r * 2 + dy), colour)
    return im.resize((im.width * 2, im.height * 2), Image.Resampling.NEAREST)


def render_font_sheet_labelled() -> Image.Image:
    """Larger review sheet: each glyph at 8x with its code and character."""
    scale = 8
    gw, gh = 4 * scale, 8 * scale
    label_h = 22
    cell_w, cell_h = gw + 16, gh + label_h + 12
    cols, rows = 16, 6
    margin = 16
    title_h = 28
    w = margin * 2 + cols * cell_w
    h = margin * 2 + title_h + rows * cell_h
    im = Image.new("RGB", (w, h), (20, 20, 20))
    draw = ImageDraw.Draw(im)
    draw.text((margin, 8), "OpticOS 4x8 font  (codes 32-127, clean-room)", fill=(220, 220, 220))
    for i in range(96):
        code = 32 + i
        ch = chr(code)
        col, row = i % cols, i // cols
        x = margin + col * cell_w
        y = margin + title_h + row * cell_h
        # glyph background (one Spectrum character cell, 4x8, scaled)
        for r, bits in enumerate(GLYPHS[ch]):
            for c, p in enumerate(bits):
                colour = INK if p == "#" else PAPER
                for dy in range(scale):
                    for dx in range(scale):
                        im.putpixel((x + 4 + c * scale + dx, y + c * 0 + 4 + r * scale + dy), colour)
        # gap column hint: already in the glyph
        label = "127 block" if code == 127 else f"{code} {ch}"
        draw.text((x + 2, y + 4 + gh + 2), label, fill=(180, 180, 180))
    return im


def main() -> None:
    validate()
    destinations = [
        Path("/workspace/newrom/font"),
        Path("/workspace/opticos-repo/font"),
    ]
    preview = Path("/tmp/opticos-preview")
    assets = Path("/workspace/opticos-repo/assets")
    preview.mkdir(parents=True, exist_ok=True)
    assets.mkdir(parents=True, exist_ok=True)

    blob = packed_bytes()
    px = render_screen()
    frame = compose_frame(px)
    frame_3x = frame.resize((FRAME_W * 3, FRAME_H * 3), Image.Resampling.NEAREST)
    raw = Image.new("RGB", (SCREEN_W, SCREEN_H), PAPER)
    for y, row in enumerate(px):
        for x, colour in enumerate(row):
            raw.putpixel((x, y), colour)
    sheet = render_font_sheet_labelled()
    crop = raw.crop((0, 0, 34 * 4, 16))
    closeup = crop.resize((crop.width * 8, crop.height * 8), Image.Resampling.NEAREST)

    for here in destinations:
        here.mkdir(parents=True, exist_ok=True)
        (here / "font4x8.bin").write_bytes(blob)
        write_font4_txt(here / "font4.txt")
        write_font4x8_py(here / "font4x8.py", blob)
        # Keep the generator itself in sync when we run from /workspace/newrom/font.
        src = Path(__file__).resolve()
        dest = (here / "make_font.py").resolve()
        if src != dest:
            dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        frame.save(here / "opticos_boot.png")
        frame_3x.save(here / "opticos_boot_3x.png")
        raw.save(here / "opticos_boot_raw256x192.png")

    # Repo assets: the 1x and 3x frames plus the glyph sheet. Boot PNGs
    # are not stored under font/ in the public repo.
    for extra in (Path("/workspace/newrom/font/opticos_boot.png"),
                  Path("/workspace/newrom/font/opticos_boot_3x.png"),
                  Path("/workspace/newrom/font/opticos_boot_raw256x192.png")):
        pass
    frame.save(assets / "opticos_boot.png")
    frame_3x.save(assets / "opticos_boot_3x.png")
    sheet.save(assets / "font_sheet.png")
    # Review copies
    frame.save(preview / "opticos_boot.png")
    frame_3x.save(preview / "opticos_boot_3x.png")
    raw.save(preview / "opticos_boot_raw256x192.png")
    sheet.save(preview / "font_sheet.png")
    closeup.save(preview / "banner_closeup.png")

    # Do not commit boot PNGs inside the repo's font/ directory.
    for leftover in (
        Path("/workspace/opticos-repo/font/opticos_boot.png"),
        Path("/workspace/opticos-repo/font/opticos_boot_3x.png"),
        Path("/workspace/opticos-repo/font/opticos_boot_raw256x192.png"),
    ):
        if leftover.exists():
            leftover.unlink()

    print(f"packed {len(blob)} bytes")
    print(f"frame {FRAME_W}x{FRAME_H}, 3x {FRAME_W*3}x{FRAME_H*3}")
    print(f"banner {len(BANNER)} chars at row {BANNER_ROW} col {BANNER_COL}")
    print(f"cursor at row {CURSOR_ROW} col {CURSOR_COL}")
    print("wrote", ", ".join(str(d) for d in destinations), "and", preview)


if __name__ == "__main__":
    main()
