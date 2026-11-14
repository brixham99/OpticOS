"""Auto-load typing: Fuse's phantom typist (File > Open with auto-load on)
types J, SYMBOL+P, SYMBOL+P, ENTER, one key per frame, from the first frame
in which the keyboard is read.  OpticOS must not lose those keys under the
start-up chime, and J"" alone must run as LOAD "".  Also checks that
ordinary lines are untouched by the J"" rule."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import Spectrum
from typist import Typist, KEYMAP
import p3lib
from p3lib import LINEBUF, CON_LEN
fails = 0
def check(name, ok, info=''):
    global fails
    print('%-60s %s %s' % (name, 'PASS' if ok else 'FAIL', info)); fails += not ok
rom = p3lib.ROM
s = Spectrum(rom); t = Typist(s)
for n in range(300):
    t.frame(lambda k, d: s.key(KEYMAP[k], d))
    if t.state == 'INACTIVE': break
s.frame(3)
cl = s.peek(CON_LEN)
line = bytes(s.peek(LINEBUF + i) for i in range(cl)).decode('latin1')
check('typist: all four keys taken', [x[2] for x in t.log] == ['j', 'sym+p', 'sym+p', 'enter'], t.log)
check('typist: J"" runs as LOAD ""', line == 'LOAD ""', repr(line))
check('typist: in the tape loader (LD-BYTES)', 0x0556 <= s.regs()['PC'] < 0x0605, '%04X' % s.regs()['PC'])
for txt in ('J""', 'j""'):
    b = p3lib.Basic()
    try: b.line(txt, 3_000_000); ok = False
    except TimeoutError: ok = 0x0556 <= b.s.regs()['PC'] < 0x0605 and b.s.border() == 7
    check('%s typed by hand waits in the tape loader' % txt, ok, '%04X' % b.s.regs()['PC'])
b = p3lib.Basic()
for txt in ('j = 5: PRINT j', 'PRINT "j"; ""', 'j""x'):
    b.line(txt)
rows = [r for r in b.screen() if r]
check('j = 5: PRINT j still prints 5', '5' in rows, rows[-6:])
check('PRINT "j"; "" untouched', 'j' in rows, rows[-6:])
check('j""x is still an error, not LOAD', rows[-2] in ('No such PROC or FN', 'Syntax error'), rows[-6:])
print('\n%d failure(s)' % fails); sys.exit(1 if fails else 0)
