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
# ---- phase 5b: graphics, colours, BEEP, functions, SWAP, machine
def px(x, y):
    yy = 191 - y
    a = 0x4000 | ((yy & 0xC0) << 5) | ((yy & 7) << 8) | ((yy & 0x38) << 2) | (x >> 3)
    return s.peek(a) >> (7 - (x & 7)) & 1
b.line('CLS'); b.line('PLOT 0,0: PLOT 255,191: PLOT 100,50')
check('PLOT corners and a point', (px(0, 0), px(255, 191), px(100, 50), px(101, 50)), (1, 1, 1, 0))
b.line('CLS'); b.line('PLOT 10,10: DRAW 20,5: DRAW TO 10,40')
line1 = all(px(10 + i, 10 + round(i * 5 / 20)) or px(10 + i, 10 + int(i * 5 / 20)) or px(10 + i, 11 + int(i * 5 / 20)) for i in range(21))
check('DRAW relative (Bresenham), ends at the target', (line1, px(30, 15)), (True, 1))
check('DRAW TO absolute, COORDS updated', (px(10, 40), s.peek(SYM['COORDS']), s.peek(SYM['COORDS'] + 1)), (1, 10, 40))
b.line('CLS'); b.line('OVER 1: PLOT 5,5: PLOT 5,5: OVER 0: INVERSE 1: PLOT 6,6: INVERSE 0')
check('OVER flips, INVERSE clears', (px(5, 5), px(6, 6)), (0, 0))
b.line('CLS'); b.line('PLOT 300,0')
check('PLOT out of range', out(b)[-1], 'Bad argument')
b.line('CLS'); b.line('PLOT 0,192'); check('PLOT y 192 out of range', out(b)[-1], 'Value outside range')
b.line('CLS'); b.line('PRINT INK 2; PAPER 6;"A";"B"')
attr = s.peek(0x5800 + 32 * 1)
check('PRINT INK/PAPER inside PRINT', attr, 6 * 8 + 2)
b.line('PRINT "C"'); check('temporary colours end with the PRINT', (s.peek(0x5800 + 32 * 2), s.peek(0x5800 + 32 * 3)), (s.peek(SYM['ATTR_P']),) * 2)
b.line('CLS'); b.line('BRIGHT 1: FLASH 1: PRINT "x": BRIGHT 0: FLASH 0')
check('BRIGHT / FLASH statements', s.peek(0x5800 + 32) & 0xC0, 0xC0)
s.mic_start(4); b.line('BEEP 0.2, 0', 400_000_000); bp = s.mic_pulses()[1:-1]
mid = bp[len(bp) // 4: 3 * len(bp) // 4]; per = 2 * sum(mid) / len(mid) if mid else 0
check('BEEP 0.2,0: middle C, 0.2 s', (abs(3500000 / per - 261.63) < 2 if per else False, round(len(bp) / 2 / 261.63, 1)), (True, 0.2))
s.mic_start(4); b.line('BEEP 0.1, 12'); bp = s.mic_pulses()[1:-1]
mid = bp[len(bp) // 4: 3 * len(bp) // 4]; per = 2 * sum(mid) / len(mid) if mid else 0
check('BEEP an octave up', abs(3500000 / per - 523.25) < 3 if per else False, True)
def pr(expr):
    b.line('CLS'); b.line('PRINT ' + expr); r = out(b); return r[-1] if r else ''
check('INSTR', [pr('INSTR("hello","l")'), pr('INSTR("hello","lo")'), pr('INSTR("hello","x")'),
                pr('INSTR("hello","l",4)'), pr('INSTR("ab","")'), pr('INSTR("ab","abc")')], ['3', '4', '0', '4', '1', '0'])
check('STRING$', [pr('STRING$(3,"ab")'), pr('LEN STRING$(0,"x")'), pr('STRING$(5,"-")+"|"')], ['ababab', '0', '-----|'])
check('HEX$', [pr('HEX$ 255'), pr('HEX$(-1)'), pr('HEX$ 4096')], ['00FF', 'FFFF', '1000'])
check('UPPER$', [pr('UPPER$ "MiXed 1z{"'), pr('LEN UPPER$ ""')], ['MIXED 1Z{', '0'])
check('ERR$', b.run(['TRY', 'PRINT 1/0', 'CATCH', 'PRINT ERR$', 'ENDTRY'])[-1], 'Division by zero')
check('DPOKE / DPEEK / PEEK', (b.line('CLS'), b.line('DPOKE 40000, 4660: PRINT DPEEK 40000; " "; PEEK 40001'), out(b)[-1])[2], '4660 18')
b.line('POKE 40010,1: POKE 40011,57: POKE 40012,48: POKE 40013,201')   # ld bc,12345 : ret
check('USR returns BC', pr('USR 40010'), '12345')
b.line('POKE 40010,62: POKE 40011,7: POKE 40012,211: POKE 40013,254: POKE 40014,201')  # ld a,7: out (254),a: ret
check('CALL', (b.line('CALL 40010: PRINT 5'), out(b)[-1])[1], '5')
check('IN / JOY run', [pr('IN 254 > 0'), pr('JOY >= 0')], ['-1', '-1'])
check('SWAP numbers and strings', b.run(['a=1: b=2: a$="xy": b$="pqr"', 'SWAP a, b: SWAP a$, b$', 'b$=b$+"!"',
      'PRINT a;b;a$;b$']) [-1], '21pqrxy!')
check('SWAP type mismatch', b.run(['a=1: b$="x"', 'SWAP a, b$'])[-1], 'Type mismatch, line 2')

fails = [k for k, v in res.items() if not v]
json.dump(dict(cases=res, failures=fails), open(os.path.join(ROOT, 'build/test_phase5.json'), 'w'), indent=1)
print('\n%d/%d passed' % (len(res) - len(fails), len(res)))
sys.exit(1 if fails else 0)
