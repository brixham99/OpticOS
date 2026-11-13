#!/usr/bin/env python3
"""Phase 3 in real Fuse: type a structured program (">" lines), LIST and
RUN it, and screenshot.  Usage: fuse_phase3.py build/opticos.rom out_dir"""
import os, sys, time, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rig'))
from fuse_phase1 import Fuse
from fuse_phase2 import type_line
PROG = ['DEF fib(n)', 'IF n<2 THEN RETURN n', 'RETURN fib(n-1)+fib(n-2)', 'ENDFN',
        'DEF show(n)', 'LOCAL i', 'FOR i=1 TO n', 'PRINT "fib(";i;") = ";fib(i)', 'NEXT', 'ENDPROC',
        'TRY', 'show 5: PRINT 1/0', 'CATCH', 'PRINT "Caught error ";ERR', 'ENDTRY']
if __name__ == '__main__':
    rom, out = os.path.abspath(sys.argv[1]), sys.argv[2]
    os.makedirs(out, exist_ok=True)
    subprocess.run(['pkill', '-f', 'fuse-sdl.*opticos'])
    f = Fuse(rom); time.sleep(3)
    for l in PROG: type_line(f, '>' + l)
    for l in ['CLS', 'LIST', 'RUN']: type_line(f, l); time.sleep(0.5)
    time.sleep(1)
    p = os.path.join(out, 'fuse_program.png'); f.shot(p); f.close()
    print('saved', p)
