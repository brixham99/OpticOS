#!/usr/bin/env python3
"""PicoCalc sound: the beeper's edges as the firmware gets them (pc_edges,
with T-state times) give the start-up chime and BEEP at the right pitch and
length, and pc_render, which makes the firmware's 31.25 kHz samples from
them, keeps that pitch.  Runs on the PicoCalc ROM whatever OPTICOS_MACHINE
says."""
import os, sys, statistics
os.environ['OPTICOS_MACHINE'] = 'picocalc'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p3lib import Basic

CLOCK = 3_500_000
RATE = 31_250
fails = 0
def check(name, got, want, tol):
    global fails
    ok = got is not None and abs(got - want) <= tol * want
    print('%-52s %s %s' % (name, 'PASS' if ok else 'FAIL', '%.4g (want %.4g)' % (got or 0, want)))
    fails += not ok
def notes(edges):
    """split edges into notes (a gap of 20,000 T ends one): [(Hz, seconds)]"""
    out, cur = [], [edges[0]] if edges else []
    for e in edges[1:]:
        if (e[0] - cur[-1][0]) & 0xFFFFFFFF > 20_000: out.append(cur); cur = []
        cur.append(e)
    if cur: out.append(cur)
    res = []
    for n in out:
        if len(n) < 4: continue
        half = statistics.median((b[0] - a[0]) & 0xFFFFFFFF for a, b in zip(n, n[1:]))
        res.append((CLOCK / (2 * half), ((n[-1][0] - n[0][0]) & 0xFFFFFFFF) / CLOCK))
    return res

b = Basic(); s = b.s                    # boots: the chime plays
chime = notes(s.edges())
check('chime: first note, Hz', chime[0][0] if chime else None, 523, 0.015)
check('chime: first note, seconds', chime[0][1] if chime else None, 0.15, 0.05)
check('chime: second note, Hz', chime[1][0] if len(chime) > 1 else None, 122, 0.015)
check('chime: second note, seconds', chime[1][1] if len(chime) > 1 else None, 0.45, 0.05)
for dur, pitch in ((0.2, 0), (0.5, -12), (0.1, 24)):
    s.edges(); b.line('BEEP %s, %d' % (dur, pitch))
    n = notes(s.edges())
    hz = 261.6256 * 2 ** (pitch / 12)
    check('BEEP %s, %d: Hz' % (dur, pitch), n[0][0] if n else None, hz, 0.01)
    check('BEEP %s, %d: seconds' % (dur, pitch), n[0][1] if n else None, dur, 0.03)

# the firmware's samples: 625 a frame (31.25 kHz), from the same edges
s.edges(); t0 = s.lib.pc_tstates(); b.line('BEEP 0.3, 7'); t1 = s.lib.pc_tstates()
e = s.edges()
n = (t1 - t0) * RATE // CLOCK
smp, lv = s.render(t0, t1 - t0, n, e, 0, 200)
rises = [i for i in range(1, n) if smp[i - 1] < 100 <= smp[i]]
hz = 261.6256 * 2 ** (7 / 12)
check('samples: BEEP 0.3, 7 keeps its pitch, Hz', (len(rises) - 1) * RATE / (rises[-1] - rises[0]) if len(rises) > 2 else None, hz, 0.01)
check('samples: the note lasts 0.3 s', (rises[-1] - rises[0]) / RATE if rises else None, 0.3, 0.03)
check('samples: within 0-amp', max(smp) <= 200 and min(smp) >= 0, True, 0)
check('samples: level at the end matches the beeper', lv == s.lib.pc_level(), True, 0)
quiet, _ = s.render(t1, 69888, 625, [], lv, 200)
check('samples: no edges, a steady level (silence)', len(set(quiet)), 1, 0)
print('%d failure(s)' % fails); sys.exit(1 if fails else 0)
