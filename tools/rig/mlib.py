"""OpticOS maths in the rig: 5-byte encode/decode and routine calls.

The ROM is run headless; numbers are passed through scratch RAM at $6000.
Errors (RST 8) come back to the sentinel through ERR_SP; err is ERR_NR."""
import os, re, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import Spectrum, lib
import mpmath as mp
mp.mp.prec = 200
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
ROM = os.path.join(ROOT, 'build/opticos.rom')
SYM = {}
for line in open(os.path.join(ROOT, 'build/opticos.sym')):
    m = re.match(r'(\w+)\s+EQU\s+0?([0-9A-F]+)H', line)
    if m: SYM[m.group(1).lower()] = int(m.group(2), 16)
A, B, TXT = 0x6000, 0x6008, 0x6100
ERRW = 0x5FF8

def encode(x):
    """Exact float / mpf / int -> 5 bytes, rounding to nearest (ties away)."""
    x = mp.mpf(x)
    if x == int(x) and abs(x) <= 65535:
        v = int(x) & 0x1FFFF
        return bytes([0, 0xFF if x < 0 else 0, v & 255, (v >> 8) & 255, 0])
    s = 0x80 if x < 0 else 0
    m, e = mp.frexp(abs(x))          # m in [0.5,1)
    mi = int(mp.floor(m * 2**32 + mp.mpf(0.5)))
    if mi == 2**32: mi >>= 1; e += 1
    e += 128
    if not 1 <= e <= 255: raise OverflowError
    return bytes([e, ((mi >> 24) & 0x7F) | s, (mi >> 16) & 255, (mi >> 8) & 255, mi & 255])

def decode(b):
    b = bytes(b)
    if b[0] == 0:
        v = b[2] | b[3] << 8
        if b[1] == 0xFF: v -= 65536
        elif b[1] != 0: raise ValueError('bad int form %r' % b)
        return mp.mpf(v)
    mi = (b[1] | 0x80) << 24 | b[2] << 16 | b[3] << 8 | b[4]
    v = mp.ldexp(mp.mpf(mi), b[0] - 128 - 32)
    return -v if b[1] & 0x80 else v

def ulp(x):
    """Ulp of the 32-bit mantissa float at x (int form counts as float)."""
    x = mp.mpf(x)
    if x == 0: return mp.ldexp(1, -128 - 32)
    m, e = mp.frexp(abs(x)); return mp.ldexp(1, e - 32)

class M:
    def __init__(self):
        self.s = Spectrum(ROM)
        self.s.frame(80)                       # boot to the prompt
        self.s.poke(ERRW, 0xF0); self.s.poke(ERRW + 1, 0x5F)
    def run(self, name, limit=20_000_000, **regs):
        s = self.s
        s.poke(SYM['err_nr'], 0xFF)
        s.poke(SYM['err_sp'], ERRW & 255); s.poke(SYM['err_sp'] + 1, ERRW >> 8)
        t0 = lib.z_tstates()
        r = s.call(SYM[name], SP=0x5FE0, IY=0x5C3A, limit=limit, **regs)
        t = lib.z_tstates() - t0
        e = s.peek(SYM['err_nr'])
        return r, (None if e == 0xFF else e), t
    def bin(self, name, x, y, raw=False):
        self.s.load(A, x if raw else encode(x)); self.s.load(B, y if raw else encode(y))
        r, e, t = self.run(name, HL=A, DE=B)
        return self.s.block(A, 5), e, t
    def un(self, name, x, raw=False):
        self.s.load(A, x if raw else encode(x))
        r, e, t = self.run(name, HL=A)
        return self.s.block(A, 5), e, t
