#!/usr/bin/env python3
"""Phase 4 in real Fuse: enter a program with AUTO, LIST it (marker on the
current line), move the marker up with Caps+7, EDIT it (Caps+1) and change
it with the cursor keys; screenshot mid-edit.
Usage: fuse_phase4.py build/opticos.rom out_dir"""
import os, sys, time, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rig'))
from fuse_phase1 import Fuse
from fuse_phase2 import type_line
PROG = ['DEF stars(n)', 'LOCAL i', 'FOR i=1 TO n', 'PRINT "*";', 'NEXT', 'PRINT', 'ENDPROC',
        'FOR k=1 TO 5', 'stars k', 'NEXT']
def typ(f, text):
    type_line.__globals__  # same key mapping, no Return
    from rig import SYM
    for ch in text:
        if ch == ' ': f.key('space')
        elif ch in SYM: f.key(SYM[ch], mods=('Control_L',))
        elif ch.isupper(): f.key(ch.lower(), mods=('Shift_L',))
        else: f.key(ch)
if __name__ == '__main__':
    rom, out = os.path.abspath(sys.argv[1]), sys.argv[2]
    os.makedirs(out, exist_ok=True)
    subprocess.run(['pkill', '-f', 'fuse-sdl.*opticos'])
    f = Fuse(rom); time.sleep(3)
    type_line(f, 'AUTO')
    for l in PROG: type_line(f, l)
    type_line(f, '')
    type_line(f, 'LIST'); time.sleep(0.5)
    f.shot(os.path.join(out, 'fuse_list_marker.png'))
    for k in ['7', '7', '7', '7']: f.key(k, mods=('Shift_L',)); time.sleep(0.6)   # marker up to "PRINT"
    f.key('1', mods=('Shift_L',)); time.sleep(0.6)                           # EDIT
    typ(f, ' "-"'); time.sleep(0.5)                                         # PRINT -> PRINT "-"
    f.shot(os.path.join(out, 'fuse_edit.png'))
    f.key('Return'); time.sleep(0.8)
    type_line(f, 'RUN'); time.sleep(1)
    f.shot(os.path.join(out, 'fuse_after_edit.png')); f.close()
    print('saved', out)
