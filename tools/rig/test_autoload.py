"""Auto-load typing: an emulator that auto-loads a tape (Fuse's File > Open
with auto-load on, its phantom typist) resets the machine and types LOAD ""
the Sinclair way - J, SYMBOL+P, SYMBOL+P, ENTER ("Keyword" mode) or
L O A D " " ENTER ("Keystroke" mode) - from the first frame the keyboard
is read.  OpticOS v1.0.2 drops every key typed before its prompt appears,
so the typing does nothing: no load and no error, just the ] prompt.
LOAD "" typed after the prompt still loads."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import Spectrum
from typist import Typist, KEYMAP, STATES, STATES_KEYSTROKE
import p3lib
from p3lib import LINEBUF, CON_LEN, SYM
fails = 0
def check(name, ok, info=''):
    global fails
    print('%-62s %s %s' % (name, 'PASS' if ok else 'FAIL', info)); fails += not ok
rom = p3lib.ROM
def screen(s):
    b = p3lib.Basic.__new__(p3lib.Basic); b.s = s
    return [r for r in b.screen() if r]
for mode, states, want in (('Keyword', STATES, ['j', 'sym+p', 'sym+p', 'enter']),
                           ('Keystroke', STATES_KEYSTROKE, ['l', 'o', 'a', 'd', 'sym+p', 'sym+p', 'enter'])):
    s = Spectrum(rom); t = Typist(s, states=states)
    for n in range(400):
        t.frame(lambda k, d: s.key(KEYMAP[k], d))
        if t.state == 'INACTIVE': break
    s.frame(100)
    rows = screen(s)
    line = bytes(s.peek(LINEBUF + i) for i in range(s.peek(CON_LEN))).decode('latin1')
    check('%s: the typist typed all its keys' % mode, [x[2] for x in t.log] == want, t.log)
    check('%s: nothing typed, a clean ] prompt, no error' % mode,
          rows == ['OpticOS (c) 2026 Optica Technology Design', 'OpticBASIC v1.0.2', ']'] and line == '', (rows, line))
    check('%s: not loading (border black, at the prompt)' % mode,
          s.border() == 0 and not (0x0556 <= s.regs()['PC'] < 0x0605), '%04X' % s.regs()['PC'])
# LOAD "" typed by hand after the prompt still loads
s = Spectrum(rom); s.frame(250)
s.type('load ""\n'); s.frame(20)
check('LOAD "" typed after the prompt waits in the tape loader',
      0x0556 <= s.regs()['PC'] < 0x0605 and s.border() == 7, '%04X border %d' % (s.regs()['PC'], s.border()))
# a key pressed during the chime is dropped too
s = Spectrum(rom); s.frame(100); s.type('x', hold=3, gap=3); s.frame(150)
check('a key pressed during the chime is dropped', screen(s)[-1:] == [']'], screen(s)[-2:])
# J"" typed by hand is an ordinary (wrong) line now
b = p3lib.Basic()
b.line('j""')
rows = [r for r in b.screen() if r]
check('j"" typed by hand is not LOAD (an error, no load)', rows[-2] in ('No such PROC or FN', 'Syntax error') and b.s.border() == 0, rows[-3:])
print('\n%d failure(s)' % fails); sys.exit(1 if fails else 0)
