#!/usr/bin/env python3
"""Phase 2 in real Fuse: type PRINT lines at the ] prompt and screenshot.
Usage: fuse_phase2.py build/opticos.rom out_dir
Keys go in as a Spectrum keyboard would send them: Caps Shift = Shift_L,
Symbol Shift = Control_L (so " is Symbol+P, ; is Symbol+O)."""
import os, sys, time, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rig'))
from fuse_phase1 import Fuse
from rig import SYM
LINES = ['PRINT "Hello, World!"', 'PRINT 2+2, SQR 2, "Hi";"!"', '? 1/3, PI*2, 2^10, EXP 1',
         '? SIN(PI/6);" ";ATN 1*4;" ";1E-5;" ";1E10', '? 1/0']
def type_line(f, text):
    for ch in text:
        if ch == ' ': f.key('space')
        elif ch in SYM: f.key(SYM[ch], mods=('Control_L',))
        elif ch.isupper(): f.key(ch.lower(), mods=('Shift_L',))
        else: f.key(ch)
    f.key('Return'); time.sleep(0.6)
if __name__ == '__main__':
    rom, out = os.path.abspath(sys.argv[1]), sys.argv[2]
    os.makedirs(out, exist_ok=True)
    subprocess.run(['pkill', '-f', 'fuse-sdl.*opticos'])
    f = Fuse(rom); time.sleep(3)
    for l in LINES: type_line(f, l)
    time.sleep(0.5)
    f.shot(os.path.join(out, 'fuse_hello.png')); f.close()
    print('saved', os.path.join(out, 'fuse_hello.png'))
