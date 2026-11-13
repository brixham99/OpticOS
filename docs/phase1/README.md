# OpticOS Phase 0 and Phase 1 report

13 November 2026. This phase covers the rig plus boot, screen, keyboard, tape, the compatibility entry points and the legacy loader. There is no OpticBASIC yet.

## Phase 0: the rig (`tools/rig/`)

- **`z80.c`** is a new full Z80 core, written from scratch. It covers the main, CB, ED, DD/FD and DDCB/FDCB instruction groups, including the undocumented IXH/IXL/IYH/IYL forms, SLL, the DDCB register copies, `IN F,(C)`, `OUT (C),0`, the X/Y flags and MEMPTR. It passes **zexdoc 67/67** and **zexall 67/67** (`python3 tools/rig/zex.py zexdoc|zexall`, about 30 s each). The exerciser `.com` files are downloaded into `tools/rig/tests/cache/` and are not committed.
- The Spectrum shell runs a 16K write-protected ROM from `$0000`. It provides the 50 Hz INT (IM 0/1/2, with the EI delay), the keyboard matrix, Kempston, approximate ULA contention, border/beeper/MIC output with an edge recorder, and **EAR input fed from a TAP file**. The feed is built from the standard pilot, sync, bit and pause timings, and can be sped up or slowed down for tolerance tests.
- **`rig.py`** is the Python front end. It handles booting, frames, typing text (including SYMBOL SHIFT and E mode), calling ROM routines with chosen registers, TAP to pulses, recorded pulses back to blocks, screenshots, and a 64-column screen-to-text decoder.
- **`test_phase1.py`** holds the Phase 1 tests. Run it with `--ref /path/to/48.rom` to add the black-box comparisons against the Sinclair ROM. That ROM is only executed, never read into the source or committed.

## Phase 1: the ROM (`src/`)

Build it with `make` or `./build.sh`, which runs `pasmo --bin src/opticos.asm` and produces `build/opticos.rom` at exactly 16,384 bytes. `tools/check_layout.py` checks every fixed address and makes sure no section runs into the next fixed point. `tools/similarity_check.py` is the clean-room gate from spec §1.3.

| Module | File | What it does |
|---|---|---|
| Restarts, NMI | `opticos.asm` | RST 0/8/16/40, IM 1 ISR at `$0038`, NMI at `$0066` (jumps to NMIADD if it is non-zero, with the Sinclair bug fixed), RST 40 raises "Calculator not supported" |
| Boot | `boot.asm` | RAM test (48K or 16K), P_RAMT, RAMTOP `$FF57`, UDG, system variables, K/S/R/P channels, streams, IM 1, colour bar, banner |
| Keyboard | `keyboard.asm` | Matrix scan in the ISR: debounce, REPDEL/REPPER auto-repeat, CAPS/SYMBOL, caps lock (CAPS+2), E mode (CAPS+SYM then Y U F G D S A for `[ ] { } \ \| ~`), CAPS+digit editing codes, LAST_K and FLAGS bit 5 |
| Print | `print.asm` | 64-column output with the 4×8 font at `$3E80`, masked nibble merge, INVERSE, OVER, INK/PAPER/FLASH/BRIGHT (including 8 = transparent), AT, TAB, comma, backspace, wrap, scroll, RST 16 through CURCHL. PR_OUT is at `$0970`, so `POKE 23739,111` turns it into the RET at `$096F`. |
| CLS | `cls.asm` | CLS at `$0D6B` and CL-ALL at `$0DAF` |
| Tape | `save.asm`, `load.asm`, `edge.asm` | SA-BYTES at `$04C2`, LD-BYTES at `$0556`, LD-EDGE-2/1 at `$05E3`/`$05E7` (358 T delay, 59 T per sample, the same B/C/carry contract), common exit with BREAK reported as error D |
| Sound | `sound.asm` | BEEPER at `$03B5`: DE = cycles, HL = period, with a period of 8·HL+241 T |
| Stubs | `stubs.asm` | CHAN-OPEN at `$1601`, PR-STRING at `$203C`, PIXEL-ADD at `$22AA` (the Sinclair 175−y convention) |
| Errors | `errors.asm` | RST 8 handler (ERR_NR, then unwinding to ERR_SP) and OpticOS messages |
| Console | `console.asm` | Minimal Phase 1 direct mode: the `] ` prompt, line input with a blinking 4×8 cursor, `LOAD ""` and `CLS` |
| Legacy shim | `legacy.asm` | Loads Sinclair BASIC at `$5CCB` and interprets BORDER, INK, PAPER, FLASH, BRIGHT, CLS, CLEAR, POKE, RANDOMIZE [USR], LOAD "" [CODE \| SCREEN$], PRINT (strings, numbers, AT, `; , '`), REM, GO TO and RUN, with `+ - *`, USR, PEEK, VAL "n", BIN and hidden 5-byte numbers |

### Boot screen

Row 0 is a 16-swatch colour bar made from attribute cells only: normal black to white, then BRIGHT black to white, each swatch two cells wide. Row 1 holds `OpticOS (c) 2026 Optica Technology`, row 2 is blank, and row 3 shows the `] ` prompt with the cursor at column 2. The rig checks that the ROM's screen matches `assets/opticos_boot.png` exactly.

## Test results (rig, `test_phase1.py --ref 48.rom`)

| Test | Result | Detail |
|---|---|---|
| row 0 has no text (colour bar only) | PASS | '' |
| boot banner text at row 1 | PASS | 'OpticOS (c) 2026 Optica Technology' |
| row 2 blank, row 3 prompt "] " | PASS | ['', ']'] |
| cursor position row 3 col 2 | PASS |  |
| RAM test found 48K (P_RAMT=$FFFF) | PASS | 0xffff |
| RAMTOP default $FF57 | PASS | 0xff57 |
| row 0 colour bar: 16 paper swatches x 2 cells | PASS | 00 09 12 1B 24 2D 36 3F 40 49 52 5B 64 6D 76 7F |
| row 0 has no ink pixels | PASS |  |
| rows 1-23 white on black, border 0 | PASS | {7} |
| boot screen matches assets/opticos_boot.png exactly | PASS | 0 differing pixels |
| FRAMES counts 50 per second | PASS | 50 |
| typed text echoes in 64 columns after "] " | PASS | '] The quick brown fox: 0123456789 !@#$%&()_+-=*/?<>;,."[]{}\|~^' |
| unknown command reply, then a new prompt | PASS | ['Phase 1 console: try LOAD ""', ']'] |
| caps lock and delete | PASS | '] ABCx' |
| RST 16 wraps at 64 columns and scrolls | PASS | cursor row 23 col 46 |
| SA-BYTES output decodes to flag+data+parity | PASS | 1 blocks, 302 bytes |
| SA-BYTES pulse timings within tolerance | PASS | pilot 2174, sync 677/729, bit0 862 (844..982), bit1 1723 (1704..1840) T |
| SA-BYTES header pilot is 8063 half-pulses | PASS |  |
| LD-BYTES loads a block at 100% speed | PASS |  |
| LD-BYTES loads a block at 90% speed | PASS |  |
| LD-BYTES loads a block at 110% speed | PASS |  |
| LD-BYTES verify mode (memory empty: must fail) | PASS |  |
| LD-BYTES reports a parity error | PASS |  |
| LD-BYTES rejects a wrong flag byte | PASS |  |
| LD-EDGE-1 B/C/carry vs reference, 300-16000 T | PASS | max \|dB\| = 0 |
| reference LD-BYTES loads an OpticOS-saved block | PASS |  |
| OpticOS LD-BYTES loads a reference-saved block | PASS |  |
| BEEPER period = 8*HL + 241 T (0.3%) | PASS | HL=100 1040/1041; HL=500 4240/4241; HL=1500 12262/12241 |
| LOAD "" runs bounceball (EAR feed, no traps) | PASS | PC=806E after 58 s; ['Bytes: BallCode', 'Program: BounceBall'] |
| Bounce Ball responds to SPACE | PASS |  |
| LOAD "" runs miremare (EAR feed, no traps) | PASS | PC=9837 after 212 s; ['Bytes: MIREMARE$', 'Program: MIRE MARE'] |
| POKE 23739,111 hides the Bytes: line | PASS |  |

Also passing: zexdoc 67/67, zexall 67/67, `check_layout.py` OK, and `similarity_check.py` OK (no run of 12 or more bytes shared with the Sinclair ROM outside the font and filler).

**Real Fuse 1.6.0** (`tools/fuse_phase1.py`, with `--rom-48 build/opticos.rom --no-traps --no-accelerate-loader --no-detect-loader`) boots to the screen above, echoes typing, and loads both games from the real tape signal once `load ""` is typed and the tape is played. Fuse's `--fastload` only speeds up emulation; it is not a trap.

## Screenshots

| File | What it shows |
|---|---|
| `fuse_boot.png` | Boot screen in real Fuse |
| `fuse_console.png` | Typing and a command reply in Fuse |
| `fuse_bounceball.png`, `fuse_bounceball_play.png` | Bounce Ball loaded through OpticOS in Fuse (title, then in play) |
| `fuse_miremare.png` | Mire Mare loaded through OpticOS in Fuse |
| `rig_*.png` | The same in the headless rig, plus a 64-column wrap and scroll test |

## Byte usage against the spec budget (§8.2)

| Spec item | Module | Bytes used | Phase budget | % |
|---|---|---:|---:|---:|
| 1 | Restarts, NMI, reset, RAM test, sysvars, channels | 278 | 380 | 73% |
| 2 | Boot banner text + call | 40 | 40 | 100% |
| 3 | Interrupt routine, keyboard scan, key tables | 355 | 520 | 68% |
| 4 | 64-column print, control codes, colours, scroll, CLS, RST 16 | 578 | 1000 | 58% |
| 8 | Tape low level: SA-BYTES, LD-BYTES, edges, tape_ret | 310 | 380 | 82% |
| 10 | Sound: BEEPER | 82 | 160 | 51% |
| 26 | Errors: RST 8 handler and messages | 271 | 450 | 60% |
| 9 | Tape commands: header search, name match, Program:/Bytes: | 115 | 520 | 22% |
| 27 | Legacy loader shim (interpreter, expressions, PRINT) | 838 | 650 | 129% |
| 13 | Number output (pr_dec, pr_hex shared) | 50 | 550 | 9% |
| 25 | Direct mode and console (phase 1 minimal) | 335 | 250 | 134% |
| 28 | Fixed-address stubs (CHAN-OPEN, PR-STRING, PIXEL-ADD, $096F) | 78 | 200 | 39% |
| 7 | 4-pixel font | 384 | 384 | 100% |
| | **Total (phase 1 modules)** | **3714** | **5484** | |

ROM: 16,384 bytes; 3714 bytes of code and data placed, 12670 free (zero-filled gaps).

Only the modules that exist so far are listed. The legacy shim is **838 bytes against a 650 budget**. It interprets more than the bare minimum (PRINT, GO TO and RUN, VAL, multiplication). The spec's cut list already allows it to be slimmed by about 200 bytes, and its expression code can be shared with OpticBASIC in Phase 3. The console is over budget because it is a temporary Phase 1 console that Phase 3/4 direct mode replaces.

## Known limitations and deviations

- **Mire Mare's text is unreadable under OpticOS.** At start-up the game builds its font from the Sinclair ROM's 8×8 character set at `$3D00` (`font_init`), and decision 1 left that font out. The game loads and plays, but its lettering comes out as garbage. There are two fixes: give Mire Mare its own embedded font (we own the source), or revisit decision 1 (+768 bytes).
- MODE 32, block graphics (128–143) and UDG printing (144–164) are not in Phase 1. Codes of 128 and above print as `?` for now. The legacy shim doubles the column in `PRINT AT` instead of switching to MODE 32.
- BEEPER uses AF′ and IX, as the original's contract allows. Long periods run about 0.2% slow because of the outer-loop overhead.
- Some error texts are worded differently from Sinclair's (the clean-room gate flagged the traditional wording), for example "Tape: bad or missing block".
- CHAN-OPEN sets CURCHL only. It does not set the Sinclair channel flags.
