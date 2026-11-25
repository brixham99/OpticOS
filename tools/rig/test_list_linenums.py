#!/usr/bin/env python3
"""LIST shows leading line numbers in SCREEN 0 (64-col) and SCREEN 1 (32-col).

Mode 0 is the 48K rig. Mode 1 is a Fuse 128K run (32-col printer) decoded
with the 8x8 font.
"""
import os, sys, time, subprocess, tempfile
sys.path.insert(0, os.path.dirname(__file__))
from p3lib import Basic
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
FONT8 = os.path.join(ROOT, 'fonts', 'optic8x8.bin')
FUSE = os.path.join(ROOT, 'tools', 'fuse_screen128.py')

results = []
def check(name, ok, detail=''):
    results.append((name, bool(ok), detail))
    print('%-56s %s  %s' % (name, 'PASS' if ok else 'FAIL', detail))

def t_mode0():
    b = Basic()
    rows = b.run(['10 PRINT "Hello"', '20 PRINT "World"'], 'LIST')
    # run() drops the leading ']' and trailing blanks
    text = '\n'.join(rows)
    check('LIST shows line numbers in mode 0',
          '10 PRINT "Hello"' in text and '20 PRINT "World"' in text,
          repr(rows))

def decode32(im, font, scale=2, bx=64, by=48):
    glyphs = {c: font[8*(c-32):8*(c-32)+8] for c in range(32, 128)}
    inv = {bytes(g): chr(c) for c, g in glyphs.items()}
    inv[bytes(8)] = ' '
    rows = []
    for r in range(24):
        s = []
        for c in range(32):
            raw = bytearray(8)
            for yy in range(8):
                byte = 0
                for xx in range(8):
                    px = bx + (c*8+xx)*scale + scale//2
                    py = by + (r*8+yy)*scale + scale//2
                    if sum(im.getpixel((px, py))[:3]) > 160:
                        byte |= 0x80 >> xx
                raw[yy] = byte
            s.append(inv.get(bytes(raw), '?'))
        rows.append(''.join(s).rstrip())
    return rows

def t_mode1():
    font = open(FONT8, 'rb').read()
    here = tempfile.mkdtemp(prefix='listnums-')
    sys.path.insert(0, os.path.join(ROOT, 'tools', 'rig'))
    from p3lib import Basic
    from rig import decode_pulses
    import struct
    b = Basic(); s = b.s
    prog = ['10 PRINT "Hello, 32-column mode"',
            '20 PRINT "abcdefghij0123456789XY"',
            '30 PRINT "Printed in SCREEN 1"']
    b.line('NEW'); b.enter(prog); s.mic_start(3)
    b.line('SAVE "mode1txt"', 2_000_000_000)
    got = decode_pulses(s.mic_pulses()); assert len(got) == 2, len(got)
    blocks = [bytes(x) for x in got]
    tape = os.path.join(here, 'mode1txt.tap')
    open(tape, 'wb').write(b''.join(struct.pack('<H', len(x)) + x for x in blocks))
    out = os.path.join(here, 'shots')
    os.makedirs(out, exist_ok=True)
    env = os.environ.copy()
    # fuse_screen128 uses fuse_phase1.ENV / DISPLAY
    proc = subprocess.run(
        ['python3', FUSE, out, os.path.abspath(tape)],
        input='>load ""\n!F8\n=8\n>screen 1\n=1\n>list\n=2\n@list_nums\n',
        text=True, cwd=ROOT, capture_output=True, timeout=120)
    shot = os.path.join(out, 'list_nums.png')
    if proc.returncode != 0 or not os.path.exists(shot):
        check('LIST shows line numbers in mode 1', False,
              'fuse failed rc=%s out=%r err=%r' % (proc.returncode, proc.stdout, proc.stderr[-1000:]))
        return shot
    rows = decode32(Image.open(shot), font)
    text = '\n'.join(rows)
    # Line 20 is 33 characters, so the closing quote wraps in 32-col mode.
    ok = ('10 PRINT "Hello, 32-column mode"' in rows
          and any(r.startswith('20 PRINT "abcdefghij0123456789XY') for r in rows)
          and '30 PRINT "Printed in SCREEN 1"' in rows)
    check('LIST shows line numbers in mode 1', ok, text)
    return shot

def main():
    t_mode0()
    t_mode1()
    nfail = sum(1 for _, ok, _ in results if not ok)
    print('\n%d tests, %d failed' % (len(results), nfail))
    return 0 if nfail == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
