#!/usr/bin/env python3
"""Happy Bat for the PicoCalc (examples/picocalc), played in the rig: LOAD
"happybatpc" from a card holding examples/picocalc/picocalc_examples.tap
runs the game, which loads its own code; the title screen; a game flown by an
autopilot (it steers the bat for the middle of the next gap) that must
score, at full speed (a step every 2 frames); then game over.  Screenshots
go to build/picocalc/.  Needs pasmo (for the code's symbols) and the tape
(examples/picocalc/mktape_pc.py)."""
import os, sys, shutil, tempfile
os.environ['OPTICOS_MACHINE'] = 'picocalc'
HERE = os.path.dirname(os.path.abspath(__file__))
EX = os.path.join(HERE, '..', '..', 'examples', 'picocalc')
sys.path.insert(0, HERE); sys.path.insert(0, EX)
from p3lib import Basic, SYM, shot
from mktape_pc import assemble

fails = 0
def check(name, got, want):
    global fails
    ok = got == want
    print('%-58s %s %s' % (name, 'PASS' if ok else 'FAIL', '' if ok else '%r, wanted %r' % (got, want)))
    fails += not ok

code, HB = assemble()
card = tempfile.mkdtemp(prefix='hbpc_card_')
shutil.copy(os.path.join(EX, 'picocalc_examples.tap'), card)
b = Basic(); s = b.s; s.sd(card)
def typed(text):                        # a line typed at the prompt, without waiting for the prompt again
    s.run_until(SYM['cg_lp'], 20_000_000)
    s.load(SYM['EBUF'], text.encode()); s.poke(SYM['CON_LEN'], len(text))
    s.setregs(PC=SYM['con_enter'], SP=s.regs()['SP'] + 2)
def rows(): return b.screen()
def tap_space(): s.key(' '); s.frame(3); s.key(' ', False); s.frame(3)

# ---- loading and the title screen
typed('LOAD "happybatpc"'); s.frame(400)
r = rows()
check('the game loaded its code ("HP" at 60017)', bytes(s.block(60017, 2)), b'HP')
i0 = HB['init'] - 60000                  # (the bytes before init are its variables)
check('the code is the assembled happybat_pc.asm', bytes(s.block(HB['init'], len(code) - i0)), code[i0:])
check('title: the name', r[8].strip(), 'H A P P Y    B A T')
check('title: the score line', ' '.join(r[0].split()), 'HAPPY BAT SCORE 0 BEST 0')
check('title: the help row', ' '.join(r[39].split()), 'SPACE flap BREAK stop')
ground = lambda: bytes(s.lib.pc_bits()[304 * 40 + i] for i in range(8 * 40))   # its 8 lines
g1 = ground(); s.frame(6); g2 = ground()       # (3 steps of 4 pixels; 4 would be the pattern's repeat)
check('title: the ground scrolls', g1 != g2 and any(g2), True)
check('title: the bat is drawn in its cells', s.attr(10, (16 + s.dpeek(HB['oldy'])) >> 3), 0x4E)
shot(s, 'pc_happybat_title.png')

# ---- a game, flown by the autopilot
tap_space(); s.frame(4)
check('SPACE starts a game (play mode)', s.peek(HB['mode']), 1)
def next_gap():
    best = None
    for i in range(5):
        a = HB['ptab'] + 6 * i
        x = s.peek(a)
        if x == 0x80: continue
        x = x - 256 if x > 127 else x
        if x + 7 >= 18 and (best is None or x < best[0]): best = (x, s.dpeek(a + 1), s.dpeek(a + 3))
    return best
t0, steps0, frames, pressed, mid = s.peek(HB['tick']), 0, 0, 0, False
score = lambda: int(rows()[0].split('SCORE')[1].split()[0])
while frames < 3000 and score() < 3:
    gap = next_gap()
    target = (gap[1] + gap[2]) // 2 - 4 if gap else 136
    if pressed: s.key(' ', False); pressed = 0
    elif s.dpeek(HB['baty']) > target + 6 and s.peek(HB['v16'] + 1) == 0: s.key(' '); pressed = 1
    s.frame(2); frames += 2
    if not mid and gap and gap[0] < 40: shot(s, 'pc_happybat_play.png'); mid = True
    if s.peek(HB['crash']): break
check('the autopilot scores 3 points', score() >= 3, True)
check('pipes on the screen', mid, True)
ticks = (s.peek(HB['tick']) - t0) & 255
lag = (ticks - frames // 2) % 256
pts = score()                           # (each point's BEEP and PRINT costs BASIC about a step)
check('a step every 2 frames (the code keeps pace)', lag >= 254 - pts or lag <= 2, True)

# ---- game over: stop flapping
s.key(' ', False); s.frame(400)
r = rows()
check('game over: the box', r[15].strip(), 'G A M E    O V E R')
check('game over: the score', ' '.join(r[17].split()), 'Score %d' % score())
shot(s, 'pc_happybat_over.png')
shutil.rmtree(card)
print('%d failure(s)' % fails); sys.exit(1 if fails else 0)
