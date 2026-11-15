#!/usr/bin/env python3
"""rig.py - OpticOS headless rig on the shared Z80 core (emu/z80core.h).

Spectrum(rom) boots a 16K ROM from $0000 with write protection on the 48K
Spectrum shell (libz80.so, z80.c).  It offers frame stepping with the 50 Hz
interrupt, the keyboard matrix (type text, hold keys), an EAR input feed
built from TAP files with the standard ROM timings, a MIC recorder that
decodes saved pulses back to TAP blocks, screenshots, and a screen-to-text
decoder for the 4x8 font.

PicoCalc(rom) runs build/opticos_pc.rom on the PicoCalc machine
(libpicocalc.so, emu/picocalc.c): the same keyboard matrix and timing, with
the 320x320 display (80x40 text) in place of the Spectrum screen and tape.
"""
import ctypes, os, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
EMU = os.path.join(HERE, '..', '..', 'emu')

def build(so, src):
    deps = [src, os.path.join(EMU, 'z80core.h')]
    if not os.path.exists(so) or os.path.getmtime(so) < max(map(os.path.getmtime, deps)):
        subprocess.check_call(['gcc', '-O2', '-shared', '-fPIC', '-o', so, src])
    l = ctypes.CDLL(so)
    l.z_mem.restype = ctypes.POINTER(ctypes.c_uint8)
    l.z_tstates.restype = ctypes.c_longlong
    l.z_run_until.argtypes = [ctypes.c_int, ctypes.c_longlong]
    l.z_run_until2.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_longlong]
    return l
lib = build(os.path.join(HERE, 'libz80.so'), os.path.join(HERE, 'z80.c'))
lib.z_mic_buf.restype = ctypes.POINTER(ctypes.c_uint32)
lib.z_mic_count.restype = ctypes.c_long
lib.z_ear_pos.restype = ctypes.c_long
pclib = build(os.path.join(HERE, 'libpicocalc.so'), os.path.join(EMU, 'picocalc.c'))
pclib.pc_bits.restype = ctypes.POINTER(ctypes.c_uint8)
pclib.pc_attrs.restype = ctypes.POINTER(ctypes.c_uint8)

# --- keyboard: (row, bit); rows $FE..$7F
ROWS = ['^zxcv', 'asdfg', 'qwert', '12345', '09876', 'poiuy', '\nlkjh', ' #mnb']  # ^ caps, # sym
KEYPOS = {}
for r, keys in enumerate(ROWS):
    for b, k in enumerate(keys): KEYPOS[k] = (r, b)
SYM = {':': 'z', '`': 'x', '?': 'c', '/': 'v', '<': 'r', '>': 't', '!': '1', '@': '2', '#': '3',
       '$': '4', '%': '5', '_': '0', ')': '9', '(': '8', "'": '7', '&': '6', '"': 'p', ';': 'o',
       '=': 'l', '+': 'k', '-': 'j', '^': 'h', '.': 'm', ',': 'n', '*': 'b'}
EMODE = {'[': 'y', ']': 'u', '{': 'f', '}': 'g', '\\': 'd', '|': 's', '~': 'a'}

# --- tape: standard ROM encoding
PILOT, SYNC1, SYNC2, BIT0, BIT1 = 2168, 667, 735, 855, 1710
NOTOGGLE = 0x80000000

def tap_blocks(path):
    d = open(path, 'rb').read(); i = 0; out = []
    while i < len(d):
        n = d[i] | d[i + 1] << 8; out.append(d[i + 2:i + 2 + n]); i += 2 + n
    return out

def block_pulses(blk, pause_ms=1000, scale=1.0):
    p = [PILOT] * (8063 if blk[0] < 128 else 3223) + [SYNC1, SYNC2]
    for byte in blk:
        for k in range(7, -1, -1):
            t = BIT1 if byte >> k & 1 else BIT0
            p += [t, t]
    p = [int(x * scale) for x in p]
    if pause_ms: p.append(NOTOGGLE | int(3500 * pause_ms))
    return p

def tap_pulses(path, lead_ms=200, scale=1.0):
    p = [NOTOGGLE | 3500 * lead_ms]
    for b in tap_blocks(path): p += block_pulses(b, scale=scale)
    return p

def decode_pulses(lens):
    """Decode recorded half-pulse lengths (T) into blocks (flag..parity)."""
    blocks = []; i = 0; n = len(lens)
    while i < n:
        # find a run of pilot pulses
        run = 0
        while i < n and 1800 < lens[i] < 2600: run += 1; i += 1
        if run < 200:
            i += 1; continue
        if i + 1 >= n: break
        i += 2  # sync pulses
        bits = []
        while i + 1 < n and 600 < lens[i] < 2200 and 600 < lens[i + 1] < 2200:
            bits.append(1 if lens[i] + lens[i + 1] > 2565 else 0); i += 2
        data = bytes(int(''.join(map(str, bits[k:k + 8])), 2) for k in range(0, len(bits) - 7, 8))
        blocks.append(data)
    return blocks

class Spectrum:
    lib = lib
    def __init__(self, rom, ram48=True):
        self.lib.z_init()
        self.mem = self.lib.z_mem()
        data = open(rom, 'rb').read() if isinstance(rom, str) else rom
        assert len(data) == 16384
        ctypes.memmove(self.mem, data, 16384)
        if not ram48:
            raise NotImplementedError
        self.lib.z_setpc(0)
        self.frames = 0
    # ---- memory
    def peek(self, a): return self.mem[a]
    def dpeek(self, a): return self.mem[a] | self.mem[a + 1] << 8
    def poke(self, a, v): self.mem[a] = v & 255
    def block(self, a, n): return bytes(self.mem[a:a + n])
    def load(self, a, data): ctypes.memmove(ctypes.addressof(self.mem.contents) + a, bytes(data), len(data))
    def regs(self):
        r = (ctypes.c_int * 17)(); self.lib.z_getregs(r)
        return dict(zip('AF BC DE HL IX IY SP PC AF_ BC_ DE_ HL_ I R IFF1 IFF2 IM'.split(), list(r)))
    def setregs(self, **kw):
        d = self.regs(); d.update(kw)
        r = (ctypes.c_int * 17)(*[d[k] for k in 'AF BC DE HL IX IY SP PC AF_ BC_ DE_ HL_ I R IFF1 IFF2 IM'.split()])
        self.lib.z_setregs(r)
    # ---- time
    def frame(self, n=1):
        for _ in range(n): self.lib.z_frame(); self.frames += 1
    def run_until(self, pc, tstates): return self.lib.z_run_until(pc, tstates)
    def run_until2(self, pc1, pc2, tstates): return self.lib.z_run_until2(pc1, pc2, tstates)
    def call(self, addr, ret=0x5FF0, limit=50_000_000, **regs):
        """Call a ROM routine with registers; returns regs on return."""
        self.load(ret, b'\x18\xfe')           # JR $ sentinel
        sp = regs.pop('SP', 0x5FE0)
        self.poke(sp - 2, ret & 255); self.poke(sp - 1, ret >> 8)
        self.setregs(PC=addr, SP=sp - 2, **regs)
        if not self.run_until(ret, limit): raise TimeoutError('routine did not return')
        return self.regs()
    # ---- keyboard
    def key(self, k, down=True):
        r, b = KEYPOS[k]; self.lib.z_key(r, b, 1 if down else 0)
    def press(self, keys, hold=3, gap=3):
        for k in keys: self.key(k)
        self.frame(hold)
        for k in keys: self.key(k, False)
        self.frame(gap)
    def type(self, text, hold=3, gap=3):
        for ch in text:
            if ch == '\n': self.press(['\n'], hold, gap)
            elif ch in EMODE:
                self.press(['^', '#'], hold, gap); self.press([EMODE[ch]], hold, gap)
            elif ch in SYM: self.press(['#', SYM[ch]], hold, gap)
            elif ch.isupper(): self.press(['^', ch.lower()], hold, gap)
            else: self.press([ch], hold, gap)
    # ---- tape
    def tape(self, path_or_pulses, play=True, scale=1.0):
        p = tap_pulses(path_or_pulses, scale=scale) if isinstance(path_or_pulses, str) else path_or_pulses
        arr = (ctypes.c_uint32 * len(p))(*p)
        self.lib.z_ear_load(arr, len(p)); self.lib.z_ear_play(1 if play else 0)
        self.tape_len = len(p)
    def tape_pos(self): return self.lib.z_ear_pos()
    def mic_start(self, bit=3): self.lib.z_mic_bit(bit); self.lib.z_mic_record(1)
    def mic_pulses(self):
        n = self.lib.z_mic_count(); b = self.lib.z_mic_buf()
        return [b[i] for i in range(n)]
    # ---- screen
    def border(self): return self.lib.z_border()
    def bitmap(self):
        """192 rows x 256 bools (ink pixels, before attributes)."""
        m = self.mem; rows = []
        for y in range(192):
            a = 0x4000 | ((y & 0xC0) << 5) | ((y & 7) << 8) | ((y & 0x38) << 2)
            rows.append([(m[a + (x >> 3)] >> (7 - (x & 7))) & 1 for x in range(256)])
        return rows
    def image(self, scale=2, border=True):
        from PIL import Image
        bm = self.bitmap(); m = self.mem
        bw = 32 if border else 0
        im = Image.new('RGB', (256 + 2 * bw, 192 + 2 * bw), PAL[self.border()])
        px = im.load()
        for y in range(192):
            for x in range(256):
                at = m[0x5800 + (y >> 3) * 32 + (x >> 3)]
                p = BPAL if at & 0x40 else PAL
                px[x + bw, y + bw] = p[at & 7] if bm[y][x] else p[(at >> 3) & 7]
        return im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    def text_rows(self, font):
        """Decode the screen as rows of 4x8 characters (24x64 on the Spectrum)."""
        glyphs = {}
        for ch in range(32, 128):
            k = (ch - 32) >> 1
            g = tuple((font[8 * k + r] >> 4) if ch % 2 == 0 else (font[8 * k + r] & 15) for r in range(8))
            glyphs.setdefault(g, chr(ch))
        bm = self.bitmap(); out = []
        for row in range(len(bm) // 8):
            s = ''
            for col in range(len(bm[0]) // 4):
                g = tuple(int(''.join(str(bm[row * 8 + r][col * 4 + c]) for c in range(4)), 2) for r in range(8))
                s += glyphs.get(g, '\x7f' if all(v == 15 for v in g) else '\ufffd')
            out.append(s.rstrip())
        return out

PAL = [(0, 0, 0), (0, 0, 215), (215, 0, 0), (215, 0, 215), (0, 215, 0), (0, 215, 215), (215, 215, 0), (215, 215, 215)]
BPAL = [(0, 0, 0), (0, 0, 255), (255, 0, 0), (255, 0, 255), (0, 255, 0), (0, 255, 255), (255, 255, 0), (255, 255, 255)]

class PicoCalc(Spectrum):
    """The PicoCalc machine: 320x320 display, attributes per 4x8 cell."""
    lib = pclib
    W = H = 320
    def tape(self, *a, **k): raise NotImplementedError('the PicoCalc has no tape')
    def border(self): return 0
    def bitmap(self):
        """320 rows x 320 bools (ink pixels, before attributes)."""
        b = self.lib.pc_bits()
        return [[(b[y * 40 + (x >> 3)] >> (7 - (x & 7))) & 1 for x in range(320)] for y in range(320)]
    def attr(self, col, row): return self.lib.pc_attrs()[row * 80 + col]
    def image(self, scale=2, border=False):
        from PIL import Image
        bm = self.bitmap(); a = self.lib.pc_attrs()
        im = Image.new('RGB', (320, 320)); px = im.load()
        for y in range(320):
            for x in range(320):
                at = a[(y >> 3) * 80 + (x >> 2)]
                p = BPAL if at & 0x40 else PAL
                px[x, y] = p[at & 7] if bm[y][x] else p[(at >> 3) & 7]
        return im.resize((320 * scale, 320 * scale), Image.NEAREST)
