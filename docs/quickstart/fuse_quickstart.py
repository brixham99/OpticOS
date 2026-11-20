#!/usr/bin/env python3
"""Type the QuickStart's OpticBASIC snippets into real Fuse (OpticOS ROM,
build/opticos.rom) exactly as printed on page 2, and take the screenshots:
the start-up screen (cover), the prompt commands, and the AUTO program's RUN
and LIST. Usage: python3 docs/quickstart/fuse_quickstart.py (after ./build.sh)"""
import os, sys, time, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..', '..')
sys.path.insert(0, os.path.join(ROOT, 'tools')); sys.path.insert(0, os.path.join(ROOT, 'tools', 'rig'))
from fuse_phase1 import Fuse
from fuse_phase2 import type_line
OUT = os.path.join(HERE, 'img'); os.makedirs(OUT, exist_ok=True)
PROMPT = ['PRINT "Hello from OpticOS!"', 'PRINT 2 + 2', 'BORDER 1: PAPER 6: INK 1: CLS', 'PRINT "Blue on yellow"', 'BEEP 0.5, 7']
PROG = ['FOR i = 1 TO 5', 'PRINT INK i; "OpticOS "; i', 'BEEP 0.1, i * 2', 'NEXT']
subprocess.run(['pkill', '-f', 'fuse-sdl.*opticos'])
f = Fuse(os.path.abspath(os.path.join(ROOT, 'build/opticos.rom'))); time.sleep(4.5)   # boot, chime and key swallow
f.shot(os.path.join(OUT, 'boot.png'))
for l in PROMPT[:2]: type_line(f, l)
time.sleep(0.5); f.shot(os.path.join(OUT, 'try_print.png'))
for l in PROMPT[2:]: type_line(f, l)
time.sleep(1); f.shot(os.path.join(OUT, 'try_colour.png'))
type_line(f, 'AUTO')
for l in PROG: type_line(f, l)
type_line(f, '')
type_line(f, 'RUN'); time.sleep(2); f.shot(os.path.join(OUT, 'prog_run.png'))
type_line(f, 'LIST'); time.sleep(1); f.shot(os.path.join(OUT, 'prog_list.png'))
type_line(f, 'NEW'); time.sleep(4.5); f.shot(os.path.join(OUT, 'after_new.png'))
f.close(); print('saved', OUT)
