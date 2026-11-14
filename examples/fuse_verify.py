#!/usr/bin/env python3
"""Load every program on opticos_examples.tap in real Fuse (traps off, real
tape signal), run it and take a screenshot into shots/.  Run from the repo
root after ./build.sh and examples/mktape.py."""
import os, sys, time, subprocess
from PIL import Image, ImageChops
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(ROOT, 'tools')); sys.path.insert(0, os.path.join(ROOT, 'tools', 'rig'))
from fuse_phase1 import Fuse
from fuse_phase2 import type_line
# --traps: Fuse's defaults (tape traps, loader detection and acceleration),
# F8 not pressed; screenshots then go to build/shots_traps/.
TRAPS = '--traps' in sys.argv
sys.argv = [a for a in sys.argv if a != '--traps']
OUT = os.path.join(ROOT, 'build', 'shots_traps') if TRAPS else os.path.join(HERE, 'shots')
os.makedirs(OUT, exist_ok=True)
ROM = os.path.abspath(os.path.join(ROOT, 'build', 'opticos.rom'))
TAPE = os.path.join(HERE, 'opticos_examples.tap')
def settle(f, t_min=8, t_max=240):
    t0 = time.time(); last = None; still = 0
    while time.time() - t0 < t_max:
        time.sleep(2); f.shot('/tmp/_ex_poll.png')
        d = Image.open('/tmp/_ex_poll.png').convert('L')
        moved = last is None or sum(1 for v in ImageChops.difference(d, last).getdata() if v) > 300   # cursor flash < 300 px
        still = 0 if moved else still + 1; last = d
        if still >= 3 and time.time() - t0 > t_min: break
    return time.time() - t0
def title_up(f, t_max=240):
    """Happy Bat: wait for its title screen (blue playfield, the yellow
    "Press SPACE to start" on row 18); the screen never settles, it is animated"""
    t0 = time.time()
    while time.time() - t0 < t_max:
        time.sleep(1); f.shot('/tmp/_ex_poll.png')
        im = Image.open('/tmp/_ex_poll.png').convert('RGB').resize((320, 240), Image.NEAREST); w = im.load()
        if w[42, 124] == (0, 0, 255) and any(w[32 + x, 24 + y] == (255, 254, 0) for x in range(80, 200) for y in range(144, 152)):
            return time.time() - t0
    return None
RUNS = {'times': 3, 'guess': 3, 'fact': 3, 'sort': 4, 'errors': 3, 'ball': 4, 'tree': 32, 'colour': 6, 'flag': 22}
only = sys.argv[1:]
for name in ['examples'] + list(RUNS) + ['hilo', 'happybat']:
    if only and name not in only: continue
    subprocess.run(['pkill', '-f', 'fuse-sdl'])
    f = Fuse(ROM, TAPE, traps=TRAPS); time.sleep(3)
    type_line(f, 'LOAD ""' if name == 'examples' else 'LOAD "%s"' % name)
    if not TRAPS: f.key('F8')
    if name == 'happybat':
        # saved with AUTO start: it runs as soon as it has loaded, sets CLEAR
        # 59999 and loads its "hbcode" CODE block, the next one on the tape
        t = title_up(f); assert t is not None, 'happybat: no title screen'
        f.shot(os.path.join(OUT, 'happybat_loaded.png'))
        f.key('space', hold=0.1); t0 = time.time(); k = 0    # start
        while time.time() - t0 < 4.6:          # flap every 0.7 s: about level flight
            if time.time() - t0 > k * 0.7: f.key('space', hold=0.1); k += 1
            time.sleep(0.05)
        f.shot(os.path.join(OUT, 'happybat.png')); f.close()
        print(name, 'title after %.0f s' % t, flush=True); continue
    t = settle(f)
    f.shot(os.path.join(OUT, '%s_loaded.png' % name))
    if name in RUNS:
        type_line(f, 'CLS'); type_line(f, 'RUN'); time.sleep(RUNS[name])
    elif name == 'hilo':
        type_line(f, 'CLS'); type_line(f, 'RUN'); time.sleep(1)
        for g in ['50', 'lots', '25', '75', '12', '88', '37']: type_line(f, g); time.sleep(0.5)
    f.shot(os.path.join(OUT, '%s.png' % name)); f.close()
    print(name, 'loaded in %.0f s' % t, flush=True)
