#!/usr/bin/env python3
# test_phase5.py - phase 5 statements in the rig: INPUT, DATA / READ /
# RESTORE, and SAVE / LOAD / VERIFY (program and CODE) through the MIC
# and EAR signals, with no traps.
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
from p3lib import Basic, SYM, ROOT, ROM
from rig import decode_pulses, block_pulses, NOTOGGLE
res = {}
def check(name, got, want):
    ok = got == want; res[name] = ok
    print('%-36s %s' % (name, 'ok' if ok else 'FAIL %r -> %r' % (want, got)))
def out(b):
    r = [x for x in b.screen() if x != '']
    while r and r[-1] == ']': r.pop()
    return r
b = Basic(); s = b.s
# INPUT
b.run(['INPUT "n? ";a', 'PRINT a*2']); s.type('21'); s.frame(5)
check('INPUT echoes typed keys', out(b)[-1], 'n? 21')
s.press(['\n']); s.frame(30)
check('INPUT number with prompt', out(b)[-2:], ['n? 21', '42'])
b.run(['INPUT a$, b', 'PRINT b;a$']); b.line('hi there'); b.line('7')
check('INPUT string and number', out(b)[-1], '7hi there')
b.run(['DIM a(3)', 'INPUT a(2)', 'PRINT a(2)+1']); b.line('-1.5')
check('INPUT into an array element', out(b)[-1], '-0.5')
b.line('CLS'); b.line('INPUT x: PRINT x^2'); b.line('12')
check('INPUT in direct mode', out(b)[-1], '144')
# DATA / READ / RESTORE
check('DATA / READ numbers, strings, expressions',
      b.run(['DATA 1, 2, "x"', 'PRINT "go"', 'DATA 3+4', 'READ a, b, c$, d', 'PRINT a+b;c$;d'])[-1], '3x7')
check('RESTORE', b.run(['DATA 5', 'READ a', 'RESTORE', 'READ b', 'PRINT a+b'])[-1], '10')
check('RUN restores DATA', b.run(['DATA 9', 'READ a', 'PRINT a'], 'RUN')[-1] == '9' and
      (b.line('CLS'), b.line('RUN'), out(b)[-1])[2], '9')
check('Out of DATA error', b.run(['DATA 1', 'READ a, b'])[-1], 'Out of DATA, line 2')
# SAVE a program, NEW, LOAD it back from the recorded signal
PROG = ['DEF sq(x) = x*x', 'FOR i=1 TO 3', 'PRINT sq(i);', 'NEXT']
b.line('NEW'); b.enter(PROG)
s.mic_start(3); b.line('SAVE "squares"', 900_000_000)
blocks = decode_pulses(s.mic_pulses())
hdr = blocks[0] if blocks else b''
check('SAVE: header block', (len(blocks), hdr[:13]), (2, bytes([0, 0]) + b'squares   ' + bytes([hdr[12] if len(hdr) > 12 else 0])))
check('SAVE: data starts with "OB" 1 0', blocks[1][1:5] if len(blocks) > 1 else b'', b'OB\x01\x00')
tape = [NOTOGGLE | 35000] + sum((block_pulses(x) for x in blocks), []) + [NOTOGGLE | 3500000]
def load(cmd, t=tape):
    s.tape(t); b.line('CLS'); b.line(cmd, 900_000_000); return out(b)
b.line('NEW'); r = load('LOAD "squares"')
check('LOAD "name" shows the header', 'Program: squares' in r, True)
b.line('CLS'); b.line('LIST'); r = out(b)
check('LOAD restores the program', [x.lstrip('>') for x in r[1:]], ['DEF sq(x)=x*x', 'FOR i=1 TO 3', '  PRINT sq(i);', 'NEXT'])
b.line('CLS'); b.line('RUN'); check('loaded program runs', out(b)[-1], '149')
b.line('NEW'); load('LOAD ""'); b.line('CLS'); b.line('RUN')
check('LOAD "" loads it too', out(b)[-1], '149')
r = load('VERIFY "squares"'); check('VERIFY passes', r[-1], 'Program: squares')
b.line('AUTO'); b.line('PRINT'); b.line('')
r = load('VERIFY "squares"'); check('VERIFY fails after a change', r[-1], 'Tape: bad or missing block')
# SAVE ... CODE / LOAD ... CODE
s.mic_start(3); b.line('SAVE "rom" CODE 0, 300', 900_000_000)
cb = decode_pulses(s.mic_pulses())
check('SAVE CODE: type 3 header and data', (cb[0][1] if cb else -1, len(cb[1]) - 2 if len(cb) > 1 else 0,
      cb[1][1:301] == open(ROM, 'rb').read()[:300] if len(cb) > 1 else False), (3, 300, True))
ctape = [NOTOGGLE | 35000] + sum((block_pulses(x) for x in cb), []) + [NOTOGGLE | 3500000]
load('LOAD "" CODE 40000', ctape)
check('LOAD "" CODE start', s.block(40000, 300) == open(ROM, 'rb').read()[:300], True)
r = load('VERIFY "rom" CODE 40000', ctape); check('VERIFY CODE', r[-1], 'Bytes: rom')
s.image().save(os.path.join(ROOT, 'docs/phase5/rig_tape.png'))
fails = [k for k, v in res.items() if not v]
json.dump(dict(cases=res, failures=fails), open(os.path.join(ROOT, 'build/test_phase5.json'), 'w'), indent=1)
print('\n%d/%d passed' % (len(res) - len(fails), len(res)))
sys.exit(1 if fails else 0)
