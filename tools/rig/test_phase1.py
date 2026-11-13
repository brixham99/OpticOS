#!/usr/bin/env python3
"""Phase 1 tests for OpticOS in the headless rig.

  python3 tools/rig/test_phase1.py [--ref path/to/48.rom] [--quick]

--ref enables the black-box comparisons with the Sinclair ROM (edge-timing
sweep, and loading OpticOS-saved blocks with the reference LD-BYTES).  The
reference ROM is only executed, never read or copied, and is never committed.
Screenshots go to docs/phase1/.
"""
import os, random, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import Spectrum, tap_pulses, block_pulses, decode_pulses, NOTOGGLE
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
ROM = os.path.join(ROOT, 'build/opticos.rom')
FONT = open(os.path.join(ROOT, 'font/font4x8.bin'), 'rb').read()
SHOTS = os.path.join(ROOT, 'docs/phase1')
REF = sys.argv[sys.argv.index('--ref') + 1] if '--ref' in sys.argv else None
QUICK = '--quick' in sys.argv
TAPES = {'bounceball': '/workspace/spectrum-ball/bounceball.tap',
         'miremare': '/workspace/mire-mare-repo/build/miremare.tap'}
SYM = {}
import re
for line in open(os.path.join(ROOT, 'build/opticos.sym')):
    m = re.match(r'(\w+)\s+EQU\s+0?([0-9A-F]+)H', line)
    if m: SYM[m.group(1)] = int(m.group(2), 16)
results = []
def check(name, ok, detail=''):
    results.append((name, bool(ok), detail))
    print('%-46s %s  %s' % (name, 'PASS' if ok else 'FAIL', detail))

def T(rows):
    return [r.rstrip('\x7f').rstrip() for r in rows]

def booted():
    s = Spectrum(ROM); s.frame(150); return s

# 1. boot screen against the mock-up layout
def t_boot():
    from PIL import Image
    s = booted()
    rows = T(s.text_rows(FONT))
    check('row 0 has no text (colour bar only)', rows[0] == '', repr(rows[0]))
    check('row 1 blank', rows[1] == '', repr(rows[1]))
    check('boot banner text at row 2', rows[2] == 'OpticOS (c) 2026 Optica Technology', repr(rows[2]))
    check('OpticBASIC version at row 3', rows[3] == 'OpticBASIC v0.1', repr(rows[3]))
    check('row 4 blank, row 5 prompt "] "', rows[4] == '' and rows[5] == ']', repr(rows[4:6]))
    check('rows 6-23 empty', all(r == '' for r in rows[6:]), '')
    check('cursor position row 5 col 2', (s.peek(0x5C89), s.peek(0x5C88)) == (5, 2))
    check('RAM test found 48K (P_RAMT=$FFFF)', s.dpeek(0x5CB4) == 0xFFFF, hex(s.dpeek(0x5CB4)))
    check('RAMTOP default $FF57', s.dpeek(0x5CB2) == 0xFF57, hex(s.dpeek(0x5CB2)))
    bar = list(s.block(0x5800, 32))
    want = [((i & 7) * 9) | (0x40 if i >= 8 else 0) for i in range(16) for _ in (0, 1)]
    check('row 0 colour bar: 16 paper swatches x 2 cells', bar == want, ' '.join('%02X' % v for v in bar[::2]))
    check('row 0 has no ink pixels', not any(s.block(0x4000 + (l << 8), 32) != bytes(32) for l in range(8)))
    attrs = set(s.block(0x5820, 736))
    check('rows 1-23 white on black, border 0', attrs == {7} and s.border() == 0, str(attrs))
    # wait until the blinking cursor is showing, then compare with the mock-up
    for _ in range(40):
        if s.peek(0x5C03): break
        s.frame()
    mock = Image.open(os.path.join(ROOT, 'assets/opticos_boot.png')).convert('RGB')
    ours = s.image(scale=1, border=True)
    diff = sum(1 for y in range(mock.height) for x in range(mock.width) if mock.getpixel((x, y)) != ours.getpixel((x, y)))
    check('boot screen matches assets/opticos_boot.png exactly', diff == 0, '%d differing pixels' % diff)
    s.image().save(os.path.join(SHOTS, 'rig_boot.png'))
    f0 = s.dpeek(0x5C78); s.frame(50)
    check('FRAMES counts 50 per second', s.dpeek(0x5C78) - f0 == 50, str(s.dpeek(0x5C78) - f0))

# 2. keyboard echo in 64 columns, wrap and scroll
def t_keys():
    s = booted()
    line = 'The quick brown fox: 0123456789 !@#$%&()_+-=*/?<>;,."[]{}|~^'
    assert len(line) <= 61
    s.type(line)
    rows = T(s.text_rows(FONT))
    check('typed text echoes in 64 columns after "] "', rows[5] == '] ' + line, repr(rows[5]))
    s.type('\n')
    rows = T(s.text_rows(FONT))
    check('unknown command reply, then a new prompt', rows[6] == 'Syntax error' and rows[7] == ']',
          repr(rows[6:8]))
    # caps lock and delete
    s.press(['^', '2']); s.type('abc'); s.press(['^', '2']); s.type('xy'); s.press(['^', '0'])
    rows = T(s.text_rows(FONT))
    check('caps lock and delete', rows[7] == '] ABCx', repr(rows[7]))
    # print 64-column wrap and scroll via RST 16 from machine code
    s = booted()
    text = bytes(range(32, 127)) * 20
    code = bytearray()
    # ld hl,text ; ld bc,len ; loop: ld a,(hl) ; rst 16 ; inc hl ; dec bc ; ld a,b ; or c ; jr nz,loop ; ret
    code += bytes([0x21, 0x00, 0x90, 0x01, len(text) & 255, len(text) >> 8,
                   0x7E, 0xD7, 0x23, 0x0B, 0x78, 0xB1, 0x20, 0xF8, 0xC9])
    s.load(0x8000, code); s.load(0x9000, text)
    s.call(0x8000, limit=200_000_000, IFF1=1, IFF2=1, IM=1)
    rows = T(s.text_rows(FONT))
    full = ''.join(chr(c) for c in text)
    # after scrolling, the last 23 rows hold the tail of the stream, 64 per row
    pos = s.peek(0x5C88), s.peek(0x5C89)
    tail_rows = [r.ljust(64) for r in rows[:pos[1] + 1]]
    stream = ''.join(tail_rows)[:pos[1] * 64 + pos[0]]
    check('RST 16 wraps at 64 columns and scrolls', full.endswith(stream.rstrip()) and len(stream) > 1000,
          'cursor row %d col %d' % (pos[1], pos[0]))
    s.image().save(os.path.join(SHOTS, 'rig_64col_scroll.png'))

# 3. SA-BYTES: record MIC, decode, timing; round trip through LD-BYTES
def save_block(rom, data, flag=0xFF):
    s = Spectrum(rom); s.frame(150)
    s.load(0x8000, data)
    s.mic_start(3)
    s.call(SYM['SA_BYTES'], limit=900_000_000, IX=0x8000, DE=len(data), AF=flag << 8)
    return s.mic_pulses()[1:]

def stats(p):
    import statistics
    return statistics.mean(p), min(p), max(p)

def t_save():
    random.seed(1)
    data = bytes(random.randrange(256) for _ in range(300))
    p = save_block(ROM, data)
    blocks = decode_pulses(p)
    par = 0xFF
    for b in data: par ^= b
    want = bytes([0xFF]) + data + bytes([par])
    check('SA-BYTES output decodes to flag+data+parity', blocks and blocks[0] == want,
          '%d blocks, %d bytes' % (len(blocks), len(blocks[0]) if blocks else 0))
    pil = [x for x in p[:3000] if 1800 < x < 2600]
    i = next(k for k in range(3000, 3400) if p[k] < 1000)   # first sync half
    s1, s2 = p[i], p[i + 1]
    bits = p[i + 2:i + 2 + 16 * 300]
    b0 = [x for x in bits if x < 1280]; b1 = [x for x in bits if x >= 1280]
    m = lambda v: sum(v) / len(v)
    det = 'pilot %.0f, sync %d/%d, bit0 %.0f (%d..%d), bit1 %.0f (%d..%d) T' % (
        m(pil), s1, s2, m(b0), min(b0), max(b0), m(b1), min(b1), max(b1))
    ok = abs(m(pil) - 2168) < 25 and abs(s1 - 667) < 40 and abs(s2 - 735) < 40 and \
        abs(m(b0) - 855) < 25 and abs(m(b1) - 1710) < 25 and max(b0) < 1000 and min(b1) > 1550
    check('SA-BYTES pulse timings within tolerance', ok, det)
    check('SA-BYTES header pilot is 8063 half-pulses',
          sum(1 for x in save_block(ROM, bytes(17), 0x00)[:8100] if 1800 < x < 2600) >= 8060)
    return p, want

def load_block(rom, pulses, length, flag=0xFF, verify=False, ref=None):
    s = Spectrum(rom); s.frame(150)
    s.tape([NOTOGGLE | 35000] + pulses + [NOTOGGLE | 3500000])
    af = (flag << 8) | (0 if verify else 1)
    r = s.call(0x0556, limit=900_000_000, IX=0x8000, DE=length, AF=af)
    return r['AF'] & 1, s.block(0x8000, length), s

def t_load():
    random.seed(2)
    data = bytes(random.randrange(256) for _ in range(500))
    par = 0xFF
    for b in data: par ^= b
    blk = bytes([0xFF]) + data + bytes([par])
    for scale in (1.0, 0.9, 1.1):
        c, got, _ = load_block(ROM, block_pulses(blk, 0, scale), 500)
        check('LD-BYTES loads a block at %.0f%% speed' % (scale * 100), c == 1 and got == data)
    c, got, _ = load_block(ROM, block_pulses(blk, 0), 500, verify=True)
    check('LD-BYTES verify mode (memory empty: must fail)', c == 0)
    bad = bytearray(blk); bad[100] ^= 1
    c, got, _ = load_block(ROM, block_pulses(bytes(bad), 0), 500)
    check('LD-BYTES reports a parity error', c == 0)
    c, got, _ = load_block(ROM, block_pulses(blk, 0), 500, flag=0x00)
    check('LD-BYTES rejects a wrong flag byte', c == 0)

# 4. black-box comparisons with the reference ROM
def edge_B(rom, P, b0=0):
    s = Spectrum(rom); s.frame(150)
    s.tape([P, NOTOGGLE | 3500000], play=False)
    import rig
    rig.lib.z_ear_play(1)
    r = s.call(0x05E7, limit=5_000_000, BC=(b0 << 8) | 0x00)
    return (r['BC'] >> 8, r['AF'] & 1, r['BC'] & 255)

def t_ref():
    if not REF:
        check('reference comparisons', True, 'skipped (no --ref)'); return
    worst = 0; rows = []
    for P in range(300, 16000, 97):
        a = edge_B(ROM, P); b = edge_B(REF, P)
        worst = max(worst, abs(a[0] - b[0]) if a[1] == b[1] else 99)
        if a[2] != b[2]: worst = 99
    check('LD-EDGE-1 B/C/carry vs reference, 300-16000 T', worst <= 1, 'max |dB| = %d' % worst)
    random.seed(3)
    data = bytes(random.randrange(256) for _ in range(200))
    p = save_block(ROM, data)
    c, got, _ = load_block(REF, p, 200)
    check('reference LD-BYTES loads an OpticOS-saved block', c == 1 and got == data)
    p = save_block(REF, data)
    c, got, _ = load_block(ROM, p, 200)
    check('OpticOS LD-BYTES loads a reference-saved block', c == 1 and got == data)

# 5. BEEPER period
def t_beeper():
    s = booted()
    out = []
    for hl in (100, 500, 1500):
        s.mic_start(4)
        s.call(SYM['BEEPER'], limit=200_000_000, DE=40, HL=hl, IFF1=1, IFF2=1, IM=1)
        p = s.mic_pulses()[2:-1]
        per = sum(p) / len(p) * 2
        out.append((hl, per, 8 * hl + 241))
    ok = all(abs(a - b) <= max(12, 0.003 * b) for _, a, b in out)
    check('BEEPER period = 8*HL + 241 T (0.3%)', ok, '; '.join('HL=%d %.0f/%d' % o for o in out))

# 6. LOAD "" of real game tapes through the EAR feed
def t_games():
    for name, tap in TAPES.items():
        if QUICK and name == 'miremare': continue
        s = booted()
        s.type('load ""'); s.tape(tap); s.press(['\n'])
        hdrs = set()
        for i in range(300 * 50):
            s.frame()
            for r in s.text_rows(FONT)[:6]:
                if r.startswith(('Program:', 'Bytes:')): hdrs.add(r)
            if s.regs()['PC'] >= 0x6000 and s.tape_pos() >= s.tape_len: break
        s.frame(150)
        pc = s.regs()['PC']
        s.image().save(os.path.join(SHOTS, 'rig_%s.png' % name))
        check('LOAD "" runs %s (EAR feed, no traps)' % name, pc >= 0x6000,
              'PC=%04X after %.0f s; %s' % (pc, s.frames / 50, sorted(hdrs)))
        if name == 'bounceball':
            # the game responds to keys: SPACE starts it
            before = s.block(0x4000, 6144); s.press([' '], 5, 50)
            check('Bounce Ball responds to SPACE', s.block(0x4000, 6144) != before)
            s.image().save(os.path.join(SHOTS, 'rig_bounceball_play.png'))
        else:
            # Mire Mare pokes 23739,111: its "Bytes:" lines must be hidden
            check('POKE 23739,111 hides the Bytes: line', 'Bytes: MIREMARE  ' not in hdrs, '')

os.makedirs(SHOTS, exist_ok=True)
for t in (t_boot, t_keys, t_save, t_load, t_ref, t_beeper, t_games):
    t()
fails = [r for r in results if not r[1]]
print('\n%d passed, %d failed' % (len(results) - len(fails), len(fails)))
json.dump(results, open(os.path.join(ROOT, 'build/test_phase1.json'), 'w'), indent=1)
sys.exit(1 if fails else 0)
