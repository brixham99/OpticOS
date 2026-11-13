#!/usr/bin/env python3
"""Build examples/opticos_examples.tap and .tzx.  Each program in src/ is
typed into the ROM in the test rig and saved there with OpticOS's own SAVE;
the recorded MIC signal is decoded back into blocks, so the tape holds
exactly what the ROM writes (type-0 "Program:" header, data starting with
the "OB" $01 $00 signature).  Run from the repo root after ./build.sh."""
import os, sys, struct
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools', 'rig'))
from p3lib import Basic
from rig import decode_pulses
ORDER = [('menu', 'examples', 'menu'), ('times', 'times', None), ('guess', 'guess', None), ('fact', 'fact', None),
         ('sort', 'sort', None), ('errors', 'errors', None), ('ball', 'ball', None), ('tree', 'tree', None),
         ('colour', 'colour', None), ('hilo', 'hilo', None), ('flag', 'flag', None)]
b = Basic(); s = b.s
blocks = []
for src, name, auto in ORDER:
    prog = [l.strip() for l in open(os.path.join(HERE, 'src', src + '.bas')) if l.strip()]
    b.line('NEW'); b.enter(prog)
    s.mic_start(3)
    b.line('SAVE "%s"%s' % (name, ' AUTO ' + auto if auto else ''), 2_000_000_000)
    got = decode_pulses(s.mic_pulses())
    assert len(got) == 2, (name, len(got))
    hdr, data = got
    assert hdr[0] == 0 and hdr[1] == 0 and len(hdr) == 19, name           # flag 0, type 0 (Program:)
    assert hdr[2:12].decode().rstrip() == name, hdr[2:12]
    assert data[0] == 0xFF and bytes(data[1:5]) == b'OB\x01\x00', name     # OpticBASIC signature
    for blk in got:
        p = 0
        for x in blk[:-1]: p ^= x
        assert p == blk[-1], name                                          # parity
    length = hdr[12] | hdr[13] << 8; p1 = hdr[14] | hdr[15] << 8
    print('%-9s %5d bytes  %s' % (name, length, 'auto-runs PROC %s' % auto if p1 < 0x8000 else ''))
    blocks += [bytes(hdr), bytes(data)]
tap = b''.join(struct.pack('<H', len(x)) + x for x in blocks)
open(os.path.join(HERE, 'opticos_examples.tap'), 'wb').write(tap)
tzx = b'ZXTape!\x1a\x01\x14' + b''.join(b'\x10' + struct.pack('<HH', 1000, len(x)) + x for x in blocks)
open(os.path.join(HERE, 'opticos_examples.tzx'), 'wb').write(tzx)
print('wrote opticos_examples.tap (%d bytes) and .tzx (%d bytes), %d programs' % (len(tap), len(tzx), len(blocks) // 2))
