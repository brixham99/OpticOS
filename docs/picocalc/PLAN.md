# OpticOS on the ClockworkPi PicoCalc: plan

Target: PicoCalc with a **Raspberry Pi Pico 2 (RP2350)**. Status: P1–P3 and P5 done; P4 firmware runs on a Pico 2 W (display, keyboard, SD card, sound).

## Approach

The OpticOS Z80 code runs on an emulated Z80 inside RP2350 firmware. The
Spectrum hardware underneath it is replaced by a small **PicoCalc machine**
that the firmware implements in C. One source tree builds two ROMs:

| Build | Output | Hardware layer |
|---|---|---|
| Spectrum (unchanged) | `build/opticos.rom` | ULA screen at `$4000`, key matrix, tape pulses |
| PicoCalc | `build/opticos_pc.rom` | I/O-port devices served by the firmware |

The Spectrum ROM must stay byte-identical, which the existing layout check and
rig tests prove. PicoCalc-only code sits behind `if PICOCALC` in the same
files, so the two builds share the interpreter, maths, tokeniser and editor.

## The PicoCalc machine

| Device | Z80 side | Firmware side |
|---|---|---|
| CPU | Z80 at 3.5 MHz, 50 Hz IM 1 interrupt, `FRAMES` as today | the rig's core (`z80.c`), no ULA contention; core 0 |
| RAM | 64K map as today: ROM `$0000-$3FFF`, RAM above | `$4000-$5AFF` becomes plain RAM (no display file) |
| Display | ports: glyph at (col,row) with attribute and OVER/INVERSE, plot, line, scroll, CLS, cursor | 320×320 1-bpp bitmap + one attribute per 8×8 cell (40×40), text in the display's own 8×8 font (`emu/font8x8.h`, public domain), Spectrum palette and FLASH; changed rows pushed to the ST7796SP panel (RGB565) over SPI from core 1 |
| Keyboard | unchanged: the Spectrum key matrix on port `$FE` (scan, `KEY(k$)`, BREAK, INKEY$) | I2C keyboard controller polled each frame; each PicoCalc key held down is shown as its Spectrum keys (e.g. `(` as SYMBOL SHIFT + 8, ← as CAPS SHIFT + 5) |
| Sound | unchanged: port `$FE` bit 4 (BEEP, chime) | beeper edges timestamped in T-states, rendered each frame to 625 samples at 31.25 kHz (`pc_render`) and played as PWM on GPIO 26/27/28, 40 ms behind; `tools/rig/test_pc_sound.py` |
| Storage | `SA-BYTES` / `LD-BYTES` hand each block to a storage device (port `$D3`); `CAT` (PicoCalc only, token `$F2` after all the shared ones) | blocks go to `/OpticOS/<name>.tap` (TAP format) on the SD card through FatFs; a file reads on like a tape, and `LOAD ""` carries on into the next file in name order; the wanted name is read from `LG_NAME` |

Text becomes **40 columns × 40 rows**: 320×320 pixels in an 8×8 font that the
display device draws (an earlier 80×40 layout in the ROM's 4×8 font was too
small to read on the PicoCalc's screen). The ROM's 4×8 font stays for the
Spectrum build.
Graphics become **320×320**, origin bottom left.

## What changes in the Z80 source

1. **Geometry equates.** `COLS`, `ROWS`, `GFX_W`, `GFX_H` replace the literal
   64/63/24/23/192/191 in `print.asm`, `console.asm`, `list.asm`, `basic.asm`,
   `gfx.asm` and `boot.asm`.
2. **Screen primitives** (PicoCalc build only): `draw_glyph`, `attr_set`,
   `scroll`, `CLS`, `cur_set` and `plot` each become a few `OUT`s. The
   PicoCalc-only routines live in `src/pc.asm`. DRAW becomes
   one host `line` command, because coordinates above 255 would otherwise need
   a 16-bit rewrite of the Z80 line routine. `COORDS` widens to 16-bit x/y.
3. **Keyboard:** no change. The firmware presents the PicoCalc keys as the
   Spectrum matrix, as the rig's typist does, so the ROM's scan, auto-repeat,
   `KEY(k$)` (several keys at once) and BREAK work as they are.
4. **Dropped from the PicoCalc build:** the Spectrum tape pulse code, the
   legacy game loader (`LOAD ""` for game tapes), the key matrix scan and the
   colour-bar boot screen. The ROM still has to fit in 16K, and these drops
   free space there. `BORDER` does nothing and `IN 31` returns 0.

## What changes outside it

- **Z80 core split.** `tools/rig/z80.c` becomes `z80core.c` (CPU only, shared)
  plus the Spectrum shell. The rig and the firmware both build the same core.
- **Rig: PicoCalc mode.** The rig runs `opticos_pc.rom` against a C model of the
  PicoCalc devices (the same code the firmware uses, minus the LCD and I2C
  drivers). The Python tests then run headless on the Mac and read the
  40×40 text buffer directly. This is the main proof before any hardware.
- **Firmware:** `picocalc/` holds a pico-sdk CMake project for RP2350. It has
  ST7796SP SPI, keyboard I2C, PWM audio, and FatFs on SD, and builds `opticos.uf2`
  with the ROM embedded.

## Phases

| # | Delivers | Proof |
|---|---|---|
| P1 | core split; `PICOCALC` flag; geometry equates; rig PicoCalc mode with text display and keyboard | Spectrum ROM byte-identical and its tests pass; PicoCalc ROM boots in the rig, and PRINT/LIST/editor tests pass at 40×40 |
| P2 | colours, FLASH, cursor, scroll, PLOT/DRAW 320×320, boot screen | `tools/rig/test_pc_screen.py` (incl. DRAW pixel-identical to the Spectrum ROM); rig screenshots in `build/picocalc/` |
| P3 | SAVE/LOAD/VERIFY to files through the storage device; CAT | `tools/rig/test_pc_files.py` (host directory as the card; a Spectrum ROM SAVE loads unchanged) |
| P4 | RP2350 firmware: LCD, keyboard, audio, SD; UF2 | boots on your PicoCalc |
| P5 | the PicoCalc guide | [README.md](README.md); the main README points to it |

## Decisions needed

1. **Toolchain.** None of `pasmo`, `arm-none-eabi-gcc`, `cmake` or the pico-sdk
   is on this Mac, and Homebrew has no `pasmo` formula. Proposal: a Docker image
   (`tools/docker/`) with all four, used by `make` and `make picocalc`. That
   gives one reproducible build and installs nothing on the host.
2. **CAT.** It was dropped for the Spectrum (spec §12), but with an SD card,
   files you can't list are awkward. Proposal: bring `CAT` back in the PicoCalc
   build only, listing `/OpticOS/*.tap`.
3. **Game tapes.** First dropped, because games need the Spectrum screen;
   later added back as a Spectrum screen mode (display register 27), which the
   legacy loader turns on (see README.md, "Spectrum games").
