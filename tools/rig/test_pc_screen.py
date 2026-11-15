#!/usr/bin/env python3
"""PicoCalc screen (P2): the boot screen, colours and their transparency
(colour 8), the cursor, scrolling, and PLOT / DRAW on 320x320 pixels.
The same DRAW commands are also run on the Spectrum ROM, which must light
the same pixels (the display device draws lines with the ROM's algorithm).
Runs on the PicoCalc ROM whatever OPTICOS_MACHINE says."""
import os, sys, json, subprocess
os.environ['OPTICOS_MACHINE'] = 'picocalc'
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from p3lib import Basic, SYM, shot

fails = 0
def check(name, got, want):
    global fails
    ok = got == want
    print('%-58s %s %s' % (name, 'PASS' if ok else 'FAIL', '' if ok else '%r, wanted %r' % (got, want)))
    fails += not ok
def out(b):                    # the last output row above the ] prompt (rows of only pixels skipped)
    return [r for r in b.screen() if r.replace('\ufffd', '').strip()][-2]

b = Basic(); s = b.s
bits, attrs = s.lib.pc_bits, s.lib.pc_attrs
def px(x, y): return bits()[(319 - y) * 40 + (x >> 3)] >> (7 - (x & 7)) & 1
def at(col, row): return attrs()[row * 40 + col]
def cell(col, row): return [bits()[(row * 8 + r) * 40 + col] for r in range(8)]
ATTR_P = lambda: s.peek(SYM['ATTR_P'])

# ---- boot screen
r = b.screen()
check('boot: colour bar of the 8 BRIGHT colours, 5 cells each',
      [at(c, 0) for c in range(40)], [0x40 | (c // 5) * 9 for c in range(40)])
check('boot: banner on two lines, then the version', r[2:5],
      ['OpticOS (c) 2026', 'Optica Technology Design', 'OpticBASIC v1.0.3'])
check('boot: the bar has no pixels', any(bits()[r * 40 + c] for r in range(8) for c in range(40)), False)
shot(s, 'pc_boot.png')

# ---- cursor: the cell at the print position inverts every 16 frames
b.line('CLS'); s.run_until(SYM['cg_lp'], 10_000_000)
col, row = s.peek(SYM['S_POSN']), s.peek(SYM['S_POSN'] + 1)
seen = set()
for _ in range(40):
    s.frame(1); seen.add(tuple(cell(col, row)))
check('cursor blinks: the cell goes solid and back', sorted(seen), sorted({(0,) * 8, (255,) * 8}))

# ---- colours: one attribute per 8x8 cell, so no clash with a neighbour
b.line('CLS'); b.line('PRINT AT 5,3; INK 2; PAPER 6; "AB"')
check('PRINT INK/PAPER colours its own cells', (at(3, 5), at(4, 5)), (0x32, 0x32))
check('...and not its neighbours', (at(2, 5), at(5, 5)), (ATTR_P(), ATTR_P()))
b.line('PRINT AT 6,0; "C"'); check('temporary colours end with the PRINT', at(0, 6), ATTR_P())
b.line('BRIGHT 1: FLASH 1: PRINT AT 7,0; "x": BRIGHT 0: FLASH 0')
check('BRIGHT / FLASH statements', at(0, 7) & 0xC0, 0xC0)
b.line('PAPER 3: INK 7: CLS')
check('CLS paints every cell with PAPER/INK', set(attrs()[i] for i in range(1600)), {0x1F})
b.line('PAPER 0: INK 7: CLS')

# colour 8 keeps the cell's own colour, for PRINT and for PLOT / DRAW (as test_phase5, row 0 = y 312-319)
def eight(cmd):
    b.run(['PRINT AT 0,0; PAPER 1; INK 7; STRING$(8, " ");', cmd])
eight('PRINT AT 0,0; PAPER 8; INK 2; "x";'); check('PRINT PAPER 8 keeps the paper', '%02X' % at(0, 0), '0A')
eight('PAPER 3: PAPER 8: INK 4: PLOT 8, 319'); check('PLOT after PAPER 8 keeps the paper', '%02X' % at(1, 0), '0C')
eight('INK 8: PAPER 5: PLOT 16, 319: DRAW 7, 0'); check('DRAW with INK 8 keeps the ink', '%02X' % at(2, 0), '2F')
b.run(['PRINT AT 0,0; PAPER 1; INK 7; BRIGHT 1; FLASH 1; STRING$(8, " ");', 'BRIGHT 8: FLASH 8: INK 2: PAPER 6: PLOT 24, 319'])
check('PLOT with BRIGHT 8, FLASH 8 keeps both', '%02X' % at(3, 0), 'F2')
eight('INK 2: PAPER 6: PLOT 0, 319'); check('PLOT without 8 sets ink and paper', '%02X' % at(0, 0), '32')
b.line('INK 7: PAPER 0: CLS')

# ---- scrolling: text and its colours move up together; the new row gets ATTR_P
b.run(['PRINT PAPER 2; "red"', 'FOR i=1 TO 50: PRINT i: NEXT'])
r = b.screen()
red = [rw for rw in range(40) if at(0, rw) == 0x17]
check('scroll: the last numbers end at the bottom', r[37:39], ['49', '50'])
check('scroll: "red" and its paper scrolled off together', (red, 'red' in r), ([], False))
check('scroll: the rows that came in have ATTR_P', set(at(c, 39) for c in range(40)), {ATTR_P()})

# ---- PLOT and DRAW on 320 x 320 pixels
def gx(): return s.dpeek(SYM['GX']), s.dpeek(SYM['GY'])
b.line('CLS'); b.line('PLOT 0,0: PLOT 319,319: PLOT 100,50')
check('PLOT corners and a point', (px(0, 0), px(319, 319), px(100, 50), px(101, 50)), (1, 1, 1, 0))
check('PLOT sets the last point', gx(), (100, 50))
check('PLOT colours the pixel\'s 8x8 cell', at(100 >> 3, (319 - 50) >> 3), ATTR_P())
b.line('CLS'); b.line('PLOT 10,10: DRAW 20,5: DRAW TO 10,300')
check('DRAW relative ends at the target', (px(30, 15), gx() == (10, 300)), (1, True))
check('DRAW TO reaches y 300 (beyond the Spectrum\'s 191)', px(10, 300), 1)
b.line('CLS'); b.line('PLOT 200,200: DRAW -50,-30')
check('DRAW with negative steps', (px(150, 170), gx()), (1, (150, 170)))
b.line('CLS'); b.line('PLOT 0,0: DRAW TO 319,319')
check('DRAW the full diagonal', all(px(i, i) for i in range(320)), True)
b.line('CLS'); b.line('OVER 1: PLOT 5,5: PLOT 5,5: OVER 0: INVERSE 1: PLOT 6,6: INVERSE 0')
check('OVER flips, INVERSE clears', (px(5, 5), px(6, 6)), (0, 0))
for cmd in ('PLOT 320,0', 'PLOT 0,320', 'PLOT 10,160: DRAW TO 400,0', 'PLOT 10,160: DRAW -11,0'):
    b.line('CLS'); b.line(cmd)
    check('out of range: %s' % cmd, out(b), 'Value outside range')
check('...and the last point is unchanged', gx(), (10, 160))
b.line('CLS'); b.line('PLOT -1,0'); check('PLOT -1,0 is an error', out(b) in ('Value outside range', 'Bad argument'), True)

# ---- the same lines as the Spectrum ROM, pixel for pixel (y < 150: clear of the text rows on both)
DRAWS = ['PLOT 120,70: DRAW 100,23', 'PLOT 120,70: DRAW 17,70', 'PLOT 120,70: DRAW -90,40',
         'PLOT 120,70: DRAW -13,-60', 'PLOT 120,70: DRAW 60,-61', 'PLOT 20,20: DRAW TO 230,140',
         'PLOT 40,140: DRAW TO 41,5', 'PLOT 5,5: DRAW 0,100: DRAW 100,0: DRAW 0,-100: DRAW -100,0']
def lit(bm_px, w):
    return sorted((x, y) for y in range(150) for x in range(w) if bm_px(x, y))
spec = subprocess.run([sys.executable, '-c', '''
import os, sys, json
os.environ.pop("OPTICOS_MACHINE", None)
sys.path.insert(0, %r)
from p3lib import Basic
b = Basic(); res = []
for cmd in %r:
    b.line("CLS"); b.line(cmd); bm = b.s.bitmap()
    res.append(sorted((x, y) for y in range(150) for x in range(256) if bm[191 - y][x]))
print(json.dumps(res))
''' % (HERE, DRAWS)], capture_output=True, text=True)
want = [[tuple(p) for p in l] for l in json.loads(spec.stdout)] if spec.returncode == 0 else None
if want is None: print(spec.stderr)
for cmd, w in zip(DRAWS, want or [None] * len(DRAWS)):
    b.line('CLS'); b.line(cmd)
    check('same pixels as the Spectrum ROM: ' + cmd, lit(px, 320), w)

# a picture for the eye
b.line('INK 7: PAPER 0: CLS')
b.run(['FOR i=0 TO 319 STEP 16', 'INK 1+(i/16) MOD 7: PLOT i,0: DRAW TO 319-i,319', 'NEXT',
       'PRINT AT 18,13; INK 0; PAPER 7; BRIGHT 1; " OpticOS "', 'PRINT AT 20,11; INK 6; FLASH 1; "40 x 40 text"'])
shot(s, 'pc_gfx.png')
print('%d failure(s)' % fails); sys.exit(1 if fails else 0)
