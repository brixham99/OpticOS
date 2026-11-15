#!/usr/bin/env python3
"""PicoCalc files (P3): SAVE / LOAD / VERIFY through the storage device to
<name>.tap files (a host directory stands in for the SD card's /OpticOS),
and CAT.  A program saved by the Spectrum ROM, through its tape signal, must
load on the PicoCalc unchanged.  Runs on the PicoCalc ROM whatever
OPTICOS_MACHINE says."""
import os, sys, json, shutil, subprocess, tempfile
os.environ['OPTICOS_MACHINE'] = 'picocalc'
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from p3lib import Basic, SYM
from rig import tap_blocks

fails = 0
def check(name, got, want):
    global fails
    ok = got == want
    print('%-58s %s %s' % (name, 'PASS' if ok else 'FAIL', '' if ok else '%r, wanted %r' % (got, want)))
    fails += not ok
TMP = tempfile.mkdtemp(prefix='opticos_sd_')
def card(name):
    d = os.path.join(TMP, name); b.s.sd(d); return d
def rows(): return [r for r in b.screen() if r]
def last(): return rows()[-2]                                 # the last output row, above the ] prompt
def listing(): b.line('CLS'); b.line('LIST'); return [r.lstrip('> ') for r in rows()[1:-1]]
def cat(): b.line('CLS'); b.line('CAT'); return rows()[1:-1]

b = Basic(); s = b.s
PROG = ['FOR i=1 TO 3', 'PRINT i*i', 'NEXT']

# ---- SAVE writes a TAP file: header and data blocks, with good parity
d = card('a')
b.line('NEW'); b.enter(PROG); b.line('SAVE "squares"')
f = os.path.join(d, 'squares.tap')
check('SAVE "squares" makes squares.tap', os.path.exists(f), True)
blk = tap_blocks(f) if os.path.exists(f) else []
check('two blocks: a header (flag 0, 17 bytes) and the data (flag $FF)',
      [(x[0], len(x) - 2) for x in blk][:1] + [x[0] for x in blk][1:], [(0, 17), 0xFF])
check('header: type 0 (program), name padded to 10', (blk[0][1], blk[0][2:12]) if blk else None, (0, b'squares   '))
par = all(x[-1] == __import__('functools').reduce(lambda p, c: p ^ c, x[:-1], 0) for x in blk)
check('both blocks have good parity', par and len(blk) == 2, True)
check('SAVE reports nothing and is back at the prompt', rows()[-1], ']')

# ---- LOAD and VERIFY
b.line('NEW'); b.line('CLS'); b.line('LOAD "squares"')
check('LOAD prints the header it found', 'Program: squares' in rows(), True)
check('LOAD "squares" brings the program back', listing(), PROG)
b.line('CLS'); b.line('VERIFY "squares"'); check('VERIFY against the program in place', last(), 'Program: squares')
check('...and leaves no error', rows()[-1], ']')
b.line('NEW'); b.enter(['PRINT "changed"']); b.line('CLS'); b.line('VERIFY "squares"')
check('VERIFY a different program fails', last(), 'Tape: bad or missing block')
b.line('LOAD "squares"'); b.line('LOAD "squares"')
check('LOAD the same name twice (round the card again)', listing(), PROG)
b.line('CLS'); b.line('LOAD "nothere"'); check('LOAD a missing file', last(), 'Tape: bad or missing block')

# ---- CODE
for i in range(300): s.poke(40000 + i, (i * 7 + 3) & 255)
want = bytes(s.block(40000, 300))
b.line('SAVE "data" CODE 40000, 300')
for i in range(300): s.poke(40000 + i, 0); s.poke(50000 + i, 0)
b.line('LOAD "data" CODE 50000'); check('LOAD CODE to a new address', bytes(s.block(50000, 300)), want)
b.line('LOAD "data" CODE'); check('LOAD CODE to the address it was saved from', bytes(s.block(40000, 300)), want)
b.line('CLS'); b.line('VERIFY "data" CODE 50000'); check('VERIFY CODE', rows()[-1], ']')
s.poke(50100, s.peek(50100) ^ 1); b.line('CLS'); b.line('VERIFY "data" CODE 50000')
check('VERIFY CODE spots one changed byte', last(), 'Tape: bad or missing block')

# ---- CAT, names, LOAD ""
check('CAT lists the .tap files in name order', cat(), ['data', 'squares'])
open(os.path.join(d, 'readme.txt'), 'w').write('not a tape')
check('CAT leaves out other files', cat(), ['data', 'squares'])
b.line('SAVE "a/b:c" CODE 40000, 10'); check('characters a card can\'t hold become _', os.path.exists(os.path.join(d, 'a_b_c.tap')), True)
b.line('NEW'); b.line('CLS'); b.line('LOAD ""')
r = rows()
check('LOAD "": skips the CODE files, as a tape would, across files', [x for x in r if x.startswith(('Program', 'Bytes'))],
      ['Bytes: a/b:c', 'Bytes: data', 'Program: squares'])
check('...and loads the program', listing(), PROG)
card('empty'); check('CAT on an empty card', cat(), ['No files'])
b.line('CLS'); b.line('LOAD ""'); check('LOAD "" with no files', last(), 'Tape: bad or missing block')
s.lib.z_storage_dir(os.fsencode(os.path.join(TMP, 'missing')))
check('CAT with no card', cat(), ['No SD card'])
b.line('CLS'); b.line('SAVE "x"'); check('SAVE with no card', last(), 'Tape: bad or missing block')

# ---- the examples tape: one file of 13 blocks, found by file name or by block name
d = card('examples')
shutil.copy(os.path.join(HERE, '..', '..', 'examples', 'opticos_examples.tap'), os.path.join(d, 'OpticOS_examples.tap'))
b.line('NEW'); b.enter(['PRINT "a"']); b.line('SAVE "aaa"')           # another file, first in name order
def loaded(): return [r for r in listing() if r]
b.line('NEW'); b.line('LOAD "OpticOS_examples"')
check('LOAD by file name (first 10 characters): its first program', any('PROC menu' in r for r in loaded()), True)
b.line('NEW'); b.line('CLS'); b.line('LOAD "times"')
check('LOAD a program by its name, inside a file of many', 'Program: times' in rows() and rows()[-1] == ']', True)
b.line('NEW'); b.line('CLS'); b.line('LOAD "flag"'); b.line('CLS'); b.line('LOAD "tree"')
check('...and another after it (on along the file)', 'Program: tree' in rows() and rows()[-1] == ']', True)
b.line('CLS'); b.line('LOAD "guess"')
check('...and one before it (round from the first file again)', 'Program: guess' in rows() and rows()[-1] == ']', True)
for i in range(4): s.poke(60014 + i, 0)
b.line('CLEAR 59999'); b.line('LOAD "hbcode" CODE')
check('LOAD "hbcode" CODE: Happy Bat\'s machine code', bytes(s.block(60014, 2)), b'HB')
b.line('CLS'); b.line('LOAD "aaa"'); check('a one-program file still loads by name', listing(), ['PRINT "a"'])
b.line('CLS'); b.line('LOAD "nothere"'); check('a name on no file and in no file', last(), 'Tape: bad or missing block')

# ---- a program saved by the Spectrum ROM (decoded from its MIC signal) loads here
spec = subprocess.run([sys.executable, '-c', '''
import os, sys, json
os.environ.pop("OPTICOS_MACHINE", None)
sys.path.insert(0, %r)
from p3lib import Basic
from rig import decode_pulses
b = Basic(); b.enter(%r); s = b.s
s.mic_start(3); b.line('SAVE "spectrum"', 900_000_000)
print(json.dumps([list(x) for x in decode_pulses(s.mic_pulses())]))
''' % (HERE, PROG)], capture_output=True, text=True)
d = card('spectrum')
if spec.returncode: print(spec.stderr)
with open(os.path.join(d, 'spectrum.tap'), 'wb') as f:
    for x in (json.loads(spec.stdout) if spec.returncode == 0 else []):
        f.write(bytes([len(x) & 255, len(x) >> 8]) + bytes(x))
b.line('NEW'); b.line('LOAD "spectrum"')
check('a Spectrum ROM SAVE loads on the PicoCalc', listing(), PROG)
b.line('CLS'); b.line('RUN'); check('...and runs', rows()[1:4], ['1', '4', '9'])

shutil.rmtree(TMP)
print('%d failure(s)' % fails); sys.exit(1 if fails else 0)
