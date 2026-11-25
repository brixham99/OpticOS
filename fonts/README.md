# OpticOS 8x8 font (clean-room)

Original 8×8 bitmap font for the planned 32-column text mode.
**Not wired into the ROM and not committed** — source lives here as
untracked work for review.

## Character set

Matches the existing OpticOS 4×8 font, not the Sinclair layout:

- 96 glyphs, codes 32–127
- Standard ASCII 32–126 (code 96 is a grave / backtick, **not** £)
- Code 127 is a solid editor cursor / wrap block
- No copyright glyph; banners keep using ASCII `(c)`
- A © would now be legible at 8×8, but the 4×8 set has none, so this
  set does not invent one

## Metrics and style

- 8×8 cell; column 0 is a 1-pixel left bearing (empty except code 127)
- Shared baseline at row 5; capitals and digits occupy rows 0–5
- Lower case: 5-row x-height on rows 1–5; ascenders also use row 0;
  descenders (`g j p q y`) use rows 6–7
- Vertical stems are 2 pixels (ULA / composite-friendly); horizontals are
  1 pixel so they balance after TV bloom
- Geometric, open counters; slashed rectangular `0` vs octagonal `O`;
  `8` is symmetric (same-width aligned bowls, indented waist);
  `A` has a tall pointed roof and a low crossbar; `D` is square-left /
  rounded-right; `I` / `1` / `l` / `|` are distinct

The bitmaps were drawn by hand in `optic8x8.txt`. They were not copied
from the Sinclair ROM font, from any other copyrighted font, or by
scaling the 4×8 glyphs.

## Files

| File | Role |
|------|------|
| `optic8x8.txt` | Source of truth (`#` ink, `.` paper) |
| `make_optic8x8.py` | Converter and sample-sheet renderer |
| `optic8x8.bin` | 768-byte packed font (8 bytes/glyph, bit 7 = left) |
| `optic8x8.py` | The same bytes as a Python module (generated) |
| `optic8x8_sheet.png` | 3× sample sheet: two 320×240 Spectrum-like screens (white on blue, black on white) |

Rebuild:

```
python3 fonts/make_optic8x8.py
```
