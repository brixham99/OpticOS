# OpticOS on the ClockworkPi PicoCalc: design and plan

Target: PicoCalc with a **Raspberry Pi Pico 2 or Pico 2 W (RP2350)**. Status:
all phases done and checked on a PicoCalc with a Pico 2 W. How to build and
use it is in [README.md](README.md); this is how it was designed and built.

## Approach

The OpticOS Z80 code runs on an emulated Z80 inside RP2350 firmware. The
Spectrum hardware underneath it is replaced by a small **PicoCalc machine**
that the firmware implements in C. One source tree builds two ROMs:

| Build | Output | Hardware layer |
|---|---|---|
| Spectrum (unchanged) | `build/opticos.rom` | ULA screen at `$4000`, key matrix, tape pulses |
| PicoCalc | `build/opticos_pc.rom` | I/O-port devices served by the firmware |

The Spectrum ROM stays byte-identical, which the layout check and the rig
tests prove. PicoCalc-only code sits behind `if PICOCALC` (a `pasmo --equ`),
so the two builds share the interpreter, maths, tokeniser and editor.

## The PicoCalc machine

| Device | Z80 side | Firmware side |
|---|---|---|
| CPU | Z80 at 3.5 MHz, 50 Hz IM 1 interrupt, `FRAMES` as on the Spectrum | the shared core (`emu/z80core.h`), no ULA contention; core 0 |
| RAM | the Spectrum's 64K map: ROM `$0000-$3FFF`, RAM above | `$4000-$5AFF` is plain RAM, unless shown as the Spectrum screen |
| Display | port `$D1`, register in B: glyph at (col, row) with attribute and OVER/INVERSE, plot, line, scroll, CLS, cursor; byte access for machine code; the Spectrum screen mode | 320×320 1-bpp bitmap + one attribute per 8×8 cell (40×40), text in the display's own 8×8 font (`emu/font8x8.h`, public domain), Spectrum palette and FLASH; changed rows pushed to the ST7796SP panel (RGB565) over SPI from core 1 |
| Keyboard | unchanged: the Spectrum key matrix on port `$FE` (scan, `KEY(k$)`, BREAK, INKEY$); Kempston on port `$1F` | the I2C keyboard controller, polled; each PicoCalc key held down is shown as its Spectrum keys (e.g. `(` as SYMBOL SHIFT + 8, ← as CAPS SHIFT + 5) |
| Sound | unchanged: port `$FE` bit 4 (BEEP, chime) | beeper edges timestamped in T-states, rendered each frame to 625 samples at 31.25 kHz (`pc_render`) and played as PWM on GPIO 26/27/28, 40 ms behind |
| Storage | `SA-BYTES` / `LD-BYTES` hand each block to a storage device (port `$D3`); `CAT` (PicoCalc only, token `$F2` after all the shared ones) | blocks go to `/OpticOS/<name>.tap` (TAP format) on the SD card through FatFs; the files in name order read as one tape |

Text is **40 columns × 40 rows**: 320×320 pixels in an 8×8 font that the
display device draws. (The first layout, 80×40 in the ROM's 4×8 font, was too
small to read on the PicoCalc's screen.) Graphics are **320×320**, origin
bottom left. The ROM's 4×8 font stays for the Spectrum build.

## What changed in the Z80 source

1. **Geometry equates.** `COLS`, `ROWS`, `GFX_W` and `GFX_H` replace the literal
   64/24/256/192 limits in `print.asm`, `console.asm`, `list.asm`, `gfx.asm`
   and `boot.asm`.
2. **Screen primitives** (PicoCalc build only): `draw_glyph`, `scroll`, `CLS`,
   `cur_set` and PLOT/DRAW each become a few `OUT`s; the PicoCalc-only
   routines live in `src/pc.asm`. DRAW is one display `line` command (the
   device draws with the Spectrum ROM's algorithm, so the same pixels light),
   because coordinates above 255 would otherwise need a 16-bit rewrite of the
   Z80 line routine. The last point is `GX`/`GY` (16-bit) at `$5A00`.
3. **Storage.** `SA-BYTES` and `LD-BYTES` call the storage device; `CAT` is a
   PicoCalc-only keyword after all the shared tokens, so every shared token
   keeps its value and programs move between the machines unchanged. The
   emulator-trap layout checks are Spectrum-only, and `clear.asm` moves into
   the room the tape code left, to make space for the keyword.
4. **The Spectrum screen.** The legacy loader shows the Spectrum screen when
   it runs a Sinclair program, and every prompt shows OpticOS's display
   again (`dev_mode`).
5. **Unchanged:** the keyboard scan (the firmware presents the PicoCalc's keys
   as the Spectrum matrix), the legacy loader, the boot sequence and chime,
   and everything else.

## What changed outside it

- **Z80 core split.** The CPU moved from `tools/rig/z80.c` into
  `emu/z80core.h`, which the Spectrum rig (`z80.c`), the PicoCalc machine
  (`emu/picocalc.c`) and the firmware all build.
- **Rig: PicoCalc mode.** The rig runs `opticos_pc.rom` on `emu/picocalc.c`
  (the same code as the firmware, minus the LCD, keyboard and SD drivers; a
  host directory stands in for the card). The tests run headless and read
  the 40×40 display directly. This was the main proof before any hardware.
- **Firmware:** `picocalc/` is a pico-sdk CMake project for the RP2350 (ST7796SP
  on SPI1, keyboard on I2C1, SD card on SPI0 through carlk3's no-OS-FatFS, PWM
  audio) that builds `opticos.uf2` with the ROM embedded.
- **Toolchain:** a Docker image (`tools/docker/`) with pasmo, gcc, cmake, the
  pico-sdk, picotool and the FatFs library, so nothing is installed on the
  host.

## Phases

| # | Delivered | Proof |
|---|---|---|
| P1 | core split; `PICOCALC` flag; geometry equates; rig PicoCalc mode with text display and keyboard | Spectrum ROM byte-identical and its tests pass; PicoCalc ROM boots in the rig, and the PRINT/LIST/editor tests pass at 40×40 |
| P2 | colours, FLASH, cursor, scroll, PLOT/DRAW 320×320, boot screen | `test_pc_screen.py` (DRAW pixel-identical to the Spectrum ROM) |
| P3 | SAVE/LOAD/VERIFY to files through the storage device; CAT | `test_pc_files.py` (a Spectrum ROM SAVE loads unchanged) |
| P4 | RP2350 firmware: LCD, keyboard, SD, sound; UF2 | runs on a PicoCalc; `test_pc_sound.py` |
| P5 | the PicoCalc guide | [README.md](README.md) |
| — | examples redone for 40×40, Happy Bat ported; the Spectrum screen mode and Kempston joystick | `test_pc_examples.py`, `test_pc_happybat.py`, `test_pc_spectrum.py`; Manic Miner on a PicoCalc |

## Decisions

1. **Toolchain:** a Docker image, not native installs.
2. **CAT:** back in the PicoCalc build only, listing `/OpticOS/*.tap`.
3. **Spectrum games:** first left out, because they need the Spectrum screen;
   then added back as a Spectrum screen mode (display register 27) that the
   legacy loader turns on.
4. **Serial:** the PicoCalc's USB-C port (UART0) carries the console; the Pico's
   own USB is not used.
