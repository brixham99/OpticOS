# OpticOS 128: SCREEN 0 / 1 / 2 (RC-6, phase 1)

Screen modes for OpticBASIC on a 128K Spectrum, hosted in an OpticOS extension ROM
in ROM slot 1 (`build/opticos128ext.rom`, built by `ext128/build.py`).
OpticOS itself (ROM slot 0, `build/opticos.rom`) gains only small hooks.

## ROM space

| ROM | Before | After |
|---|---|---|
| OpticOS (slot 0), main v1.0.4 | 116 bytes free | – |
| OpticOS (slot 0), opticos128-say branch | 113 | 81 (32 bytes of hooks, below) |
| SAY extension ROM (opticos128-say) | about 5.3K free | unchanged (not merged) |
| Screen extension ROM (new) | – | code $1000–$14B3 plus tables at $3E00/$3F00: 10,813 bytes free |

ROM 0 hooks (32 bytes, packed into existing gaps):
- `xchk`/`xgo` (19): when SMODE ≠ 0, divert to ROM 1. `xgo` is also the far-call entry.
- `xfn` (5): an unknown FN (POINT) goes to ROM 1 before "No such variable".
- `st_plot` (+8): PLOT checks the mode first.
- `console` (12): the console entry resets SMODE to 0 and shows screen 5. It doubles as the return gadget for far calls.
- `CLS` (+4).

ROM 0 also keeps the existing `ext_hook`, which now keeps SMODE's screen bit when it pages.

## Syntax

| Statement | Mode 0 | Modes 1/2 |
|---|---|---|
| `SCREEN n` | n = 0 normal display, 1 = 64×48 (2×2 cells, two colours per cell), 2 = 32×24 (one colour per 8×8 cell) | – |
| `PLOT x,y[,c]` | unchanged | Origin at the bottom left. The colour is c (0–15), or INK + 8×BRIGHT. Out of range gives "Value outside range". |
| `POINT(x,y)` | pixel 0/1 of screen 5 | colour 0–15 from the framebuffer |
| `CLS` | unchanged | fills with PAPER (+8×BRIGHT) |
| `SCREEN FLIP` | – | Switches to manual double buffering. Renders the hidden screen (bank 7's at $C000, or screen 5), waits for the frame and shows it. |
| DRAW, PRINT, INK/PAPER | unchanged | Phase 2. PRINT writes to screen 5 as normal and may be overwritten by the renderer. |

- **Auto mode (default after SCREEN 1/2):** every PLOT/CLS is rendered to screen 5 at once.
- **Manual mode:** after the first SCREEN FLIP, nothing shows until the next FLIP.
- **Text and editor:** every return to the console (end of program, error, BREAK) resets to SCREEN 0 and screen 5, so the editor and error messages are always readable. The picture stays on screen until the next CLS.

## Memory

Bank 7 is paged at $C000 only inside ROM 1, with interrupts off and a private stack. OpticOS's own stack and heap are in bank 0 at $C000+.

| Bank 7 | Use |
|---|---|
| $C000–$DAFF | the shadow screen (screen 7) |
| $DC00–$E7FF | framebuffer: 64×48 colours, one byte each, cell-major (3K) |
| $E800–$EAFF | dirty flags per cell (bit 0 screen 5, bit 1 screen 7) |
| $EB00 / $F200 | dirty-cell lists for each screen |
| $F900 | variables, private stack below $0000 |

There's no conflict with OpticOS 128 or SAY: neither uses bank 7. The renderer and tables are in ROM 1.

- **Mode 1:** the chunky64 v2 renderer. Ink is the most common colour in the cell and paper the next, through a 256-entry attribute table.
- **Mode 2:** writes attributes only, with the bitmap cleared, through a 16-entry table (paper = ink = colour, BRIGHT = bit 3).

## Demo

`examples/src/flags128.bas` (tape `examples/flags128.tap`/`.tzx`): the Union Flag from `flag.bas`.

- **SCREEN 0:** drawn by the original listing.
- **SCREEN 1 and SCREEN 2:** the same flag computed pixel by pixel from its geometry.

Screenshots are in `docs/screenmodes/`. Fuse 128K timings: SCREEN 0 18 s, SCREEN 1 92.7 s, SCREEN 2 23.3 s. The time is OpticBASIC's floating-point maths, not PLOT.

## Running it

```
fuse-sdl --machine 128 --rom-128-0 build/opticos.rom --rom-128-1 build/opticos128ext.rom
```

## Known limits (phase 1)

- FRAMES and the keyboard aren't serviced while ROM 1 renders with interrupts off. A full-screen render loses a few interrupts, so FRAMES and WAIT run slow in heavy FLIP loops. ROM 1's IM 1 handler counts FRAMES during FLIP's wait.
- DRAW, CIRCLE, PRINT and INPUT in modes 1/2 aren't handled.
- On a 48K Spectrum, SCREEN gives "No such PROC or FN" as before, and nothing else changes (rig suites pass).
