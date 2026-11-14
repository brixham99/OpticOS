"""NEW (v1.0.2) is a full cold start, exactly as at power-on: RAM test and
clear, colour bar, copyright and version banner, chime, ] prompt."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p3lib
from p3lib import SYM, LINEBUF, CON_LEN
fails = 0
def check(name, ok, info=''):
    global fails
    print('%-58s %s %s' % (name, 'PASS' if ok else 'FAIL', info)); fails += not ok
cold = p3lib.Basic(); cold.s.frame(200)
want_rows = [r for r in cold.screen()]
want_attrs = cold.s.block(0x5800, 768)
b = p3lib.Basic(); s = b.s
rt0 = s.dpeek(SYM['RAMTOP'])
b.enter(['PRINT "hello"']); b.line('a = 7'); b.line('b% = 9'); b.line('BORDER 2: PAPER 1: INK 6')
b.line('CLEAR 50000'); s.poke(60000, 0x5A)
check('set-up: program, variables, colours, CLEAR 50000 in place',
      s.dpeek(SYM['RAMTOP']) != rt0 and s.border() == 2)
# type NEW and ENTER as con_enter would, then follow the cold start
s.run_until(SYM['cg_lp'], 20_000_000)
s.load(LINEBUF, b'NEW'); s.poke(CON_LEN, 3)
s.setregs(PC=SYM['con_enter'], SP=s.regs()['SP'] + 2)
hit0 = s.run_until(0x0000, 50_000_000)
check('NEW goes through $0000 (the reset entry)', hit0)
hitb = s.run_until(SYM['BEEPER'], 100_000_000)
check('the chime plays (BEEPER is called)', hitb)
s.frame(150)
check('screen is exactly the power-on screen (text)', [r for r in b.screen()] == want_rows, [r for r in b.screen() if r])
check('colour bar and attributes as at power-on', s.block(0x5800, 768) == want_attrs)
check('border black again', s.border() == 0, s.border())
check('RAMTOP back to its power-on value (CLEAR 50000 undone)', s.dpeek(SYM['RAMTOP']) == rt0, (hex(s.dpeek(SYM['RAMTOP'])), hex(rt0)))
check('RAM cleared (a byte at 60000 is 0 again)', s.peek(60000) == 0, s.peek(60000))
b.line('CLS'); b.line('LIST'); b.line('PRINT b%'); b.line('PRINT a')
rows = [r for r in b.screen() if r]
check('program gone, A%-Z% cleared, other variables gone', rows == [']', ']', '0', ']', 'No such variable', ']'], rows)
print('\n%d failure(s)' % fails); sys.exit(1 if fails else 0)
