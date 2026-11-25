# OpticOS 128: SCREEN 0 / 1 / 2 / 3

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
| `SCREEN n` | n = 0 64-column hi-res (256×192); 1 = 32-column hi-res (same bitmap, 8×8 font); 2 = 64×48 chunky (old 1); 3 = 32×24 attribute (old 2) | – |
| `PLOT x,y[,c]` | unchanged | Origin at the bottom left. The colour is c (0–15), or INK + 8×BRIGHT. Out of range gives "Value outside range". |
| `POINT(x,y)` | pixel 0/1 of screen 5 | colour 0–15 from the framebuffer |
| `CLS` | unchanged | fills with PAPER (+8×BRIGHT) |
| `SCREEN FLIP` | – | Switches to manual double buffering. Renders the hidden screen (bank 7's at $C000, or screen 5), waits for the frame and shows it. |
| DRAW, PRINT, INK/PAPER | unchanged | Phase 2. PRINT writes to screen 5 as normal and may be overwritten by the renderer. |

- **Auto mode (default after SCREEN 2/3):** every PLOT/CLS is rendered to screen 5 at once.
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

- **Mode 2:** the chunky64 v2 renderer. Ink is the most common colour in the cell and paper the next, through a 256-entry attribute table.
- **Mode 2:** writes attributes only, with the bitmap cleared, through a 16-entry table (paper = ink = colour, BRIGHT = bit 3).

## Demo

`examples/src/flags128.bas` (tape `examples/flags128.tap`/`.tzx`): the Union Flag from `flag.bas`.

- **SCREEN 0:** drawn by the original listing (full-resolution PLOT).
- **SCREEN 2 and SCREEN 3:** the same flag with `BOX` for the field and the cross, and `DRAW` of one horizontal run per arm per row for the saltires (`dband` in the listing). The red saltire is offset inside the white band with the same counterchange as SCREEN 0 (red to the left in the top half, to the right in the bottom half, white on both sides of the red). SCREEN 2 keeps the earlier ~6-chunky-pixel vertical band thickness (14 pixels horizontally, 5 of them red) with edges aligned to the 2×2 attribute grid; SCREEN 3 uses an ~3–4 cell vertical band (8 cells horizontally, 2 of them red).
- **SCREEN 1** is the same 256×192 bitmap as SCREEN 0, so the demo does not show it separately.

Screenshots are in `docs/screenmodes/` (`flags_all_modes.png`, `flag_screen0.png` / `flag_screen2.png` / `flag_screen3.png`).

## Running it

```
fuse-sdl --machine 128 --rom-128-0 build/opticos.rom --rom-128-1 build/opticos128ext.rom
```

## Known limits (phase 1)

- FRAMES and the keyboard aren't serviced while ROM 1 renders with interrupts off. A full-screen render loses a few interrupts, so FRAMES and WAIT run slow in heavy FLIP loops. ROM 1's IM 1 handler counts FRAMES during FLIP's wait.
- PRINT, LIST, INPUT and the editor use the last text mode (0 or 1). CIRCLE is implemented in all four modes: 0 and 1 plot the 256×192 bitmap; 2 and 3 use the chunky/attr framebuffer.
- On a 48K Spectrum, SCREEN gives "No such PROC or FN" as before, and nothing else changes (rig suites pass).

## Phase 2 (RC-6)

SCREEN and SAY now share one extension ROM (`build/opticos128ext.rom`, built by `ext128/build.py` from the SAY source plus `ext128/screen.asm`). Push is not approved; the work is on the local branch `opticos128-ext`.

### New statements

| Statement | Mode 0 | Modes 1/2 |
|---|---|---|
| `DRAW dx,dy[,c]` / `DRAW TO x,y[,c]` | unchanged | Bresenham in this mode's coordinates, from the last PLOT/DRAW/BOX corner. Off-screen pixels are skipped. The colour is optional (otherwise INK + 8×BRIGHT). |
| `BOX x,y,w,h[,c]` | — (identifier, handled by the extension) | Filled rectangle; (x,y) is the bottom-left, w×h pixels, clipped to the mode. Not a keyword (BOX is not in the keyword table). |
| `CIRCLE x,y,r[,c]` | not in OpticOS (dropped in v0.7; the name is "No such PROC or FN") | Midpoint circle, centre (x,y) bottom-left, radius r, clipped. r=0 is a single pixel. Colour optional (otherwise INK + 8×BRIGHT). Not a keyword. |
| `PRINT`, `LIST`, the editor, error reports, `INPUT` prompts | last text mode | RST 16 in mode 2 or 3 returns to SCREEN 0 or 1 (OMODE 64 or 32) and shows screen 5. The picture stays until the next CLS. |

Auto-show and SCREEN FLIP are unchanged. Interrupts are off while a line or box is written into the framebuffer (FRAMES does not advance for those few milliseconds); BREAK is sampled at the end of the statement.

### Demo timings (Union Flag, `examples/flags128.tap`)

| Mode | Phase 1 (pixel loop) | Phase 2 (`BOX`/`DRAW`) | Offset saltire (`dband`) |
|---|---|---|---|
| SCREEN 0 | 18 s | 18 s (same original listing) | 18 s |
| SCREEN 1 | 92.7 s | 5.4 s (centred red) | 5.3 s |
| SCREEN 2 | 23.3 s | 2.8 s (centred red) | 2.6 s |

The remaining time is OpticBASIC's per-row arithmetic for the saltires (32 or 16 rows × two arms of `PLOT`/`DRAW TO` for white, then red), not the machine-code plot. A fully integer or fewer-command saltire should go under two seconds. The printed times were read from the SCREEN 0 report after the demo (`flag_timings.png`).

### ROM space after phase 2

- OpticOS ROM 0: the 32-byte SCREEN/SAY hooks are unchanged (81 bytes of unplaced section slack as reported by `check_layout`). DRAW and the RST 16 text hook used previously empty inter-section gaps (21 bytes before NMI, 5 before BEEPER, 6 before POKE_RET, 5 after RST 16). Remaining clean gaps of 4 bytes or more: $000B (5), $002B (5), $2038 (4).
- Merged extension ROM: 2,610 bytes free ($31BE–$3AFF and $3B10–$3BFF). SAY ends at $28AD; screen code (PLOT/DRAW/BOX/CIRCLE/CLS/POINT/SCREEN/FLIP) occupies $28AD–$31BE; TA2 at $3B00 (16 bytes); TA at $3C00 (256 bytes); AY volume table $3D00–$3FFF.

### DRAW / BOX correctness (phase 2 follow-up)

The first phase-2 `flags_all_modes.png` was wrong, and the earlier report did not look at it. Modes 1 and 2 had a white-washed top, checkerboard / stairstep saltires, and pixels spilling below and to the left of the flag; mode 2 also looked as if some blocks were smaller than 8×8. Those bugs were in the machine code, not in the demo listing (`band`/`BOX` is a sound construction once DRAW and BOX are correct).

Root causes, all in `ext128/screen.asm`:

1. **`lineto` clobbered the Bresenham error term.** After `ld c,a` (error in C), the next `ld bc,(LN_CUR)` threw C away, and after `plot_cl` the "error" was restored from the row. Horizontal `DRAW` then drifted down the screen whenever the row was ≥ the length of the run, which is exactly the messy lower saltire and the spill below the flag.
2. **`lineto` read `LN_CUR` with the wrong endianness.** The current point is stored as BC (B = x, C = row), so `ld hl,(LN_CUR)` has L = row and H = x. The first version did `x1-L` and `row1-H`, so every line used the wrong delta and direction (a single pixel became a long diagonal).
3. **`sx`/`sy` were ±1 even when that axis's delta was 0**, so a corrupted error term could walk off a horizontal or vertical line. They are now 0 when the delta is 0.
4. **`boxfill` drew one extra pixel to the right of every row** (`cp b / inc b / jr nc`). At x = width that extra write wrapped in `pix_addr` to x = 0 of another row — spill below and to the left. BOX now stops after x1 and uses `plot_cl`.
5. **Y past the top (y > 47 or y > 23) wrapped in 8-bit `ytotop`**, so `DRAW TO 20,60` walked down the screen instead of clipping upward. The current row is now a signed 16-bit value; `plot_cl` skips a negative row.

Fixes were checked with `tools/rig/test_screen_gfx.py` (59 tests, all passing): DRAW in all 8 octants plus both steepness cases, negative deltas, a short horizontal run at a high row, clipping of endpoints off the right and above the top, BOX at the edges and a full-width box with no wrap, and a comparison of each mode's framebuffer against a Python-rendered 64×48 / 32×24 Union Flag (exact match to the demo construction; no pixels outside the flag; rendered screen is a clean 4×4 / 8×8 cell grid).

The screenshots in `docs/screenmodes/` were retaken from a real Fuse 128K run after the thick offset-saltire listing and inspected. SCREEN 0 mid-arm vertical thickness is about 32–33 pixels (red about 8–9); divided by 4 that is ~8, divided by 8 about 4. Modes 1 and 2 keep the earlier thick white band (mode 1 mid-arm vertical 6–7 chunky pixels, red 2–3, no three-colour 2×2 attribute cells; mode 2 vertical 3–4 cells, red 1), with the official counterchange rather than a centred red. The previous thin 4-pixel / 3-cell horizontal spans had collapsed the vertical thickness to ~2 and a 1-cell staircase. In both modes the red sits to the left in the top half and to the right in the bottom half, with white remaining on both sides of the red, matching SCREEN 0 in each quadrant.

`dband` (and the earlier `band`) must pass the colour to `DRAW TO` (`DRAW TO x2, y, c`). A bare `DRAW TO x2, y` uses INK, which is 7, so the red saltire was painted white after the first pixel.

### CIRCLE (SCREEN 0–3)

`CIRCLE x,y,r[,c]` is a midpoint circle in the extension ROM. In SCREEN 2/3 it is written into the framebuffer with `plot_cl`, dirty cells marked, and one `auto_show` render. In SCREEN 0 and 1 the same midpoint walk plots the 256×192 bitmap on screen 5: with no `c`, the pixel follows OVER/INVERSE and the cell takes ATTR_T/MASK_T (as PLOT); with `c` 0–15 the ink pixel is set (unless INVERSE) and INK+BRIGHT are taken from `c`, leaving PAPER. 48K still reports "No such PROC or FN".

The demo `examples/src/circles128.bas` (tape `examples/circles128.tap` / `.tzx`) draws a concentric red/white target on a blue field in all four modes. SCREEN 0 and 1 space the rings eight pixels apart so the attribute clash looks tidier; SCREEN 2 and 3 stay four chunky pixels / cells apart. Screenshots are in `docs/screenmodes/` (`circles_all_modes.png`, `circle_screen0.png`–`circle_screen3.png`, `circle_timings.png`).

A map of both 16K ROMs, generated from the built symbol files and `tools/check_layout.py` ranges, is `docs/screenmodes/rom_maps.png` (`tools/rom_map.py`).

### UDGs (SCREEN 1 only)

21 user-defined glyphs, codes 144–164 (G-mode keys a–u).  Each is 8×8, stored in the 168-byte area above RAMTOP (the UDG sysvar at 23675 points at the first byte).  They are POKEd from BASIC; un-POKEd glyphs are blank.  In SCREEN 1 they print as those bitmaps; in SCREEN 0 the same stored bytes print as `?` and are not rewritten.

Caps+9 toggles G-mode in SCREEN 1 only.  While it is on, a–u / A–U insert codes 144–164, accepted by the tokeniser only inside strings.  ENTER, or Caps+9 again, leaves G-mode.  48K and SCREEN 0 ignore Caps+9.  `CLEAR n` will not let RAMTOP run into the UDG area (`No room`); the UDG pointer stays at the top of RAM.

`USR "a"` was not added: after G-mode, the tokeniser and the CLEAR cap, section K had only three free bytes, which is not enough for a string form of USR.  `PEEK` of the UDG sysvar still gives the address of glyph `a`.

The demo `examples/src/udg128.bas` (tape `examples/udg128.tap` / `.tzx`) POKEs a spaceship and an alien and prints them in SCREEN 1.  The screenshot is `docs/screenmodes/udg_mode1.png`.
