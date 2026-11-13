#!/usr/bin/env python3
"""test_traps.py - OpticOS under emulators that fast-load / fast-save .tap
files by trapping the ROM tape routines (v1.0.1).  Three published trap
styles are emulated in the rig:
  fuse        load: the RET NZ at $056B, resume at the RET at $05E2;
              save: the EX AF,AF' at $04D0, resume at the RET at $053E
              (Fuse 1.6 tape.c / z80/opcodes_base.c, its trap_load_block rules)
  entry       load: fetch at $0556 (A = flag, carry = load), return to caller;
              save: fetch at $04C2, return to caller
  spectranet  load: fetch at $0562, resume in SA/LD-RET at $053F
Each style loads the example tape (LOAD "", LOAD "name"), the legacy games
and a program it saved itself; results are compared with real-signal runs."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from p3lib import Basic, SYM, ROOT
from rig import tap_blocks, decode_pulses
PASS = FAIL = 0
def check(name, ok, info=''):
    global PASS, FAIL
    PASS += bool(ok); FAIL += not ok
    print('%-62s %s  %s' % (name, 'PASS' if ok else 'FAIL', '' if ok else info))
CF = 1
LOADPC = {'fuse': 0x056B, 'entry': 0x0556, 'spectranet': 0x0562}
SAVEPC = {'fuse': 0x04D0, 'entry': 0x04C2, 'spectranet': 0x04C2}
class Trapped(Basic):
    def __init__(self, style, blocks=()):
        Basic.__init__(self); self.style = style; self.blocks = list(blocks); self.pos = 0
        self.saved = []; self.traps = 0; self.misses = 0
    def pop(self):
        s = self.s; r = s.regs(); v = s.dpeek(r['SP']); s.setregs(SP=r['SP'] + 2); return v
    def load_trap(self):
        s = self.s; r = s.regs(); self.traps += 1
        if self.style == 'entry': flag, af = r['AF'] >> 8, r['AF']          # not yet swapped into AF'
        else: flag, af = r['AF_'] >> 8, r['AF_']
        de, ix = r['DE'], r['IX']
        if self.pos >= len(self.blocks): self.misses += 1; return False
        blk = self.blocks[self.pos]; self.pos += 1
        ok = False
        if blk[0] != flag: pass                                             # wrong flag: carry clear, next block
        elif len(blk) != de + 2: self.misses += 1                            # Fuse would play the signal instead
        else:
            data = blk[1:1 + de]; par = 0
            for b in blk: par ^= b
            if af & CF: s.load(ix, data); ok = par == 0
            else: ok = s.block(ix, de) == bytes(data) and par == 0
            ix = (ix + de) & 0xFFFF; de = 0
        f = (r['AF'] & 0xFF & ~CF) | (CF if ok else 0)
        s.setregs(AF=(r['AF'] & 0xFF00) | f, DE=de, IX=ix)
        if self.style == 'fuse': s.setregs(PC=0x05E2)
        elif self.style == 'entry': s.setregs(PC=self.pop())
        else: s.setregs(PC=0x053F)
        return True
    def save_trap(self):
        s = self.s; r = s.regs(); a = r['AF'] >> 8; de, ix = r['DE'], r['IX']
        data = s.block(ix, de); par = a
        for b in data: par ^= b
        self.saved.append(bytes([a]) + data + bytes([par]))
        s.setregs(PC=0x053E if self.style == 'fuse' else self.pop())
    def line(self, text, limit=2_000_000_000):
        s = self.s
        if not s.run_until(SYM['cg_lp'], 20_000_000): raise TimeoutError('not at prompt')
        s.load(SYM['EBUF'], text.encode()); s.poke(SYM['CON_LEN'], len(text))
        s.setregs(PC=SYM['con_enter'], SP=s.regs()['SP'] + 2)
        s.run_until(SYM['con_enter'] + 1, 100)                               # step off con_enter
        lp, sp_ = LOADPC[self.style], SAVEPC[self.style]
        while True:
            hit = s.run_until2(lp, SYM['cg_lp'], limit) if True else 0
            if hit == 2: return
            if hit == 0: raise TimeoutError('line did not finish: ' + text)
            if not self.load_trap(): return                                 # tape ran out: leave it waiting
            # save traps are handled by a second pass
    def save_line(self, text, limit=2_000_000_000):
        s = self.s
        if not s.run_until(SYM['cg_lp'], 20_000_000): raise TimeoutError('not at prompt')
        s.load(SYM['EBUF'], text.encode()); s.poke(SYM['CON_LEN'], len(text))
        s.setregs(PC=SYM['con_enter'], SP=s.regs()['SP'] + 2)
        while True:
            hit = s.run_until2(SAVEPC[self.style], SYM['cg_lp'], limit)
            if hit == 2: return
            if hit == 0: raise TimeoutError('save did not finish')
            self.save_trap()
    def rows(self): return [r for r in self.screen() if r and r != ']']
    def after_tape_ok(self):
        r = self.s.regs(); return r['IFF1'] == 1

EX = tap_blocks(os.path.join(ROOT, 'examples/opticos_examples.tap'))
src = lambda n: [l.strip() for l in open(os.path.join(ROOT, 'examples/src/%s.bas' % n)) if l.strip()]
ref = Basic()
want = {}
for n in ('fact', 'sort', 'times'):
    want[n] = [r for r in ref.run(src(n)) if r != ']']
GAMES = [('bounceball', '/workspace/spectrum-ball/bounceball.tap'), ('miremare', '/workspace/mire-mare-repo/build/miremare.tap')]
for style in ('fuse', 'entry', 'spectranet'):
    b = Trapped(style, EX); b.line('LOAD ""')
    rows = b.rows()
    check('%s: LOAD "" runs the menu' % style, any('OpticOS example tape' in r for r in rows), rows[:3])
    check('%s: LOAD "" took 2 blocks by trap' % style, b.pos == 2 and b.misses == 0, (b.pos, b.misses))
    check('%s: interrupts back on, border restored' % style, b.after_tape_ok() and b.s.border() == 0, b.s.border())
    for n in ('fact', 'sort', 'times'):
        b = Trapped(style, EX); b.line('LOAD "%s"' % n)
        seen = [r for r in b.rows() if r.startswith('Program:')]
        b.cls(); b.line('RUN', 400_000_000); out = b.rows()
        check('%s: LOAD "%s" skips to it and RUN matches' % (style, n), out[-len(want[n]):] == want[n] and seen[-1] == 'Program: ' + n, out[-3:])
    b = Trapped(style, EX); b.line('LOAD "hilo"')
    check('%s: LOAD "hilo" passes all ten headers' % style, b.pos == 20 and b.misses == 0, (b.pos, b.misses))
    b = Trapped(style, EX); b.line('VERIFY "examples"')    # needs the program in memory: expect a clean failure, not a crash
    check('%s: VERIFY with nothing loaded fails cleanly' % style, b.s.run_until(SYM['cg_lp'], 50_000_000), '')
    for g, path in GAMES:
        if not os.path.exists(path): check('%s: %s present' % (style, g), False, path); continue
        bl = tap_blocks(path); b = Trapped(style, bl)
        try: b.line('LOAD ""', 3_000_000_000)
        except TimeoutError: pass                               # the game runs and never returns to the prompt
        check('%s: %s loads every block by trap' % (style, g), b.pos == len(bl) and b.misses == 0, (b.pos, len(bl), b.misses))
    if style == 'spectranet': continue
    b = Trapped(style); b.line('NEW'); b.enter(src('fact')); b.save_line('SAVE "f"')
    s = b.s; s.mic_start(3)
    real = Basic(); real.line('NEW'); real.enter(src('fact')); real.s.mic_start(3); real.line('SAVE "f"', 2_000_000_000)
    rb = [bytes(x) for x in decode_pulses(real.s.mic_pulses())]
    check('%s: SAVE by trap gives the same blocks as the real signal' % style, b.saved == rb, (len(b.saved), len(rb)))
    c = Trapped(style, b.saved); c.line('LOAD "f"'); c.cls(); c.line('RUN', 400_000_000)
    check('%s: the trapped SAVE loads back and runs' % style, c.rows()[-len(want['fact']):] == want['fact'], c.rows()[-2:])
# lower / mixed case, as typed letter by letter
for cmd in ('load ""', 'Load ""', 'LoAd "examples"'):
    b = Trapped('fuse', EX); b.line(cmd)
    check('fuse: %s runs the menu' % cmd, any('OpticOS example tape' in r for r in b.rows()), b.rows()[:2])
# before the tape routine, LOAD and SAVE fetch no code at published tape entry points
import rig
PUBLISHED = (0x0605, 0x0767, 0x076E, 0x0802, 0x0808)
for cmd, prog, stop in (('LOAD ""', None, 0x0556), ('SAVE "x"', ['PRINT 1'], 0x04C2)):
    b = Basic(); s = b.s
    if prog: b.line('NEW'); b.enter(prog)
    s.run_until(SYM['cg_lp'], 20_000_000)
    s.load(SYM['EBUF'], cmd.encode()); s.poke(SYM['CON_LEN'], len(cmd))
    s.setregs(PC=SYM['con_enter'], SP=s.regs()['SP'] + 2)
    seen = set(); r = (rig.ctypes.c_int * 17)()
    for _ in range(3_000_000):
        rig.lib.z_getregs(r)
        if r[7] == stop: break
        seen.add(r[7]); rig.lib.z_step()
    hit = ['%04X' % a for a in PUBLISHED if a in seen]
    check('%s fetches nothing at $0605/$0767/$076E/$0802/$0808 first' % cmd, r[7] == stop and not hit, hit)
print('\n%d passed, %d failed' % (PASS, FAIL)); sys.exit(1 if FAIL else 0)
