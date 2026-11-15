#!/usr/bin/env python3
"""Build examples/picocalc/happybatpc.tap: Happy Bat for the PicoCalc.

happybat_pc.asm is assembled with pasmo; happybat_pc.bas is typed into the
PicoCalc ROM in the test rig and saved there with OpticOS's own SAVE (the
rig's storage device writes it to a scratch card); then the code is put at
60000 and saved with SAVE "hbcodepc" CODE.  The two files are joined into
one, program first, so LOAD "happybatpc" runs the game, and the game's own
LOAD "hbcodepc" CODE finds the code right after it.  Run from the repo root
after building the ROMs (make), with pasmo installed (the Docker image)."""
import os, sys, shutil, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ['OPTICOS_MACHINE'] = 'picocalc'
sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools', 'rig'))
from p3lib import Basic
from rig import tap_blocks

def assemble():
    """happybat_pc.asm -> (code bytes, symbols)"""
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(['pasmo', '--bin', os.path.join(HERE, 'happybat_pc.asm'), os.path.join(d, 'hb.bin'),
                        os.path.join(d, 'hb.sym')], check=True)
        sym = {}
        for l in open(os.path.join(d, 'hb.sym')):
            p = l.split()
            if len(p) == 3 and p[1] == 'EQU': sym[p[0]] = int(p[2].rstrip('H'), 16)
        return open(os.path.join(d, 'hb.bin'), 'rb').read(), sym

def main():
    code, _ = assemble()
    prog = [l.strip() for l in open(os.path.join(HERE, 'happybat_pc.bas')) if l.strip()]
    card = tempfile.mkdtemp(prefix='hbpc_')
    b = Basic(); s = b.s; s.sd(card)
    b.line('NEW'); b.enter(prog)
    b.line('SAVE "happybatpc" AUTO start')
    b.line('CLEAR 59999')                     # (the stacks lie below RAMTOP, over 60000)
    s.load(60000, code)
    b.line('SAVE "hbcodepc" CODE 60000, %d' % len(code))
    blocks = tap_blocks(os.path.join(card, 'happybatpc.tap')) + tap_blocks(os.path.join(card, 'hbcodepc.tap'))
    assert [len(x) for x in blocks[::2]] == [19, 19] and [x[0] for x in blocks] == [0, 255, 0, 255], 'blocks'
    assert blocks[0][2:12] == b'happybatpc' and blocks[0][1] == 0 and blocks[1][1:5] == b'OB\x01\x00', 'program'
    assert blocks[2][2:12] == b'hbcodepc  ' and blocks[2][1] == 3, 'code header'
    assert blocks[2][14] | blocks[2][15] << 8 == 60000 and bytes(blocks[3][1:-1]) == code, 'code'
    for x in blocks:
        p = 0
        for c in x[:-1]: p ^= c
        assert p == x[-1], 'parity'
    out = os.path.join(HERE, 'happybatpc.tap')
    with open(out, 'wb') as f:
        for x in blocks: f.write(bytes([len(x) & 255, len(x) >> 8]) + bytes(x))
    shutil.rmtree(card)
    print('happybatpc %5d bytes  auto-runs PROC start' % (len(blocks[1]) - 2))
    print('hbcodepc   %5d bytes  CODE 60000,%d' % (len(code), len(code)))
    print('wrote %s (%d bytes)' % (os.path.relpath(out), os.path.getsize(out)))

if __name__ == '__main__': main()
