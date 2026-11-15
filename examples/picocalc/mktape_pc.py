#!/usr/bin/env python3
"""Build examples/picocalc/picocalc_examples.tap: the example programs for
OpticOS on the PicoCalc (40 x 40 text, 320 x 320 pixels).

Each program is typed into the PicoCalc ROM in the test rig and saved there
with OpticOS's own SAVE (the rig's storage device writes it to a scratch
card), the way examples/mktape.py makes the Spectrum tape.  A program comes
from src/ here when it has a PicoCalc version (the menu, ball, tree,
colour, hilo, flag and Happy Bat), otherwise from ../src (the Spectrum
version, which fits 40 columns as it is).  Happy Bat's machine code
(src/happybat_pc.asm) is assembled with pasmo, put at 60000 and saved as
"hbcodepc" CODE, right after the game.  Run from the repo root after
building the ROMs (make), with pasmo installed (the Docker image)."""
import os, sys, shutil, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ['OPTICOS_MACHINE'] = 'picocalc'
sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools', 'rig'))
from p3lib import Basic
from rig import tap_blocks

TAPE = os.path.join(HERE, 'picocalc_examples.tap')
# (source, name, AUTO proc); the code block comes last
ORDER = [('menu', 'examples', 'menu'), ('times', 'times', None), ('guess', 'guess', None), ('fact', 'fact', None),
         ('sort', 'sort', None), ('errors', 'errors', None), ('ball', 'ball', None), ('tree', 'tree', None),
         ('colour', 'colour', None), ('hilo', 'hilo', None), ('flag', 'flag', None),
         ('happybatpc', 'happybatpc', 'start')]

def source(name):
    """the PicoCalc version if there is one, else the Spectrum version"""
    pc = os.path.join(HERE, 'src', name + '.bas')
    return pc if os.path.exists(pc) else os.path.join(HERE, '..', 'src', name + '.bas')

def assemble():
    """src/happybat_pc.asm -> (code bytes, symbols)"""
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(['pasmo', '--bin', os.path.join(HERE, 'src', 'happybat_pc.asm'), os.path.join(d, 'hb.bin'),
                        os.path.join(d, 'hb.sym')], check=True)
        sym = {}
        for l in open(os.path.join(d, 'hb.sym')):
            p = l.split()
            if len(p) == 3 and p[1] == 'EQU': sym[p[0]] = int(p[2].rstrip('H'), 16)
        return open(os.path.join(d, 'hb.bin'), 'rb').read(), sym

def check(hdr, data, name, code=None):
    assert len(hdr) == 19 and hdr[0] == 0 and hdr[2:12].decode().rstrip() == name, (name, bytes(hdr))
    if code is None:
        assert hdr[1] == 0 and data[0] == 0xFF and bytes(data[1:5]) == b'OB\x01\x00', name   # Program:, signature
    else:
        assert hdr[1] == 3 and hdr[14] | hdr[15] << 8 == 60000 and bytes(data[1:-1]) == code, name
    for x in (hdr, data):
        p = 0
        for c in x[:-1]: p ^= c
        assert p == x[-1], name                                                         # parity

def main():
    code, _ = assemble()
    card = tempfile.mkdtemp(prefix='pcex_')
    b = Basic(); s = b.s; s.sd(card)
    blocks = []
    for src, name, auto in ORDER:
        prog = [l.strip() for l in open(source(src)) if l.strip()]
        b.line('NEW'); b.enter(prog)
        b.line('SAVE "%s"%s' % (name, ' AUTO ' + auto if auto else ''), 2_000_000_000)
        hdr, data = tap_blocks(os.path.join(card, name + '.tap'))
        check(hdr, data, name)
        p1 = hdr[14] | hdr[15] << 8
        print('%-10s %5d bytes  %s%s' % (name, len(data) - 2, 'auto-runs PROC %s' % auto if p1 < 0x8000 else '',
                                          '' if os.path.exists(os.path.join(HERE, 'src', src + '.bas')) else '(the Spectrum version)'))
        blocks += [hdr, data]
    b.line('NEW'); b.line('CLEAR 59999')          # (the stacks lie below RAMTOP, over 60000)
    s.load(60000, code)
    b.line('SAVE "hbcodepc" CODE 60000, %d' % len(code))
    hdr, data = tap_blocks(os.path.join(card, 'hbcodepc.tap'))
    check(hdr, data, 'hbcodepc', code)
    print('%-10s %5d bytes  CODE 60000,%d (src/happybat_pc.asm)' % ('hbcodepc', len(code), len(code)))
    blocks += [hdr, data]
    with open(TAPE, 'wb') as f:
        for x in blocks: f.write(bytes([len(x) & 255, len(x) >> 8]) + bytes(x))
    shutil.rmtree(card)
    print('wrote %s (%d bytes), %d files' % (os.path.relpath(TAPE), os.path.getsize(TAPE), len(blocks) // 2))

if __name__ == '__main__': main()
