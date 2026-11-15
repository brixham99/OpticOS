# OpticOS examples for the PicoCalc

`picocalc_examples.tap` holds the example programs for OpticOS on the
ClockworkPi PicoCalc (40 × 40 text, 320 × 320 pixels): the same eleven
programs as the Spectrum tape (`../opticos_examples.tap`, unchanged), with
the ones that drew for the Spectrum's screen redone for the PicoCalc's, and
Happy Bat ported. All were saved by the OpticOS PicoCalc ROM itself.

## Loading

Copy `picocalc_examples.tap` to the `OpticOS` folder on the SD card. Then:

* `LOAD "picocalc_examples"` loads the first program, `examples`, which starts
  itself and lists the others. (A name that is a file's name loads that
  file's first program; `CAT` lists the files.)
* `LOAD "name"` finds that program on the card, then `RUN`. `LIST` shows it.
* `LOAD "happybatpc"` loads Happy Bat, which starts itself and loads its
  machine code, `hbcodepc`, from right after it. SPACE flaps; BREAK stops.

The Spectrum tape's programs have the same names (all but Happy Bat), so keep
only this file on the card, or load the menu first: after it, `LOAD "name"`
reads on from where it is, in this file.

## Programs

| Name | Shows | Source |
|---|---|---|
| `examples` | the menu: a PROC that READs name/description pairs with `RESTORE menu`; starts itself | `src/menu.bas` (PicoCalc) |
| `times` | a times table with `TAB` and `INK` | `../src/times.bas` |
| `guess` | the computer halves its way to a number | `../src/guess.bas` |
| `fact` | recursive functions (`DEF FN … RETURN … ENDFN`) | `../src/fact.bas` |
| `sort` | `DATA`, `RESTORE name`, `SWAP` and arrays | `../src/sort.bas` |
| `errors` | `TRY`, `CATCH` and `ERROR n, msg$` | `../src/errors.bas` |
| `ball` | a bouncing ball inside the 40 × 40 screen; SPACE stops it | `src/ball.bas` (PicoCalc) |
| `tree` | a recursive tree drawn with `DRAW TO`, 1.6 times the Spectrum's | `src/tree.bas` (PicoCalc) |
| `colour` | the eight colours; every character has its own colour cell, so no clash | `src/colour.bas` (PicoCalc) |
| `hilo` | guess my number (`INPUT`, `TRY`, `CASE`) | `src/hilo.bas` (PicoCalc: a line split to fit) |
| `flag` | the Union Flag, 320 × 160, in colour cells and `DRAW` | `src/flag.bas` (PicoCalc) |
| `happybatpc` | **Happy Bat**, the game, for the PicoCalc; runs by itself | `src/happybatpc.bas` |
| `hbcodepc` | Happy Bat's machine code, `CODE 60000,1024` | `src/happybat_pc.asm` |

`(PicoCalc)` marks a version written for the PicoCalc; the others are the
Spectrum versions, which fit 40 columns as they are.

## Happy Bat on the PicoCalc

The game is the Spectrum one: the flight physics, the pipes and their gaps,
the scoring and the pacing (a step every 2 frames, 25 a second). The screen
is not:

* **Layout.** The playfield is 288 lines tall (Spectrum: 160), between the
  score line (rows 0–1) and the ground (row 38) and help text (row 39). The
  pipes come in from 80 nibbles (320 pixels) and the bat flies at x = 80. The
  bat's height and the gap lines are two-byte values, so BASIC uses DPOKE
  for them, and the parameter block moved (see the top of either source).
  The title and game-over text sits to the right of the bat.
* **Drawing.** On the Spectrum the code writes screen memory. On the PicoCalc
  the screen belongs to the display device (port `$D1`), so the code uses
  its byte access: PUT and XOR bytes along a line (XOR latches any pixel it
  lands on, for the collision test), RLD to scroll a ground line, and a row
  pattern FILLed down many lines, so a pipe takes about 30 `OUT`s where
  writing every byte would take over 1,400. Colours are set per 8 × 8 cell, as
  on the Spectrum.

## Building and testing

    python3 examples/picocalc/mktape_pc.py

types each program into the PicoCalc ROM in the test rig, saves it with
OpticOS's own SAVE, checks every block (name, type, the `OB` signature,
parity), assembles Happy Bat's code with pasmo and saves it the same way, and
writes `picocalc_examples.tap`. Then:

    python3 tools/rig/test_pc_examples.py    # loads the menu and runs every example
    python3 tools/rig/test_pc_happybat.py    # plays Happy Bat with an autopilot

Screenshots go to `build/picocalc/`. Build the ROMs first (`make`); the
Docker image (`tools/docker`) has everything.
