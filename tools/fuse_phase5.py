#!/usr/bin/env python3
"""Phase 5 in real Fuse: a program with INPUT and DATA / READ, typed with
AUTO, listed and run (screenshot after answering the INPUT); then a
graphics demo with PLOT, DRAW, colours and BEEP.
Usage: fuse_phase5.py build/opticos.rom out_dir"""
import os, sys, time, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rig'))
from fuse_phase1 import Fuse
from fuse_phase2 import type_line
PROG = ['INPUT "Your name? ";n$', 'PRINT "Hello, ";n$;". Today:"', 'FOR i=1 TO 3', 'READ w$, k',
        'PRINT k;" ";w$', 'NEXT', 'DATA "apples", 4, "pears", 2', 'DATA "plums", 3*4']
GFX = ['BORDER 0: PAPER 0: INK 7: CLS', 'FOR i=0 TO 120 STEP 6', 'INK 1+(i/6) MOD 7', 'PLOT 128,96',
       'DRAW TO i*2,0', 'PLOT 128,96', 'DRAW TO 255-i*2,191', 'NEXT', 'INK 6: PLOT 0,0: DRAW 255,0: DRAW 0,191',
       'DRAW -255,0: DRAW 0,-191', 'PRINT AT 11,20; INK 7; PAPER 1; BRIGHT 1;" OpticOS: PLOT, DRAW, INK "',
       'BEEP 0.2,0: BEEP 0.2,4: BEEP 0.4,7']
if __name__ == '__main__':
    rom, out = os.path.abspath(sys.argv[1]), sys.argv[2]
    os.makedirs(out, exist_ok=True)
    subprocess.run(['pkill', '-f', 'fuse-sdl.*opticos'])
    f = Fuse(rom); time.sleep(3)
    type_line(f, 'AUTO')
    for l in PROG: type_line(f, l)
    type_line(f, '')
    type_line(f, 'CLS'); type_line(f, 'LIST'); type_line(f, 'RUN'); time.sleep(0.8)
    type_line(f, 'Nathan'); time.sleep(1)
    f.shot(os.path.join(out, 'fuse_input_read.png'))
    type_line(f, 'NEW'); type_line(f, 'AUTO')
    for l in GFX: type_line(f, l)
    type_line(f, ''); type_line(f, 'RUN'); time.sleep(4)
    f.shot(os.path.join(out, 'fuse_graphics.png')); f.close()
    print('saved', out)
