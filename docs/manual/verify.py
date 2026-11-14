#!/usr/bin/env python3
"""Run each example in docs/manual/examples in the rig and print the screen text.
hbloader.bas runs before happybat.bas: it POKEs Happy Bat's machine code to
60000 (and SAVEs it), so the game finds its code in memory and does not wait
for the tape (NEW wipes memory, so the verifier puts the code back as
LOAD "hbcode" CODE would).  The game never stops by itself, so it is run for 3 seconds,
its title screen printed, and then stopped with BREAK."""
import os, sys, glob
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools', 'rig'))
from p3lib import Basic, SYM, LINEBUF, CON_LEN
b = Basic(); s = b.s
files = sorted(glob.glob(os.path.join(HERE, 'examples', '*.bas')))
names = [os.path.basename(f) for f in files]
if 'hbloader.bas' in names and 'happybat.bas' in names:      # the loader first
    files.insert(names.index('happybat.bas'), files.pop(names.index('hbloader.bas')))
for f in files:
    prog = [l.strip() for l in open(f) if l.strip()]
    print('=====', os.path.basename(f))
    if os.path.basename(f) == 'happybat.bas':
        # NEW is a full restart and wipes the code, so put the 1,095 bytes back
        # as LOAD "hbcode" CODE would; the game then finds "HB" at 60014
        code = s.block(60000, 1095); b.line('NEW'); s.load(60000, bytes(code))
        b.enter(prog); b.cls()
        assert s.run_until(SYM['cg_lp'], 20_000_000)
        s.load(LINEBUF, b'RUN'); s.poke(CON_LEN, 3)
        s.setregs(PC=SYM['con_enter'], SP=s.regs()['SP'] + 2)
        s.frame(150)
        for r in b.screen():             # graphics (the bat, the ground) print as #
            if r: print('|' + ''.join(c if ' ' <= c < '\x7f' else '#' for c in r))
        print('--- in memory: RAMTOP %d, code signature %s' % (s.peek(23730) | s.peek(23731) << 8, bytes([s.peek(60014), s.peek(60015)])))
        s.key('^'); s.key(' '); s.frame(20); s.key(' ', False); s.key('^', False); s.frame(20)
        print('--- BREAK:', [r for r in b.screen() if 'Break' in r])
    else:
        for r in b.run(prog, limit=3_000_000_000): print('|' + r)
    b.line('LIST'); print('--- LIST'); [print('|' + r) for r in b.screen() if r]
