# OpticOS example tape

`opticos_examples.tap` (and the same blocks as `opticos_examples.tzx`) holds eleven OpticBASIC programs, each saved by the OpticOS ROM itself in its "Program:" format (a type-0 header, then data starting with the `OB` $01 $00 signature). Every program was loaded and run in Fuse, both from the real tape signal with traps off (`--no-traps --no-detect-loader --no-accelerate-loader`) and with Fuse's tape traps and loader acceleration on (its defaults); the screenshots in `shots/` are from the traps-off runs.

## Loading

Start OpticOS, type a LOAD line, then play the tape (in Fuse: F8).

* `LOAD ""` loads the first program, `examples`, which starts itself (it was saved with `SAVE "examples" AUTO menu`) and prints the menu below.
* `LOAD "name"` skips to that program; the headers it passes are listed as `Program: name`. Then type `RUN`. `LIST` shows the program.

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

The first seven are the verified examples from the user manual (`docs/manual`); `colour`, `hilo` and `flag` are new. The sources are in `src/`.

## Rebuilding

    ./build.sh
    python3 examples/mktape.py        # types each program into the ROM in the test rig and records its SAVE
    python3 examples/fuse_verify.py   # loads and runs each one in Fuse, screenshots into shots/
    python3 examples/fuse_verify.py --traps   # the same with Fuse's tape traps on (screenshots into build/shots_traps/)

`mktape.py` checks every header name, the `OB` $01 $00 signature and the parity bytes before writing the tape.
