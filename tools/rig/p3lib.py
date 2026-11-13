# p3lib.py - drive the OpticBASIC console in the rig by injecting lines
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from rig import Spectrum
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
ROM = os.path.join(ROOT, 'build/opticos.rom')
FONT = open(os.path.join(ROOT, 'font/font4x8.bin'), 'rb').read()
SYM = {}
for l in open(os.path.join(ROOT, 'build/opticos.sym')):
    m = re.match(r'(\S+)\s+EQU\s+0?([0-9A-F]+)H', l)
    if m: SYM[m.group(1)] = int(m.group(2), 16)
LINEBUF, CON_LEN = 0x5B00, 0x5B4F
class Basic:
    def __init__(self):
        self.s = Spectrum(ROM); self.s.frame(80)
    def line(self, text, limit=400_000_000):
        s = self.s; assert len(text) <= 61, text
        if not s.run_until(SYM['cg_lp'], 20_000_000): raise TimeoutError('not at prompt')
        s.load(LINEBUF, text.encode()); s.poke(CON_LEN, len(text))
        s.setregs(PC=SYM['con_enter'])
        if not s.run_until(SYM['cg_lp'], limit): raise TimeoutError('line did not finish: ' + text)
    def screen(self):
        return [r.rstrip('\x7f').rstrip() for r in self.s.text_rows(FONT)]
    def cls(self):
        self.line('CLS')
    def run(self, prog, cmd='RUN', limit=400_000_000):
        """NEW, enter the program, CLS, run cmd; returns the output rows"""
        self.line('NEW'); 
        for l in prog: self.line('>' + l)
        self.cls(); self.line(cmd, limit)
        rows = self.screen()
        while rows and rows[-1] in ('', ']'): rows.pop()
        return [r for r in rows if r != '' ]
