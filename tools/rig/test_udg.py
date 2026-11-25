#!/usr/bin/env python3
"""UDGs in MODE 1: 21 glyphs at codes 144-164, G-mode, tokeniser, CLEAR cap.

48K / mode 0: codes 144-164 print as '?', the stored byte is not rewritten.
G-mode and the 8x8 draw path live in the extension ROM (mode 1 only).
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p3lib import Basic, SYM, ROOT, FONT
from rig import Spectrum

EXTROM = os.path.join(ROOT, 'build/opticos128ext.rom')
ESYM = {}
for line in open(os.path.join(ROOT, 'build/opticos128ext.sym')):
    m = re.match(r'(\w+)\s+EQU\s+0?([0-9A-F]+)H', line)
    if m:
        ESYM[m.group(1)] = int(m.group(2), 16)

UDG, RAMTOP, P_RAMT = SYM['UDG'], SYM['RAMTOP'], SYM['P_RAMT']
KS_MODE, OMODE = SYM['KS_MODE'], SYM['OMODE']
EBUF, CON_LEN = SYM['EBUF'], SYM['CON_LEN']
S_POSN, P_FLAG, PR_CTRL = 0x5C88, 0x5C91, 0x5C0E
ATTR_T, ERR_NR = 0x5C8F, 0x5C3A

def dpoke(s, a, v):
    s.poke(a, v & 255)
    s.poke(a + 1, v >> 8)

results = []
def check(name, got, want=True):
    if want is True:
        ok = bool(got)
        detail = '' if ok else repr(got)
    else:
        ok = got == want
        detail = '' if ok else '%r -> %r' % (want, got)
    results.append((name, ok, detail))
    print('%-56s %s  %s' % (name, 'PASS' if ok else 'FAIL', detail))

def out(b):
    r = [x for x in b.screen() if x != '']
    while r and r[-1] == ']':
        r.pop()
    return r

def raw_line(b, data, limit=400_000_000):
    s = b.s
    if not s.run_until(SYM['cg_lp'], 20_000_000):
        raise TimeoutError('not at prompt')
    s.load(EBUF, data)
    s.poke(CON_LEN, len(data))
    s.setregs(PC=SYM['con_enter'], SP=s.regs()['SP'] + 2)
    if not s.run_until(SYM['cg_lp'], limit):
        raise TimeoutError('raw line did not finish')

# ---------------------------------------------------------------------------
# 48K / mode 0: reserved area, PRINT '?', tokeniser, CLEAR
# ---------------------------------------------------------------------------
b = Basic(); s = b.s
udg = s.dpeek(UDG)
rt = s.dpeek(RAMTOP)
pramt = s.dpeek(P_RAMT)
check('UDG is RAMTOP+1', udg, rt + 1)
check('UDG area is 168 bytes below P_RAMT', pramt - rt, 168)
check('UDG area is zeroed at boot', all(s.peek(udg + i) == 0 for i in range(168)))

b.cls()
b.line('PRINT CHR$ 144;CHR$ 164;CHR$ 128')
row = [r for r in out(b) if r not in ('CLS',)]
# last printed row should be ???
printed = [r for r in out(b) if set(r) <= set('?')]
check('mode 0 PRINT CHR$ 144/164/128 is ???', printed[-1] if printed else '', '???')

b.line('a$=CHR$ 144: PRINT a$;ASC a$')
rows = out(b)
# '?144' somewhere
joined = ' '.join(rows)
check('mode 0 PRINT leaves the stored byte intact', '?144' in joined or any(r.endswith('144') and '?' in r for r in rows), True)

# tokeniser: UDG outside a string is a syntax error; inside a string is kept
b.line('CLS')
raw_line(b, b'PRINT ' + bytes([144]))
check('UDG byte outside a string is a Syntax error', out(b)[-1], 'Syntax error')

b.line('CLS')
raw_line(b, b'LET a$="' + bytes([144]) + b'"')
b.line('PRINT ASC a$')
check('UDG byte inside a string is kept', out(b)[-1], '144')

# CLEAR must not run RAMTOP into the UDG area; UDG stays put
udg0 = s.dpeek(UDG)
rt0 = s.dpeek(RAMTOP)
b.line('CLEAR %d' % (rt0 + 1))
check('CLEAR n into the UDG area is No room', (out(b)[-1], s.dpeek(RAMTOP), s.dpeek(UDG)),
      ('No room', rt0, udg0))
b.line('CLEAR 50000')
check('CLEAR 50000 leaves the UDG pointer at the top of RAM',
      (s.dpeek(RAMTOP), s.dpeek(UDG)), (50000, udg0))
b.line('CLEAR %d' % rt0)
check('CLEAR back to the default RAMTOP', s.dpeek(RAMTOP), rt0)

# G-mode does not fire in mode 0 (OMODE=64): Caps+9 is ignored, 'a' stays 'a'
check('mode 0 / 48K OMODE is 64', s.peek(OMODE), 64)
s.poke(KS_MODE, s.peek(KS_MODE) & ~4)
# type a short line with just a via the editor after a swallowed 15 would still
# leave 'a' in the buffer if G-mode were wrongly on
b.line('CLS')
b.line('PRINT "a"')
check('mode 0 letter keys are not remapped to UDG codes',
      'a' in ' '.join(out(b)) and chr(144) not in ''.join(out(b)))

# ---------------------------------------------------------------------------
# Extension: 8x8 UDG draw and G-mode mapping (called directly, no paging)
# ---------------------------------------------------------------------------
def pos8(row, col):
    lo = ((row & 7) << 5) | col   # rrca x3 of (row&7) is (row&7)<<5
    hi = 0x40 | (row & 0x18)
    return (hi << 8) | lo

sx = Spectrum(EXTROM)
sx.setregs(IFF1=0, IFF2=0, IM=1, I=0, SP=0x5FE0)
# 8-byte X shape
pat = bytes([0x81, 0x42, 0x24, 0x18, 0x18, 0x24, 0x42, 0x81])
dpoke(sx, UDG, 0xFF00)
sx.load(0xFF00, pat + bytes(8 * 20))  # first glyph; others blank
dpoke(sx, S_POSN, 5 + (10 << 8))        # L = column, H = row
sx.poke(P_FLAG, 0)
sx.poke(PR_CTRL, 0)
dpoke(sx, ATTR_T, 0x0700)  # ATTR_T / MASK_T
# clear the 8 screen bytes
base = pos8(10, 5)
for i in range(8):
    sx.poke(base + (i << 8), 0)
sx.call(ESYM['pr32'], IFF1=0, IFF2=0, AF=144 << 8, IY=ERR_NR)
got = bytes(sx.peek(base + (i << 8)) for i in range(8))
check('mode 1 pr32 draws UDG 144 from the UDG area', got, pat)
check('mode 1 print advances the column', sx.peek(S_POSN), 6)

# 128-143 stay '?' (font '?' is code 63, sub 32 = index 31)
dpoke(sx, S_POSN, 5 + (10 << 8))
sx.call(ESYM['pr32'], IFF1=0, IFF2=0, AF=128 << 8, IY=ERR_NR)
qgot = bytes(sx.peek(pos8(10, 5) + (i << 8)) for i in range(8))
# load '?' from the ext font at font8 + 8*(ord('?')-32)
font = open(os.path.join(ROOT, 'fonts/optic8x8.bin'), 'rb').read()
qref = font[8 * (ord('?') - 32):8 * (ord('?') - 31)]
check('mode 1 codes 128-143 print as ?', qgot, qref)

# G-mode
def gmap(d, mode=4):
    # x_g exits through back_ok, which on a 48K rig with only the
    # extension ROM loaded would jump to ext_main.  Stop at back_ok.
    sx.poke(KS_MODE, mode)
    sx.setregs(PC=ESYM['x_g'], DE=d << 8, IY=ERR_NR, IFF1=0, IFF2=0, SP=0x5FE0)
    if not sx.run_until(ESYM['back_ok'], 1_000_000):
        raise TimeoutError('x_g did not reach back_ok')
    return sx.regs()['DE'] >> 8, sx.peek(KS_MODE)

# Caps+9 toggles bit 2; D left as 15 (console still ignores it)
d, m = gmap(15, 0)
check('G-mode Caps+9 turns the bit on and leaves 15', (d, m & 4), (15, 4))
d, m = gmap(15, 4)
check('G-mode Caps+9 turns the bit off', (d, m & 4), (15, 0))

d, m = gmap(ord('a'), 4)
check('G-mode a becomes 144', (d, m & 4), (144, 4))
d, m = gmap(ord('U'), 4)
check('G-mode U becomes 164', (d, m & 4), (164, 4))
d, m = gmap(ord('v'), 4)
check('G-mode v is not remapped', (d, m & 4), (ord('v'), 4))
d, m = gmap(ord('a'), 0)
check('letters are plain when G-mode is off', (d, m & 4), (ord('a'), 0))
d, m = gmap(13, 4)
check('ENTER leaves G-mode', (d, m & 4), (13, 0))

failed = [n for n, ok, _ in results if not ok]
print()
print('%d/%d passed' % (len(results) - len(failed), len(results)))
if failed:
    print('FAILED:', ', '.join(failed))
    sys.exit(1)
