#!/usr/bin/env python3
"""Type the manual's examples into real Fuse (traps off) and take screenshots.
Usage: python3 docs/manual/fuse_shots.py   (from the repo root, after ./build.sh)"""
import os, sys, time, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..')
sys.path.insert(0, os.path.join(ROOT, 'tools')); sys.path.insert(0, os.path.join(ROOT, 'tools', 'rig'))
from fuse_phase1 import Fuse
from fuse_phase2 import type_line
OUT = os.path.join(HERE, 'img'); os.makedirs(OUT, exist_ok=True)
def prog(name): return [l.strip() for l in open(os.path.join(HERE, 'examples', name)) if l.strip()]
def enter(f, lines):
    type_line(f, 'NEW'); type_line(f, 'AUTO')
    for l in lines: type_line(f, l)
    type_line(f, '')
subprocess.run(['pkill', '-f', 'fuse-sdl.*opticos'])
f = Fuse(os.path.abspath(os.path.join(ROOT, 'build/opticos.rom'))); time.sleep(3)
f.shot(os.path.join(OUT, 'boot.png'))
enter(f, prog('guess.bas'))
type_line(f, 'CLS'); type_line(f, 'LIST'); time.sleep(1); f.shot(os.path.join(OUT, 'list_guess.png'))
type_line(f, 'CLS'); type_line(f, 'RUN'); time.sleep(1)
type_line(f, 'PRINT 1/0'); time.sleep(1); f.shot(os.path.join(OUT, 'run_guess.png'))
enter(f, prog('errors.bas'))
type_line(f, 'CLS'); type_line(f, 'RUN'); time.sleep(1); f.shot(os.path.join(OUT, 'run_errors.png'))
enter(f, prog('sort.bas'))
type_line(f, 'CLS'); type_line(f, 'RUN'); time.sleep(1)
type_line(f, 'PRINT FREE;" bytes free"'); time.sleep(1); f.shot(os.path.join(OUT, 'run_sort.png'))
enter(f, prog('ball.bas'))
type_line(f, 'RUN'); time.sleep(3); f.shot(os.path.join(OUT, 'run_ball.png'))
f.key('space', hold=0.5); time.sleep(1)
enter(f, prog('tree.bas'))
type_line(f, 'RUN'); time.sleep(32); f.shot(os.path.join(OUT, 'run_tree.png'))
f.close(); print('saved', OUT)
