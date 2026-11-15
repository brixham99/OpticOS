# OpticOS on the ClockworkPi PicoCalc

OpticOS also runs on the [ClockworkPi PicoCalc](https://www.clockworkpi.com/picocalc)
with a **Raspberry Pi Pico 2 or Pico 2 W** (RP2350). The OpticBASIC you know
from the Spectrum is all there: the same interpreter, maths, line editor and
programs. It runs on a 320 × 320 colour screen with the PicoCalc's keyboard,
SD card and speakers.

The PicoCalc firmware runs the OpticOS ROM on an emulated Z80 at the
Spectrum's 3.5 MHz, with its 50 Hz interrupt. The Spectrum's hardware
underneath is replaced by a small "PicoCalc machine": a display, the
keyboard, the speaker and an SD card. The ROM is built from the same source
as the Spectrum ROM, with the PicoCalc's display and storage behind
`if PICOCALC`. The Spectrum ROM itself is unchanged, byte for byte. How it
was built, phase by phase, is in [PLAN.md](PLAN.md).

## What is different from the Spectrum

| | ZX Spectrum | PicoCalc |
|---|---|---|
| Text | 64 × 24, 4 × 8 font | **40 × 40**, 8 × 8 font |
| Graphics | 256 × 192 | **320 × 320**, origin bottom left |
| Colour | one attribute per 8 × 8 cell, so two characters share one | one attribute per **character**: colours never clash |
| Storage | tape (SAVE, LOAD, VERIFY) | **SD card**: the same commands, plus **CAT** |
| Sound | the beeper (BEEP, the chime) | the same, on the PicoCalc's speakers |
| Boot | colour bar, banner, `]` | the same, with the banner on two lines |
| Spectrum games | `LOAD ""` from tape | `LOAD` from the card; shown on the Spectrum screen (below) |

The rest of OpticBASIC is the same: the keywords, procedures and functions,
the line editor, `KEY(k$)` and the error messages. Programs are tokenised
the same way, so a program saved on one machine loads on the other
unchanged.

## Spectrum games

OpticOS's legacy loader runs Spectrum software on the PicoCalc as it does on
a Spectrum. When it starts a Sinclair BASIC program (a game's loader), the
PicoCalc shows the **Spectrum screen**: `$4000–$5AFF` in the Spectrum's own
layout, 256 × 192 pixels in the middle of the panel, inside the border colour
that `BORDER` or `OUT 254` sets. OpticOS's own display comes back at its next
`]` prompt. A program can switch itself with `OUT 27*256+209, 1` (and `0`).

Put a game's `.tap` file in the `OpticOS` folder and `LOAD` it (by its file
name or its program's name), or `LOAD ""`. What works:

* games whose `.tap` has an ordinary BASIC loader that loads its blocks
  through the ROM (`LOAD "" CODE`, `LOAD "" SCREEN$`), as most do: the same
  games that load with OpticOS on a Spectrum;
* the keyboard (the Spectrum's keys, as above), the beeper, and a **Kempston
  joystick**: the arrow keys, with **Ctrl** or **Alt** as fire (`IN 31`).

What doesn't:

* turbo and protected loaders (common in `.tzx` files), which time the tape
  signal themselves: there is no tape signal; and snapshots (`.z80`, `.sna`);
* text a loader PRINTs (it goes to OpticOS's display, which is hidden while
  the Spectrum screen shows), and software that needs the Spectrum ROM's own
  routines beyond the entry points OpticOS keeps.

A dedicated PicoCalc Spectrum emulator will run more games; this is for
loading them from inside OpticOS.

## Getting it onto the PicoCalc

You need `build/fw/opticos.uf2`. It is built in Docker, so nothing has to be
installed on your computer but Docker:

```
docker build -t opticos-build tools/docker        # once: pasmo, gcc, cmake, the pico-sdk, picotool, FatFs
docker run --rm -v "$PWD":/src opticos-build make all picocalc
```

`make all` assembles both ROMs (`build/opticos.rom` and the PicoCalc one,
`build/opticos_pc.rom`); `make picocalc` builds the firmware with the
PicoCalc ROM inside it, in `build/fw/`.

To flash it, hold **BOOTSEL** on the Pico and plug its own micro-USB port into
your computer. Copy `opticos.uf2` onto the `RP2350` drive that appears; the
drive goes away and the PicoCalc starts OpticOS: the colour bar, the start-up
chime and the `]` prompt.

`build/fw/` also has two bring-up programs, for when something doesn't work:

* `lcdtest.uf2` fills the screen red, green, blue, white, once a second, and
  blinks the keyboard light.
* `soundtest.uf2` plays three rising tones, and reports on the serial console.

**Serial console.** The PicoCalc's **USB-C** port carries the Pico's UART at
115200 baud (on a Mac it appears as `/dev/cu.usbserial-…`). OpticOS reports
there every 5 seconds how long a frame takes to emulate: about 0.3 ms at the
prompt and 9 ms running BASIC flat out, of the 20 ms a frame has.

## The keyboard

The PicoCalc's keys are shown to the ROM as the Spectrum's key matrix, so
OpticOS's own keyboard handling works as it is: auto-repeat, `KEY(k$)` with
several keys at once, `INKEY$` and BREAK. You type what is printed on the
PicoCalc's keys; you never need the Spectrum's shift combinations.

| PicoCalc key | Does |
|---|---|
| letters, digits, symbols | type themselves (Shift for capitals and the upper symbols) |
| Enter | ENTER |
| Backspace, Del | DELETE (the character left of the cursor) |
| ← → | move the cursor along the input line |
| ↑ ↓ | move the current-line marker (and relist around it) |
| **F1** | **EDIT**: copy the current line into the input line |
| **Esc**, Break | **BREAK**: stops a running program, or LIST at `cont?` |
| Ctrl, Alt | fire on the Kempston joystick (with the arrows), for games |

`[ ] { } \ | ~` are typed for you through the Spectrum's E mode, so they
don't auto-repeat. Tab, Caps Lock and F2–F10 do nothing yet.

## Files on the SD card

Use a card formatted FAT32 (or exFAT). OpticOS keeps its files in a folder
called **`OpticOS`**, which it makes the first time it saves. A file can be
copied in or out on any computer.

* **`SAVE "name"`** writes `OpticOS/name.tap`; `SAVE "name" CODE start, length`
  saves bytes. The files are ordinary `.tap` files, the format Spectrum
  emulators use: a `.tap` saved by OpticOS on the Spectrum loads on the
  PicoCalc, and the other way round. A name is up to 10 characters, as on
  tape; characters a card can't hold in a file name (such as `/` or `:`)
  become `_` in the file's name.
* **`CAT`** lists the `.tap` files, without `.tap`, in name order. It shows
  `No files` for an empty folder, and `No SD card` when there is no card it
  can read. (CAT is a PicoCalc-only keyword: the Spectrum ROM has no room
  for it.)
* **`LOAD "name"`** reads the card as one long tape: the `.tap` files in name
  order, one after another. It loads the program called *name* from
  wherever it is, so a file can hold many programs, as a tape does. If
  *name* is a file's name instead (or its first 10 characters), it loads
  that file's first program: `LOAD "picocalc_examples"` loads the examples
  menu. Like a tape, it reads on from where the last LOAD stopped, so a
  program can `LOAD "" CODE` the block that follows it. It goes round from
  the first file once if it must.
* **`LOAD ""`** loads the next program along: at first, the first one on the
  card. `LOAD "name" CODE [start]` and `VERIFY` work as they do on tape.
* A missing file, a card error or no card at all reports
  **`Tape: bad or missing block`**, as a bad tape would.

## Examples

[`examples/picocalc/picocalc_examples.tap`](../../examples/picocalc) holds the
example programs redone for the PicoCalc's screen, with Happy Bat ported to
it. Copy it into the `OpticOS` folder and type `LOAD "picocalc_examples"`.

## Machine code: the PicoCalc's devices

The Z80 sees the Spectrum's 64K map: the ROM at `$0000–$3FFF` and RAM above it.
`$4000–$59FF` is free RAM (6.5K) on the PicoCalc, unless you show it as the
Spectrum screen; the ROM keeps its graphics position at `$5A00–$5A03`, and
the system variables from `$5B00` are where the Spectrum has them. FRAMES, the keyboard on port `$FE`, the speaker (bit 4 of
port `$FE`), IM 1 and the published ROM entry points work as on the Spectrum.
`SA-BYTES` (`$04C2`) and `LD-BYTES` (`$0556`) take the usual registers and
read and write the card.

**The display** is port `$D1`. Write a value with `OUT (C),A`, with C = `$D1` and
**B = the register**. From BASIC, that is `OUT register * 256 + 209, value`.

| B | Register | |
|---|---|---|
| 0, 1 | COL, ROW | the text cell, 0–39 each |
| 2, 3, 4 | ATTR, MASK, FLAG | colours (ATTR_T), their transparent bits (MASK_T), OVER (bit 0) and INVERSE (bit 2) |
| 5 | GLYPH | draw character A (32–127) at COL, ROW |
| 6 | CELL | set the cell's attribute to A |
| 7 | SCRL | scroll the text up a row; A = the new row's attribute |
| 8 | CLS | clear every pixel; every cell gets attribute A |
| 9 | CUR | invert the cell at COL, ROW |
| 10, 11 / 12, 13 | X / Y | a pixel position, low and high byte; y from the bottom |
| 14, 15, 16 | PLOT, LINE, MOVE | plot X, Y; a line to it from the last point; or just move there |
| 17 | BCOL | the byte column (0–39) for byte access; empties the row pattern |
| 18, 19 | BLINE | the line (0–319, from the top), low and high byte |
| 20 | BPUT | store byte A (8 pixels, bit 7 leftmost), then the next column |
| 21 | BXOR | XOR byte A in, then the next column; the hit latch collects A AND the old byte |
| 22 | HIT | `IN`: the hit latch, which is then cleared (an `OUT` clears it too) |
| 23 | NEXT | the next line, back at the column BCOL set |
| 24 | RLD | scroll the line 4 pixels left, A's low nibble coming in at the right; then the next line |
| 25 | PAT | add byte A to the row pattern (up to 8 bytes) |
| 26 | FILL | store the row pattern on A lines (0 = 256) down from the line |
| 27 | MODE | A = 1: show the Spectrum screen (`$4000–$5AFF`, the border); 0: this display |

Registers 0–16 are what the ROM uses for PRINT, CLS, scrolling, the cursor,
PLOT and DRAW. Registers 17–26 are the PicoCalc's answer to the Spectrum's
screen memory, for machine code written for the PicoCalc; register 27 shows
the real Spectrum screen instead, for software written for the Spectrum. This puts 8 lit pixels at byte column 5 of
line 100:

```
        ld c,$D1
        ld b,17
        ld a,5
        out (c),a           ; BCOL = 5
        inc b
        ld a,100
        out (c),a           ; line 100 (low byte)
        inc b
        xor a
        out (c),a           ; (high byte)
        ld b,20
        ld a,$FF
        out (c),a           ; BPUT: 8 pixels
```

The colour of those pixels is their cell's attribute, set with COL, ROW and
CELL. Happy Bat's code (`examples/picocalc/src/happybat_pc.asm`) uses all of
these. The display device is `emu/picocalc.c`, the same C code in the
firmware and in the test rig.

## The test rig

The headless rig (`tools/rig`) runs the PicoCalc ROM on the same machine code
as the firmware (`emu/picocalc.c`, with a host directory standing in for the
SD card), so most of this was proven on a computer before it ran on a
PicoCalc. `OPTICOS_MACHINE=picocalc` runs the shared tests on the PicoCalc
ROM, and these are PicoCalc only:

| Test | Checks |
|---|---|
| `test_pc_screen.py` | boot screen, cursor, colours and colour 8, CLS, scrolling, PLOT/DRAW on 320 × 320, and DRAW pixel-for-pixel against the Spectrum ROM |
| `test_pc_files.py` | SAVE, LOAD, VERIFY, CODE and CAT; LOAD by name across files; a program saved by the Spectrum ROM |
| `test_pc_sound.py` | the chime and BEEP pitches and lengths, and the firmware's samples |
| `test_pc_examples.py` | the examples tape: the menu and every example |
| `test_pc_happybat.py` | Happy Bat, played by an autopilot |
| `test_pc_spectrum.py` | a Sinclair game tape: the Spectrum screen and border, back to OpticOS at the prompt; the Kempston joystick |

```
docker run --rm -v "$PWD":/src opticos-build sh -c 'make all rig && python3 tools/rig/test_pc_screen.py'
```

## How the firmware is laid out

`picocalc/` is a pico-sdk project for the RP2350, built at 133 MHz and run
from RAM:

* **core 0** runs the Z80 (`emu/z80core.h`, shared with the Spectrum rig) and
  the PicoCalc machine (`emu/picocalc.c`) one 50 Hz frame every 20 ms. After
  each frame it turns the speaker's edges into 625 samples (`main.c`). A timer
  interrupt plays them at 31.25 kHz as PWM on GPIO 26, 27 and 28 (`audio.c`).
  Disk accesses happen here too, inside the Z80's `OUT`
  (`storage_sd.c`: FatFs from carlk3's no-OS-FatFS library, on SPI0).
* **core 1** polls the keyboard controller over I2C (`kbd.c`) and copies the
  rows that changed to the ST7796SP screen over SPI1 (`lcd.c`): OpticOS's
  40 × 40 display, or in Spectrum mode the Spectrum screen and its border.

Notes for anyone changing it:

* The panel is an ST7796SP, which PicoMite also uses, not the ILI9488 in
  ClockworkPi's example code. It needs 16-bit pixels, and a short pause
  around CS and DC changes; without it the panel drops command bytes.
* The firmware enables interrupts first thing (`cpsie i`). It can be
  started with them masked, which left sound (and USB) silent.
* The Pico's own USB port isn't used for a console; the USB-C port's serial
  is.
