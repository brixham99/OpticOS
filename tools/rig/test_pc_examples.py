#!/usr/bin/env python3
"""The PicoCalc examples tape (examples/picocalc/picocalc_examples.tap) in
the rig: LOAD "picocalc_examples" runs the menu, then every example loads by
name and runs without an error, with its own check.  Happy Bat is played by
test_pc_happybat.py.  Screenshots go to build/picocalc/.  Build the tape
first (examples/picocalc/mktape_pc.py)."""
import os, re, sys, shutil, tempfile
os.environ['OPTICOS_MACHINE'] = 'picocalc'
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from p3lib import Basic, SYM, shot

fails = 0
def check(name, got, want):
    global fails
    ok = got == want
    print('%-56s %s %s' % (name, 'PASS' if ok else 'FAIL', '' if ok else '%r, wanted %r' % (got, want)))
    fails += not ok
card = tempfile.mkdtemp(prefix='pcex_card_')
shutil.copy(os.path.join(HERE, '..', '..', 'examples', 'picocalc', 'picocalc_examples.tap'), card)
b = Basic(); s = b.s; s.sd(card)
def rows(): return [r for r in b.screen() if r.replace('�', '').strip()]
def error(): return [r for r in rows() if re.search(r', line \d+$', r)]
def run(name, limit=4_000_000_000):
    b.line('NEW'); b.line('CLS'); b.line('LOAD "%s"' % name)
    loaded = 'Program: %s' % name in rows()
    b.line('CLS'); b.line('RUN', limit)
    return loaded

# the menu: it starts itself; each line fits 40 columns
b.line('LOAD "picocalc_examples"')
r = b.screen()
check('the menu runs itself (LOAD by the file\'s name)', r[0], 'OpticOS examples for the PicoCalc')
names = re.findall(r'LOAD "(\w+)"', '\n'.join(r))
check('it lists the 11 examples', names, ['times', 'guess', 'fact', 'sort', 'errors', 'ball', 'tree', 'colour',
                                         'hilo', 'flag', 'happybatpc'])
check('no line wraps (each description on its own row)', all(x.startswith('   ') for x in r[3:24:2]), True)
shot(s, 'pc_ex_menu.png')

for name, want in (('times', '12 x 7 = 84'), ('guess', 'Got it: 37 in 3 tries'), ('fact', '9 squared = 81')):
    ok = run(name)
    check('%s: loads, runs, no error' % name, (ok, error()), (True, []))
    check('%s: its last line' % name, rows()[-2].strip(), want)
for name in ('sort', 'errors'):
    ok = run(name)
    check('%s: loads, runs, no error' % name, (ok, error()), (True, []))

ok = run('ball')
check('ball: loads, runs 300 moves inside 40 x 40, no error', (ok, error(), rows()[-2].strip()), (True, [], 'Moves: 300'))
ok = run('tree'); shot(s, 'pc_ex_tree.png')
check('tree: loads, grows inside 320 x 320, no error', (ok, error(), rows()[0].startswith('A tree in')), (True, [], True))
ok = run('colour'); shot(s, 'pc_ex_colour.png')
check('colour: loads, runs, no error', (ok, error()), (True, []))
check('colour: "red" in its own cell, the space before it clean', (s.attr(13, 13) & 7, s.attr(12, 13) & 7), (2, 7))
ok = run('flag'); shot(s, 'pc_ex_flag.png')
check('flag: loads, runs, no error', (ok, error()), (True, []))
paper = lambda c, r: s.attr(c, r) >> 3 & 7
check('flag: blue field, white border, red cross', (paper(14, 1), paper(17, 0), paper(19, 0), paper(0, 9), paper(0, 7)),
      (1, 7, 2, 2, 7))
check('flag: the timing line below it', b.screen()[22].startswith('Drawn in'), True)

# hilo: play it, halving the range each time
ok = run('hilo')
lo, hi, last = 1, 100, ''
for _ in range(10):
    g = (lo + hi) // 2
    s.type('%d\n' % g); s.run_until(SYM['cg_lp'], 200_000_000)
    last = rows()[-2].strip()
    if 'too low' in last: lo = g + 1
    elif 'too high' in last: hi = g - 1
    else: break
check('hilo: loads, and halving finds the number', (ok, last.startswith('Got it in'), error()), (True, True, []))
shutil.rmtree(card)
print('%d failure(s)' % fails); sys.exit(1 if fails else 0)
