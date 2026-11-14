# OpticOS example tape

`opticos_examples.tap` (and the same blocks as `opticos_examples.tzx`) holds twelve OpticBASIC programs and one block of machine code, all saved by the OpticOS ROM itself. The programs are in its "Program:" format (a type-0 header, then data starting with the `OB` $01 $00 signature). The machine code is an ordinary "Bytes:" block (type 3). Every program was loaded and run in Fuse, both from the real tape signal with traps off (`--no-traps --no-detect-loader --no-accelerate-loader`) and with Fuse's tape traps and loader acceleration on (its defaults); the screenshots in `shots/` are from the traps-off runs.

## Loading

Start OpticOS, type a LOAD line, then play the tape (in Fuse: F8).

* `LOAD ""` loads the first program, `examples`, which starts itself (it was saved with `SAVE "examples" AUTO menu`) and prints the menu below.
* `LOAD "name"` skips to that program; the headers it passes are listed as `Program: name`. Then type `RUN`. `LIST` shows the program.
* **Happy Bat** is different: type `LOAD "happybat"` and leave the tape running. It was saved with `SAVE "happybat" AUTO start`, so it runs as soon as it has loaded. Its first line, `CLEAR 59999`, keeps BASIC below its machine code. The next line, `LOAD "hbcode" CODE`, reads the very next block on the tape, `hbcode` (1,095 bytes at 60000), and then the title screen appears. No RUN is needed. If you stop the tape between the two blocks, start it again and the code still loads. `CLEAR` works here because it is in the main program, not inside a procedure. Once the code is in memory (it checks the "HB" signature at 60014), RUN starts the game again without touching the tape.

## Programs

| Name | Shows | Screenshot |
|---|---|---|
| `examples` | The menu: a PROC that READs name/description pairs with `RESTORE menu`; starts itself on loading | [examples.png](shots/examples.png) |
| `times` | A times table with `TAB` and `INK` | [times.png](shots/times.png) |
| `guess` | The computer halves its way to a number | [guess.png](shots/guess.png) |
| `fact` | Recursive functions (`DEF FN … RETURN … ENDFN`) | [fact.png](shots/fact.png) |
| `sort` | `DATA`, `RESTORE name`, `SWAP` and arrays | [sort.png](shots/sort.png) |
| `errors` | `TRY`, `CATCH`, `ERROR n, msg$`, `ERR` and `ERR$` | [errors.png](shots/errors.png) |
| `ball` | A bouncing ball; SPACE stops it | [ball.png](shots/ball.png) |
| `tree` | A recursive tree drawn with `DRAW TO` (about 25 seconds) | [tree.png](shots/tree.png) |
| `colour` | The eight colours as PAPER and INK, BRIGHT, the even/odd column clash rule, FLASH, INVERSE and boxes drawn in each INK | [colour.png](shots/colour.png) |
| `hilo` | Guess my number (spec §4.7): `RANDOMIZE`, `RND`, `INPUT`, `TRY` with `ERROR n, msg$` for bad guesses, `CASE` | [hilo.png](shots/hilo.png), [hilo_loaded.png](shots/hilo_loaded.png) |
| `flag` | The Union Flag in the top 16 rows: blue PAPER cells, white saltire lines with `PLOT` and `DRAW`, thin red diagonals from `INVERSE 1` letting red paper show, and the central cross in whole cells; prints the time it took (about 18 seconds) | [flag.png](shots/flag.png) |
| `happybat` | **Happy Bat**, a Flappy Bird-style game: OpticBASIC runs the game and calls 1,095 bytes of machine code with `CALL`/`USR`, passing values by POKE. SPACE flaps, BREAK stops. Saved with AUTO start, so it runs by itself and loads `hbcode` | [happybat_loaded.png](shots/happybat_loaded.png), [happybat.png](shots/happybat.png) |
| `hbcode` | Happy Bat's machine code, `CODE 60000,1095`. It was made by typing in `src/hbloader.bas` and running it; that program checks every DATA line and saves this block. `src/happybat.asm` is the assembler source | |

The first seven are the verified examples from the user manual (`docs/manual`); `colour`, `hilo` and `flag` are new. `happybat` is the manual's last worked example, and its own repository is [brixham99/happy-bat](https://github.com/brixham99/happy-bat). The sources are in `src/`.

## Rebuilding

    ./build.sh
    python3 examples/mktape.py        # types each program into the ROM in the test rig and records its SAVE
    python3 examples/fuse_verify.py   # loads and runs each one in Fuse, screenshots into shots/
    python3 examples/fuse_verify.py --traps   # the same with Fuse's tape traps on (screenshots into build/shots_traps/)

`mktape.py` checks every header name, the `OB` $01 $00 signature and the parity bytes before writing the tape. For `hbcode`, it types in `src/hbloader.bas`, RUNs it and records the loader's own SAVE. It then checks the bytes against `src/happybat.asm` if `pasmo` is installed.
