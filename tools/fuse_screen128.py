#!/usr/bin/env python3
"""Fuse 128K test for the screen-mode extension ROM: OpticOS in ROM slot 0,
build/opticos128ext.rom in slot 1.  Types OpticBASIC lines and takes screenshots.
Usage: fuse_screen128.py OUTDIR [tape]   (lines from stdin: '>text' type+ENTER, '=secs' wait, '@name' shot)"""
import os, sys, time, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from fuse_phase1 import ENV, DATA, x, ensure_x, Fuse, DISP
from fuse_phase2 import SYM
def keys(f, text):
    for ch in text:
        if ch == ' ': f.key('space')
        elif ch in SYM: f.key(SYM[ch], mods=('Control_L',))
        elif ch.isupper(): f.key(ch.lower(), mods=('Shift_L',))
        else: f.key(ch)
def launch(tape=None):
    ensure_x(); f = Fuse.__new__(Fuse)
    args = ['fuse-sdl', '--machine', '128', '--rom-128-0', os.path.join(ROOT, 'build', 'opticos.rom'),
            '--rom-128-1', os.path.join(ROOT, 'build', 'opticos128ext.rom'), '--no-auto-load', '--no-traps', '--no-detect-loader', '--no-accelerate-loader', '--fastload',
            '--no-sound', '--no-confirm-actions', '--no-statusbar', '--graphics-filter', 'normal']
    if tape: args += ['--tape', tape]
    f.p = subprocess.Popen(args, env=ENV, cwd=DATA, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    for _ in range(50):
        time.sleep(0.2); w = x('xdotool', 'search', '--pid', str(f.p.pid)).split()
        if w: f.win = w[-1]; break
    time.sleep(1)
    g = dict(l.split('=') for l in x('xdotool', 'getwindowgeometry', '--shell', f.win).split())
    f.geo = int(g['X']), int(g['Y']), int(g['WIDTH']), int(g['HEIGHT'])
    x('xdotool', 'windowfocus', f.win); x('xdotool', 'mousemove', '0', '0')
    return f
if __name__ == '__main__':
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    subprocess.run(['pkill', '-x', 'fuse-sdl'])
    f = launch(sys.argv[2] if len(sys.argv) > 2 else None); time.sleep(4.5)
    for line in sys.stdin.read().splitlines():
        if line.startswith('>'): keys(f, line[1:]); f.key('Return')
        elif line.startswith('='): time.sleep(float(line[1:]))
        elif line.startswith('@'): f.shot(os.path.join(out, line[1:] + '.png')); print('shot', line[1:], flush=True)
        elif line.startswith('!'): f.key(line[1:])
    f.close()
