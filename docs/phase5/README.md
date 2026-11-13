# Phase 5a: size pass and the core I/O statements

Phase 5 is the polish phase, and its overriding goal is to make the full planned feature set fit the 16K ROM with a 256-byte margin. This first milestone does the cheap part of the size pass and adds the most needed statements: `INPUT`, `DATA` / `READ` / `RESTORE`, and the tape commands `SAVE` / `LOAD` / `VERIFY`, including their `CODE` forms.

![Fuse: a program with INPUT and DATA / READ, listed and run](fuse_input_read.png)

The screenshot was taken in real Fuse (`--no-traps --no-detect-loader --no-accelerate-loader`, via `tools/fuse_phase5.py`). The program was typed with AUTO, listed and run, and `Nathan` was typed in answer to the INPUT.

## What was added

| Statement | Behaviour |
|---|---|
| `INPUT ["prompt";] v [, v …]` | Prints the prompt, then reads one line per variable at the print position. The line is edited with the usual input-line keys (left, right, DELETE, insert). EDIT and the marker keys do nothing during INPUT. A numeric variable takes the text's value, as `VAL` would. String variables, array elements (`INPUT a(2)`) and direct-mode use all work. |
| `DATA items` | Skipped when run, like `REM`. A DATA statement must start its line. Items are any expressions (`DATA "plums", 3*4`). |
| `READ v [, v …]` | Takes the next DATA item. `Out of DATA` (error 20) is raised when there are none left. |
| `RESTORE` | Starts again from the first DATA line. RUN and any program change also restore. |
| `SAVE "name"` | Saves the program as a standard type-0 ("Program:") header and a data block that starts with the signature `"OB" 1 0` (spec §3.1), then the tokenised lines and the end marker. |
| `SAVE "name" CODE start, length` | A standard type-3 ("Bytes:") file |
| `LOAD "name"` / `LOAD ""` | Finds the program and loads it. An `OB` block is moved into place as an OpticBASIC program, with the variables cleared, and you return to the prompt. Any other type-0 block is a Sinclair BASIC program and goes to the legacy loader, as before. |
| `LOAD "name" CODE [start]` | Bytes, at the header's address or at `start` |
| `VERIFY "name" [CODE [start]]` | Compares the tape with memory. A mismatch gives *Tape: bad or missing block*. |

Names are string expressions, padded to 10 characters, and `""` means "the first one found". Every header seen is printed (`Program: squares`) while searching, as before.

## Size pass

- **ASN and ACS were dropped** (the brief allowed it), along with their keywords: −87 bytes. `ATN(x/SQR(1-x*x))` gives ASN.
- **INPUT and READ share one variable-list loop**, and the tape commands share the name parser and the signature writer. LOAD reuses the legacy loader's header search, which gained a verify flag (+7 bytes). The new code was placed in the gaps after the error messages and after the line editor.
- I did not do the remaining maths items from the phase 2 list (STR$ small-integer path, compare, COS from SIN, EXP terms, VAL, register xorshift; about 290 bytes in total). Each one needs the 3,000-case mpmath run and the RNG statistics checked again. Since the ROM still has room for the next features, they are better done when the space is actually needed.

## Bytes

| | Bytes |
|---|---:|
| INPUT, DATA / READ / RESTORE (`input.asm`) | 182 |
| INPUT hooks in the console (read a line and return; editor keys off) | 30 |
| SAVE / LOAD / VERIFY / CODE (`tape.asm`) and the loader changes | 296 |
| New keywords (INPUT DATA READ RESTORE SAVE VERIFY CODE) minus ASN/ACS | 36 |
| Error message *Out of DATA*, RESTORE on RUN, workspace reset on LOAD | 29 |
| ASN / ACS code removed | −77 |
| Old LOAD "" handler removed | −17 |
| **Net** | **+473** |

ROM: **14,899 bytes placed, 1,485 free** (was 14,426 / 1,958).

## Budget: what still has to fit

The spec's budget (§8.2, v0.6) now counts the keyword table for the roughly 45 keywords still to come (about 270 bytes), which the v0.4 projection missed. With that included, the full feature list needs **17,306 bytes**. That is 922 over 16 KB, or **about 1,180 bytes over once the 256-byte margin is kept**. About 1,230 bytes are usable for the remaining features, against about 2,400 bytes of budget.

Proposed ways to close the gap, for Nathan to choose from:

| Option | Saves (approx.) |
|---|---:|
| Remaining maths squeeze (six items above) | 290 |
| Shared argument parsing and RST helpers in the evaluator and statements | 300 |
| Drop `SCREEN$(r,c)`, `ATTR`, `POINT` | 120 |
| Drop `CIRCLE` | 90 |
| Drop `MODE 32` and UDG printing (keep 64 columns only) | 170 |
| Drop `SOUND` (keep `BEEP`) | 40 |
| Drop `FIND`, `CONT`, `ERRLINE`, `ERRPROC$` | 150 |
| Drop `LABEL` / `GOTO` | 100 |
| Trim the legacy loader shim | 150 |

My recommendation: do both squeezes (about 590), drop SCREEN$/ATTR/POINT, FIND/CONT/ERRLINE/ERRPROC$ and SOUND (about 310), and decide on MODE 32 versus CIRCLE and LABEL/GOTO for the rest.

## Tests

| Suite | Result |
|---|---|
| `tools/rig/test_phase5.py` (new) | 20/20: INPUT (echo, prompt, number, string, array element, direct mode), DATA/READ (numbers, strings, expressions, across lines), RESTORE, RUN restores, *Out of DATA*. SAVE recorded from MIC and decoded (header, `OB` signature), LOAD "name" and LOAD "" back through EAR (program lists and runs), VERIFY pass and fail, SAVE CODE / LOAD CODE start / VERIFY CODE. |
| `tools/rig/test_phase4.py` | 13/13 |
| `tools/rig/test_phase3.py` | 49/49 |
| `tools/rig/test_phase1.py` | 35/35, including real game tapes through `LOAD ""` |
| `tools/rig/test_maths.py --n 3000` | 0 failures (ASN/ACS cases removed) |
| zexall | all OK |
| `tools/similarity_check.py` | OK |

`tools/rig/p3lib.py` now leaves the key-wait routine properly when it injects a line, as a real ENTER does. INPUT depends on that.

## Not done yet

In spec priority order: graphics (`PLOT`, `DRAW`, `CIRCLE`), `BEEP` / `SOUND`, `INSTR`, `STRING$`, `HEX$`, `UPPER$`, `ERR$`, `CASE`, `EXIT`, `SWAP`, `MODE 32` / UDGs from BASIC, the colour statements inside PRINT, and the machine statements (`CALL`, `USR`, `OUT`, `IN`, `DPEEK` / `DPOKE`, `KEY`, `JOY`). `SAVE … AUTO`, `SCREEN$` tape forms and `CAT` are also still to do.

---

# Phase 5b: Nathan's cuts, the squeezes, graphics and functions

![Fuse: PLOT and DRAW TO in eight colours, a border drawn with relative DRAW, and a PRINT with INK, PAPER and BRIGHT inside it](fuse_graphics.png)

Real Fuse again (`tools/fuse_phase5.py`). The program fans out lines with `DRAW TO`, cycling `INK`, draws a border with relative `DRAW`, prints a caption with `PRINT AT 11,20; INK 7; PAPER 1; BRIGHT 1;…`, and plays three notes with `BEEP`. Colour clash in the 8×8 attribute cells is as on any Spectrum.

## Decisions recorded (spec §12, items 8–12)

- Dropped: `MODE 32` and UDG printing, `CIRCLE`, `LABEL` / `GOTO` (no `GOSUB`; PROCs replace it), `SCREEN$(r,c)`, `ATTR`, `POINT`, `FIND`, `CONT`, `ERRLINE`, `ERRPROC$`, `SOUND`.
- Labels become PROC names: `RUN name`, `RESTORE name` (the first DATA after that DEF) and `SAVE "x" AUTO name`. These are specified but **not built yet**.
- The legacy shim is kept whole. It already prints at 64 columns and doubles the `PRINT AT` column, so it needed no 32-column path. Bounce Ball and Mire Mare still load (phase 1 tests, 35/35).

## Squeezes

| Squeeze | Saved |
|---|---:|
| GET-CHAR (`tk`), NEXT-CHAR (`skip1`) and "expression → integer" moved into the unused restarts `$18`, `$20`, `$30`; about 80 three-byte `CALL`s became one-byte `RST`s (also faster) | 186 |
| RND: the same xorshift (13, 17, 5) with its state in registers instead of a memory buffer (identical numbers) | 21 |
| A shared "number 0–255" entry, `ev_u8` | 15 |
| **Total** | **222** |

Tried and rejected: sending small integers through the float path in STR$ would save 36 bytes, but printing an integer becomes about 15 times slower (about 80,000 T-states, 23 ms per number). I judged that a bad trade against the integer speed goal and reverted it. The other maths items (COS from SIN, fewer EXP terms, a smaller VAL digit loop; about 130 bytes) are not done yet. Each needs the full mpmath run. The compare routine turned out to be compact already, so the estimated 70 bytes from it are not there.

## What was added

| | |
|---|---|
| `PLOT x,y` | 256×192, origin bottom left (y 0–191). `OVER 1` flips the pixel, `INVERSE 1` clears it, and the 8×8 cell takes the current colours. |
| `DRAW dx,dy` / `DRAW TO x,y` | Lines from the last point (COORDS), stepping along the longer axis. Going off the screen is *Value outside range*. |
| `FLASH`, `BRIGHT`, `INVERSE`, `OVER` | New statements, alongside `INK` and `PAPER` |
| Colours inside PRINT | `PRINT INK 2; PAPER 6; "x"`. INK, PAPER, FLASH and BRIGHT last until the statement ends. INVERSE and OVER inside PRINT stay set, because the print routine has only permanent bits for them. |
| `BEEP duration, pitch` | Sinclair semantics: pitch in semitones from middle C, f = 261.63·2^(p/12), through BEEPER. Middle C measures 261–262 Hz in the rig, and the octave 523 Hz. Pitch is limited to about −24…69 (the period must fit 16 bits). |
| `INSTR(a$, b$ [, start])` | Position or 0. `""` is found at the start position. |
| `STRING$(n, s$)`, `HEX$(n)` (4 digits), `UPPER$(s$)`, `ERR$` | `ERR$` is the last error's message, or `""` if there was none. |
| `IN(port)`, `OUT port, b`, `USR(addr)` (returns BC), `CALL addr`, `DPEEK(addr)`, `DPOKE addr, w`, `JOY` (Kempston port 31) | |
| `SWAP a, b` | Numbers, integers, strings or array elements of the same type. Swapping strings re-points each heap block at its new owner. |

## Bytes

ROM: **15,669 placed, 715 free** (14,899 / 1,485 after 5a). The new code is 238 (graphics) + 196 (BEEP, OUT, DPOKE, CALL, SWAP) + 386 (functions) + 49 (PRINT colours, colour statements, the console's colour reset) + 129 (keywords and dispatch entries), less the 222 bytes saved. The dispatch tables moved out of the full gap J2 into the last section.

## Budget (spec §8.2, v0.7)

With the cuts, the remaining features (CASE, EXIT, `ERROR n, msg$`, CLEAR, RUN/RESTORE/SAVE AUTO with a PROC name, SCREEN$ tape forms, CAT, KEY, FREE, array parameters, CALL register arguments) are budgeted at about 730 bytes. The finished ROM would then be 16,401 bytes, **about 273 bytes over once the 256-byte margin is kept**. In v0.6 that figure was about 1,180. My proposal to close it: drop array parameters by reference (80), CALL register arguments (30), CAT (45) and the SCREEN$ tape forms (25), and do the remaining maths squeezes (about 130).

## Tests

| Suite | Result |
|---|---|
| `tools/rig/test_phase5.py` | 42/42 (22 new): PLOT at the corners and in range, DRAW and DRAW TO paths and end points, COORDS, OVER and INVERSE, range errors, colours inside PRINT ending with the statement, BRIGHT/FLASH, BEEP frequency and length measured from the speaker signal, INSTR (6 cases), STRING$, HEX$, UPPER$, ERR$ in a CATCH, DPOKE/DPEEK, USR and CALL on poked code, IN/JOY, SWAP of numbers and strings (then the string is changed), SWAP type mismatch |
| Phase 1, 3, 4 | 35/35, 49/49, 13/13 |
| `test_maths.py --n 3000` | 0 failures; RND 3,000 values, mean 0.4954, chi-square 11.25 (9 dof), repeatable |
| zexall, similarity check | OK |

## Not done yet

CASE / WHEN / OTHERWISE, EXIT, `ERROR n, msg$`, CLEAR, `RUN name`, `RESTORE name`, `SAVE … AUTO name`, `SCREEN$` tape forms, CAT, `KEY(k$)`, FREE, array parameters, CALL register arguments.
