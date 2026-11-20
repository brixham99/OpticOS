#!/usr/bin/env python3
"""Check the Fuse-on-the-Mac booklet's tape advice in real Fuse (the Unix
build on the test box, same emulation core): OpticOS ROM as the 48K ROM,
Fuse's default tape settings (tape traps, loader detection, loader
acceleration and fast loading on) and auto-load either ON (File > Open's
phantom typist) or OFF. In every case the user then types LOAD "" at the
] prompt. Usage: python3 docs/quickstart/fuse-mac/fuse_mac_test.py"""
import os, sys, time, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..', '..', '..')
sys.path.insert(0, os.path.join(ROOT, 'tools')); sys.path.insert(0, os.path.join(ROOT, 'tools', 'rig'))
import fuse_phase1
from fuse_phase1 import Fuse, ENV, DATA, x, ensure_x
from fuse_phase2 import type_line
ROM = os.path.abspath(os.path.join(ROOT, 'build/opticos.rom'))
OUT = os.path.join(HERE, 'img'); os.makedirs(OUT, exist_ok=True)
def launch(tape, autoload):
    ensure_x()
    f = Fuse.__new__(Fuse)
    args = ['fuse-sdl', '--machine', '48', '--rom-48', ROM,
            '--auto-load' if autoload else '--no-auto-load',
            '--traps', '--detect-loader', '--accelerate-loader', '--fastload',
            '--no-sound', '--no-confirm-actions', '--no-statusbar', '--graphics-filter', 'normal', '--tape', tape]
    f.p = subprocess.Popen(args, env=ENV, cwd=DATA, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    for _ in range(50):
        time.sleep(0.2)
        w = x('xdotool', 'search', '--pid', str(f.p.pid)).split()
        if w: f.win = w[-1]; break
    time.sleep(1)
    g = dict(l.split('=') for l in x('xdotool', 'getwindowgeometry', '--shell', f.win).split())
    f.geo = int(g['X']), int(g['Y']), int(g['WIDTH']), int(g['HEIGHT'])
    x('xdotool', 'windowfocus', '--sync', f.win); x('xdotool', 'mousemove', '0', '0')
    return f
CASES = [('examples_tzx_autoload', 'examples/opticos_examples.tzx', True, 6),
         ('examples_tap_autoload', 'examples/opticos_examples.tap', True, 6),
         ('dino_tzx_noauto', '/workspace/dino-opticos/dino.tzx', False, 10),
         ('happybat_tap_noauto', '/workspace/happybat/happybat.tap', False, 8)]
if __name__ == '__main__':
    only = sys.argv[1:]
    for name, tape, auto, wait in CASES:
        if only and name not in only: continue
        subprocess.run(['pkill', '-f', 'fuse-sdl.*opticos'])
        tape = tape if tape.startswith('/') else os.path.join(ROOT, tape)
        f = launch(os.path.abspath(tape), auto); time.sleep(5)
        f.shot(os.path.join(OUT, name + '_prompt.png'))      # expect a clean ] prompt, nothing loaded yet
        type_line(f, 'LOAD ""'); time.sleep(wait)
        f.shot(os.path.join(OUT, name + '_loaded.png'))
        f.close(); print(name, 'done')
