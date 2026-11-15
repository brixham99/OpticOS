# Happy Bat for the PicoCalc

`happybatpc.tap` is Happy Bat ported to OpticOS on the ClockworkPi PicoCalc
(40 × 40 text, 320 × 320 pixels). The ZX Spectrum version on
`../opticos_examples.tap` is unchanged; this is a separate game with its own
names, so both can sit on the same SD card.

| Block | Type | What |
|---|---|---|
| `happybatpc` | Program, AUTO `start` | the game in OpticBASIC (`happybat_pc.bas`) |
| `hbcodepc` | CODE 60000,1024 | its machine code (`happybat_pc.asm`) |

## Playing

Copy `happybatpc.tap` to the `OpticOS` folder on the SD card, then type
`LOAD "happybatpc"`. The program starts itself, loads `hbcodepc` and shows the
title screen. SPACE flaps; BREAK stops. Once the code is in memory, RUN starts
the game again without loading it.

## What changed from the Spectrum version

The game is the same: the flight physics, the pipes and their gaps, the
scoring and the pacing (a step every 2 frames, 25 a second). The screen is
not:

* **Layout.** The playfield is 288 lines tall (Spectrum: 160), between the
  score line (rows 0–1) and the ground (row 38) and help text (row 39). The
  pipes come in from 80 nibbles (320 pixels) and the bat flies at x = 80. The
  bat's height and the gap lines are now two-byte values, so BASIC uses DPOKE
  for them, and the parameter block moved (see the top of either source).
  The title and game-over text sits to the right of the bat.
* **Drawing.** On the Spectrum the code writes screen memory. On the PicoCalc
  the screen belongs to the display device (port `$D1`), so the code uses
  its byte access: PUT and XOR bytes along a line (XOR latches any pixel it
  lands on, for the collision test), RLD to scroll a ground line, and a row
  pattern FILLed down many lines, so a pipe takes about 30 `OUT`s where
  writing every byte would take over 1,400. Colours are set per 8 × 8 cell, as
  on the Spectrum.

## Building

    python3 examples/picocalc/mktape_pc.py

assembles `happybat_pc.asm` (pasmo), types `happybat_pc.bas` into the
PicoCalc ROM in the test rig, saves both blocks with OpticOS's own SAVE and
checks them, and writes `happybatpc.tap`. `tools/rig/test_pc_happybat.py`
then plays it in the rig: the title screen, a game flown by an autopilot
that has to score, and game over (screenshots in `build/picocalc/`). Both
need the ROMs built first (`make`); the Docker image (`tools/docker`) has
everything.
