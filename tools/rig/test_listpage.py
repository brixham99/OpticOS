#!/usr/bin/env python3
"""LIST pauses at each screenful (v1.0.3): "cont?" on the bottom row after 23
newlines.  Y (either case) lists the next screenful; any other key stops with
the marker on the first line of the screenful just shown; BREAK at the prompt
reports "Break".  The prompt is rubbed out, so the ] prompt and the edit line
come back clean."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p3lib import Basic, SYM
fails = 0
def check(name, ok, info=''):
    global fails
    print('%-62s %s %s' % (name, 'PASS' if ok else 'FAIL', '' if ok else info)); fails += not ok
PROG = ['DEF PROC p%d' % i if i % 10 == 0 else ('PRINT "line %d"' % i) for i in range(100)]
PROG[13] = 'PRINT "' + 'a long line that wraps onto a second row of the screen, ' * 2 + '"'
def start(prog=PROG):
    b = Basic(); b.enter(prog); b.cls(); s = b.s
    s.run_until(SYM['cg_lp'], 20_000_000)
    s.load(SYM['EBUF'], b'LIST'); s.poke(SYM['CON_LEN'], 4)
    s.setregs(PC=SYM['con_enter'], SP=s.regs()['SP'] + 2)
    return b, s
def at_prompt(s): return bool(s.run_until(SYM['lp_w'], 50_000_000))
def tap(s, k, shift=False):
    if shift: s.key('^')
    s.key(k); s.frame(4); s.key(k, False)
    if shift: s.key('^', False)
    s.frame(4)
def rows(b): return b.screen()
def line_at(b, p): # program line text at address p, as LIST shows it (first word)
    return p
b, s = start()
ok = at_prompt(s); r = rows(b)
check('LIST stops at a prompt', ok)
check('"cont?" on the bottom row, nothing else there', r[23] == 'cont?', repr(r[23]))
check('the first program line is on the top row', r[0].lstrip('> ').startswith('DEF PROC p0'), repr(r[0]))
check('23 rows of listing above the prompt', all(x for x in r[:23]), r[:23])
top2 = None
tap(s, 'y'); ok = at_prompt(s); r2 = rows(b)
check('Y lists the next screenful and asks again', ok and r2[23] == 'cont?', repr(r2[23]))
check('the line after the last one shown is now on the top row', r2[0] not in r[:23] and r2[0] != '', (r[22], r2[0]))
tap(s, 'y', shift=True); ok = at_prompt(s); r3 = rows(b)
check('CAPS+Y (upper case) also continues', ok and r3 != r2)
top3 = r3[0].strip()
tap(s, 'n'); fin = s.run_until(SYM['cg_lp'], 50_000_000); r4 = rows(b)
check('any other key stops at the ] prompt', bool(fin) and r4[-1] == ']' or r4[23] == ']', r4[-3:])
check('the prompt is rubbed out (no "cont?" left)', not any('cont' in x for x in r4), r4[-3:])
curl = s.dpeek(SYM['CURL'])
# LIST again: the line with the ">" marker is the one that was on the top row when we stopped
s.load(SYM['EBUF'], b'CLS'); s.poke(SYM['CON_LEN'], 3); s.setregs(PC=SYM['con_enter'], SP=s.regs()['SP'] + 2)
s.run_until(SYM['cg_lp'], 50_000_000)
s.load(SYM['EBUF'], b'LIST'); s.poke(SYM['CON_LEN'], 4); s.setregs(PC=SYM['con_enter'], SP=s.regs()['SP'] + 2)
seen = []
for _ in range(6):
    if not at_prompt(s): break
    seen += [x for x in rows(b)[:23]]
    if any(x.startswith('>') for x in seen): break
    tap(s, 'y')
mk = [x for x in seen if x.startswith('>')]
check('the marker ">" is on the line that was at the top', bool(mk) and mk[0][1:].strip() == top3.lstrip('>').strip(), (mk[:1], top3))
tap(s, 'n'); s.run_until(SYM['cg_lp'], 50_000_000)
# BREAK at the prompt
b, s = start(); c0 = s.dpeek(SYM['CURL']); at_prompt(s); tap(s, 'y'); at_prompt(s)
s.key('^'); s.key(' '); s.frame(6); s.key(' ', False); s.key('^', False)
fin = s.run_until(SYM['cg_lp'], 50_000_000); r = [x for x in rows(b) if x]
check('BREAK at the prompt reports Break', bool(fin) and any('Break' in x for x in r[-3:]), r[-3:])
check('BREAK leaves the marker where it was', s.dpeek(SYM['CURL']) == c0, hex(s.dpeek(SYM['CURL'])))
check('no "cont?" left after BREAK', not any('cont' in x for x in r), r[-3:])
# a short program lists without a pause
b = Basic(); b.enter(PROG[:10]); s = b.s; s.run_until(SYM['cg_lp'], 20_000_000)
s.load(SYM['EBUF'], b'LIST'); s.poke(SYM['CON_LEN'], 4); s.setregs(PC=SYM['con_enter'], SP=s.regs()['SP'] + 2)
hit = s.run_until2(SYM['lp_w'], SYM['cg_lp'], 50_000_000)
check('a program shorter than a screen lists without pausing', hit == 2, hit)
# typing after a stopped LIST: the edit line works normally
b, s = start(); at_prompt(s); tap(s, 'x'); s.run_until(SYM['cg_lp'], 50_000_000)
b.line('PRINT 6*7'); r = [x for x in rows(b) if x]
check('the edit line works after a stopped LIST', '42' in r[-2:] or r[-2] == '42', r[-3:])
print('%d failure(s)' % fails); sys.exit(1 if fails else 0)
