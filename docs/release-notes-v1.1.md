# OpticOS v1.1

25 November 2026.

OpticOS v1.1 is the first release with two editions that share the same 16K main ROM.

## Highlights

- **48K edition:** the 16K ROM `opticos.rom`, a drop-in replacement for the Sinclair ROM. OpticBASIC still has no line numbers, and the display is still 64 columns with the condensed 4×8 font.
- **128K edition:** that same main ROM in slot 0, plus the extension ROM `opticos128ext.rom` in slot 1. This adds `SCREEN 0`–`3`, 32-column hi-res text with a new 8×8 font, chunky and attribute modes, `PLOT`/`DRAW`/`BOX`/`CIRCLE`, `SCREEN FLIP`, UDGs and G-mode in mode 1, and SAY/OpticVoice.
- The boot banner now reads `OpticBASIC v1.1`.

## The 48K edition

Use `opticos.rom` in place of the Sinclair 16K ROM.

```
fuse-sdl --machine 48 --rom-48 opticos.rom
```

Everything from v1.0.4 is still there: structured OpticBASIC (no line numbers), the Sinclair-style line editor, 64-column text, `PLOT`/`DRAW`, tape compatibility including `LOAD ""` of ordinary game tapes, and the lower-case `m` with a short middle stem. The main ROM now also carries the hooks used by the 128K edition; on a 48K machine those hooks do nothing.

Main ROM: **16,282** of 16,384 bytes placed, **102 free**. All locked hook addresses are unchanged. A clean-room similarity check against a Sinclair `48.rom` supplied outside the tree still passes (no shared run of 12 or more bytes outside the font and filler).

## The 128K edition

You need **two files**. Do not use a Sinclair 128K ROM in either slot.

| File | Slot | What it is |
|---|---|---|
| `opticos.rom` | 0 | The same 16K OpticOS ROM as the 48K edition |
| `opticos128ext.rom` | 1 | The extension: `SCREEN`, graphics, UDGs and G-mode, SAY/OpticVoice |

```
fuse-sdl --machine 128 --rom-128-0 opticos.rom --rom-128-1 opticos128ext.rom
```

What the extension adds:

- `SCREEN 0` — 64-column hi-res text and graphics (the 48K mode).
- `SCREEN 1` — 32-column hi-res text with the new 8×8 font, on the same 256×192 bitmap, so `PLOT`, `DRAW` and `CIRCLE` work as they do in mode 0. The editor, `INPUT` and `LIST` run at 32 columns. OpticBASIC still has no line numbers.
- `SCREEN 2` — chunky 64×48 graphics.
- `SCREEN 3` — attribute 32×24 graphics.
- Text printed in mode 2 or 3 returns to the last text mode used (0 or 1).
- `PLOT`, `DRAW`, `BOX`, `CIRCLE` and `POINT` in every screen mode; `SCREEN FLIP` in modes 2 and 3.
- UDGs in mode 1 only: 21 glyphs at codes 144–164, 8×8, POKEd into the UDG area above RAMTOP. In mode 0 they print as `?` and the stored byte is left intact. G-mode (Caps+9, keys a–u) inserts those codes in mode 1, inside strings only.
- SAY / OpticVoice, in the same extension ROM.

The extension ROM has **1,204 bytes free**.

Demo tapes: `flags128` (the flag in modes 0, 2 and 3), `circles128` (`CIRCLE` in modes 0–3) and `udg128` (a spaceship and an alien printed as UDGs in mode 1). Load with `LOAD ""`, then play the tape.

## Files for the release

The Sinclair `48.rom`, the Sinclair 128K ROMs, snapshots and memory dumps are **not** included.

| File | Edition | Notes |
|---|---|---|
| `opticos.rom` | 48K, and slot 0 of 128K | 16,384 bytes |
| `opticos128ext.rom` | 128K, slot 1 | 16,384 bytes |
| `opticos_examples.tap` / `.tzx` | 48K | The manual's example tape |
| `flags128.tap` / `.tzx` | 128K | Flag demo, modes 0, 2 and 3 |
| `circles128.tap` / `.tzx` | 128K | Circles in modes 0–3 |
| `udg128.tap` / `.tzx` | 128K | UDG demo in mode 1 |

The user manual (`OpticOS_User_Manual.pdf`) and the specification (`spec.pdf`) have been rebuilt so their title lines show v1.1, and both are attached to this release.

## Tests run on this branch

- Clean-room similarity check: pass.
- Headless rigs, including the 48K suites: `test_phase1` (boot text is `OpticBASIC v1.1`; the boot bitmap matches `assets/opticos_boot.png` exactly), `test_maths`, `test_phase3`, `test_phase4`, `test_phase5`, `test_autoload`, `test_new`, `test_listpage`, `test_screen_gfx` (92 tests), `test_udg` (22/22). All passed.
- `test_phase1` and `test_traps` still fail only on the pre-existing missing file `/workspace/mire-mare-repo/build/miremare.tap` (three “miremare present” cases in `test_traps`; 36 other trap cases passed). This is not a regression.
- A Fuse screenshot of the 48K boot screen was taken and checked: colour bar, `OpticOS (c) 2026 Optica Technology Design`, `OpticBASIC v1.1`, and the `]` prompt with the cursor.

## Documentation

The README now splits the 48K and 128K editions, with a feature comparison table, install instructions, and screen grabs from `docs/screenmodes`. The specification is v0.19. The boot mock-up assets have been regenerated for `OpticBASIC v1.1`.
