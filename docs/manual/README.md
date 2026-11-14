# OpticOS / OpticBASIC user manual

- **[OpticOS_User_Manual.pdf](OpticOS_User_Manual.pdf)**: A5, 68 pages, British English.
- `manual.md` is the source, `template.html` the page design (Tinos and IBM Plex Mono, the Optica logo on the cover and in the page headers). `python3 build.py` writes `manual.html` and the PDF with headless Chrome, in two passes so that the contents page gets its page numbers.
- `examples/*.bas` are the worked examples in chapter 13. `python3 verify.py` types each into the ROM in the test rig, runs it and lists it; `examples/verified_output.txt` is its output for this edition. The last example, Happy Bat, is a game: `hbloader.bas` (its machine code as type-in DATA lines with check numbers) runs first, then `happybat.bas` is run to its title screen and stopped with BREAK. `examples/happybat.asm` is the machine code source, printed in full in chapter 14.
- The Happy Bat screenshots (`img/run_happybat_*.png`) were taken in Fuse with the v1.0.1 ROM by the tools in [brixham99/happy-bat](https://github.com/brixham99/happy-bat).
- `fuse_shots.py` types the examples into real Fuse (tape traps off) and takes the screenshots in `img/`. The game screenshots and the editing screenshot come from the phase 1 and phase 4 reports.
- `preview/` has PNGs of the cover and one reference page.
