#!/usr/bin/env python3
"""Build examples/udg128.tap and .tzx from src/udg128.bas (no line numbers)."""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools', 'rig'))
from p3lib import Basic
from rig import decode_pulses
b = Basic(); s = b.s
prog = [l.strip() for l in open(os.path.join(HERE, 'src', 'udg128.bas')) if l.strip()]
b.line('NEW'); b.enter(prog); s.mic_start(3)
b.line('SAVE "udg128"', 2_000_000_000)
got = decode_pulses(s.mic_pulses()); assert len(got) == 2, len(got)
blocks = [bytes(x) for x in got]
assert blocks[1][1:5] == b'OB\x01\x00'
open(os.path.join(HERE, 'udg128.tap'), 'wb').write(b''.join(struct.pack('<H', len(x)) + x for x in blocks))
open(os.path.join(HERE, 'udg128.tzx'), 'wb').write(b'ZXTape!\x1a\x01\x14' + b''.join(b'\x10' + struct.pack('<HH', 1000, len(x)) + x for x in blocks))
print('udg128: %d bytes of program' % (blocks[0][12] | blocks[0][13] << 8))
