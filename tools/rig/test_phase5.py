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
check('IN runs (JOY dropped: IN 31 reads Kempston)', [pr('IN 254 > 0'), pr('IN 31 >= 0')], ['-1', '-1'])
check('SWAP numbers and strings', b.run(['a=1: b=2: a$="xy": b$="pqr"', 'SWAP a, b: SWAP a$, b$', 'b$=b$+"!"',
      'PRINT a;b;a$;b$']) [-1], '21pqrxy!')
check('SWAP type mismatch', b.run(['a=1: b$="x"', 'SWAP a, b$'])[-1], 'Type mismatch, line 2')

# ---- phase 5c: CASE, EXIT, ERROR n,msg$, CLEAR, FREE, KEY, RUN/RESTORE/SAVE AUTO name, BORDER
CASEP = ['DEF PROC t(x)', 'CASE x OF', 'WHEN 1, 2: PRINT "low";', 'WHEN 3', 'PRINT "three";', 'WHEN 4+1', 'PRINT "five";',
         'OTHERWISE: PRINT "other";', 'ENDCASE', 'PRINT "|";', 'ENDPROC']
check('CASE: lists, expressions, OTHERWISE', b.run(CASEP + ['FOR i=1 TO 6: t(i): NEXT'])[-1],
      'low|low|three|other|five|other|')
check('CASE: no match and no OTHERWISE', b.run(['CASE 9 OF', 'WHEN 1: PRINT "one"', 'ENDCASE', 'PRINT "after"'])[-1], 'after')
check('CASE: strings, nested CASE', b.run(['a$="b"', 'CASE a$ OF', 'WHEN "a": PRINT "A"', 'WHEN "b"', 'CASE 2 OF',
      'WHEN 2: PRINT "B2"', 'ENDCASE', 'OTHERWISE: PRINT "?"', 'ENDCASE'])[-1], 'B2')
check('CASE: type mismatch', b.run(['CASE 1 OF', 'WHEN "x": PRINT 1', 'ENDCASE'])[-1], 'Type mismatch, line 2')
check('CASE: ENDCASE missing', b.run(['CASE 1 OF', 'WHEN 1: PRINT 1'])[-1], 'Block structure, line 2')
b.line('CLS'); b.line('LIST'); 
b.run(['CASE 1 OF', 'WHEN 1', 'PRINT 1', 'OTHERWISE', 'PRINT 2', 'ENDCASE'], 'LIST')
check('LIST indents CASE', [x.lstrip('>') for x in out(b)[-6:]], ['CASE 1 OF', 'WHEN 1', '  PRINT 1', 'OTHERWISE', '  PRINT 2', 'ENDCASE'])
check('EXIT WHILE', b.run(['i=0', 'WHILE TRUE', 'i=i+1', 'IF i=4 THEN EXIT WHILE', 'WEND', 'PRINT i'])[-1], '4')
check('EXIT REPEAT (nested REPEAT inside)', b.run(['n=0', 'REPEAT', 'REPEAT', 'n=n+1', 'UNTIL TRUE', 'IF n>2 THEN EXIT REPEAT',
      'UNTIL FALSE', 'PRINT n'])[-1], '3')
check('EXIT FOR, one-line loop, frame dropped', b.run(['FOR i=1 TO 9: IF i=3 THEN EXIT FOR', 'NEXT: PRINT "x";i',
      'FOR j=1 TO 2: NEXT: PRINT j'])[-2:], ['x3', '3'])
check('EXIT FOR then the rest of the NEXT line', b.run(['FOR i=1 TO 5: IF i=2 THEN EXIT FOR', 'NEXT i: PRINT "n";i'])[-1], 'n2')
check('ERROR n: untrapped report', b.run(['PRINT 1', 'ERROR 13'])[-1], 'Syntax error, line 2')
check('error line numbers past line 2 (fixed in 5c)', b.run(['PRINT 1', 'PRINT 2', 'PRINT 3', 'PRINT 1/0'])[-1], 'Division by zero, line 4')
check('ERROR n, msg$: report', b.run(['PRINT 1', 'ERROR 99, "Level " + STR$ 7 + " missing"'])[-1], 'Level 7 missing, line 2')
check('ERROR n, msg$: ERR and ERR$ in CATCH', b.run(['TRY', 'ERROR 42, "my own error"', 'CATCH', 'PRINT ERR; ERR$', 'ENDTRY',
      'TRY', 'PRINT 1/0', 'CATCH', 'PRINT ERR$', 'ENDTRY', 'TRY', 'ERROR 42', 'CATCH', 'PRINT "[";ERR$;"]"', 'ENDTRY'])[-3:],
      ['42my own error', 'Division by zero', '[]'])
check('ERROR n, msg$: long message cut to 28', b.run(['ERROR 50, STRING$(40, "x")'])[-1], 'x' * 28 + ', line 1')
f0 = int(pr('FREE')); b.line('DIM big(100)'); f1 = int(pr('FREE'))
check('FREE, and DIM uses it', (f0 > 30000, f0 - f1 > 500), (True, True))
check('CLEAR forgets variables', b.run(['a=5', 'CLEAR', 'PRINT a'])[-1], 'No such variable, line 3')
rt = s.dpeek(SYM['RAMTOP']); b.line('CLEAR 50000'); r1 = s.dpeek(SYM['RAMTOP']); f2 = int(pr('FREE'))
b.line('CLS'); b.line('PRINT "still";: a$="ok": PRINT a$')
check('CLEAR n moves RAMTOP, FREE shrinks, still works', (r1, f2 < f0 - 10000, out(b)[-1]), (50000, True, 'stillok'))
b.line('CLS'); b.line('CLEAR 1000'); check('CLEAR n too low', (out(b)[-1], s.dpeek(SYM['RAMTOP'])), ('No room', 50000))
b.line('CLEAR %d' % rt); check('CLEAR back to the default', s.dpeek(SYM['RAMTOP']), rt)
check('CLEAR n in a program, then on', (b.run(['x=1', 'CLEAR 60000', 'y=2: PRINT y; "!"'])[-1], s.dpeek(SYM['RAMTOP'])), ('2!', 60000))
b.line('CLEAR %d' % rt)
def keyrun(keys, expr):
    for k in keys: s.key(k)
    v = pr(expr)
    for k in keys: s.key(k, False)
    s.frame(5); return v
check('KEY: held key, others, two at once, space, digit', [keyrun(['q'], 'KEY("q"); KEY("Q"); KEY("p")'),
      keyrun(['q', 'p'], 'KEY("q") AND KEY("p")'), keyrun([' '], 'KEY(" ")'), keyrun(['7'], 'KEY("7")'),
      keyrun([], 'KEY("q"); KEY("")')], ['-1-10', '-1', '-1', '-1', '00'])
PP = ['PRINT "top"', 'DEF PROC go', 'PRINT "go";', 'ENDPROC', 'DEF PROC two', 'READ a: PRINT a', 'ENDPROC',
      'DATA 1', 'DEF PROC d2', 'ENDPROC', 'DATA 2']
check('RUN name runs only that PROC', b.run(PP, 'RUN go')[-1], 'go')
check('RESTORE name: from the DATA after that DEF', b.run(PP + ['RESTORE d2: two: RESTORE: two'], 'RUN')[-2:], ['2', '1'])
check('RUN name: unknown PROC', b.run(PP, 'RUN nope')[-1], 'No such PROC or FN')
b.line('NEW'); b.enter(['PRINT "not auto"', 'DEF PROC hi', 'PRINT "auto ";PI', 'ENDPROC'])
s.mic_start(3); b.line('SAVE "auto" AUTO hi', 900_000_000)
ab = decode_pulses(s.mic_pulses())
check('SAVE AUTO: param 1 is the DEF line offset', ab[0][14] | ab[0][15] << 8 if ab else -1, 14)
atape = [NOTOGGLE | 35000] + sum((block_pulses(x) for x in ab), []) + [NOTOGGLE | 3500000]
b.line('NEW'); r = load('LOAD ""', atape)
check('LOAD of a SAVE AUTO program runs its PROC', r[-1], 'auto 3.14159265')
b.line('CLS'); b.line('LIST'); check('... and the program is there', [x.lstrip('>') for x in out(b)[-4:]], ['PRINT "not auto"', 'DEF PROC hi', '  PRINT "auto ";PI', 'ENDPROC'])
b.line('BORDER 5'); check('BORDER in OpticBASIC', (s.border(), s.peek(SYM['BORDCR']) >> 3 & 7), (5, 5))
def blk(flag, data):
    p = flag
    for x in data: p ^= x
    return bytes([flag]) + bytes(data) + bytes([p])
lprog = bytes([0, 10, 9, 0, 0xE7, 0x32, 0x0E, 0, 0, 2, 0, 0, 0x0D])   # 10 BORDER 2
lh = bytes([0]) + b'border    ' + bytes([len(lprog), 0, 10, 0, len(lprog), 0])
ltape = [NOTOGGLE | 35000] + block_pulses(blk(0, lh)) + block_pulses(blk(0xFF, lprog)) + [NOTOGGLE | 3500000]
b.line('BORDER 0'); load('LOAD ""', ltape)
check('BORDER in the legacy shim (10 BORDER 2)', (s.border(), s.peek(SYM['BORDCR']) >> 3 & 7), (2, 2))

# ---- v0.10: PROG, ERROR n without a message, deeper recursion
check('PROG is $5CCB while a legacy loader is in memory', s.dpeek(SYM['PROG']), 0x5CCB)
b.line('NEW'); check('PROG ($5C53) back at the program start after NEW', s.dpeek(SYM['PROG']), 0x5DF0)
check('DPEEK 23635 gives 24048', b.run(['PRINT DPEEK 23635'])[-1], '24048')
check('ERROR n without a message reports its number', b.run(['PRINT "x"', 'ERROR 42'])[-1], 'Error 42, line 2')
check('... typed directly too', (b.line('CLS'), b.line('ERROR 200'), out(b)[-1])[2], 'Error 200')
def deep(defs, call, step):
    return b.run(defs + ['k=1', 'TRY', 'REPEAT', call + ': k=k+%d' % step, 'UNTIL k>5000', 'CATCH', 'PRINT k-%d;" ";ERR$' % step, 'ENDTRY'],
                 limit=40_000_000_000)[-1].split(' ', 1)
fd = deep(['DEF FN g(n)', 'IF n<=0 THEN RETURN 0', 'RETURN 1+g(n-1)', 'ENDFN'], 'x=g(k)', 5)
check('recursive FN in an expression: over 50 deep (was 11)', (int(fd[0]) >= 50, fd[1]), (True, 'No room'))
pd = deep(['DEF PROC d(n)', 'IF n>0 THEN d n-1', 'ENDPROC'], 'd k', 5)
check('recursive PROC: over 130 deep (was 51)', (int(pd[0]) >= 130, pd[1]), (True, 'No room'))
check('fact(33) works (34! overflows a number)', b.run(['DEF FN f(n)', 'IF n<=1 THEN RETURN 1', 'RETURN n*f(n-1)', 'ENDFN', 'PRINT f(33)'])[-1], '8.68331763E+36')

# v0.13: INK 8 / PAPER 8 / BRIGHT 8 / FLASH 8 keep the screen's colour, for PRINT and PLOT / DRAW
A0 = 0x5800
b.run(['PRINT AT 0,0; PAPER 1; INK 7; STRING$(8, " ");', 'PRINT AT 0,0; PAPER 8; INK 2; "x";'])
check('PRINT PAPER 8 keeps the paper', '%02X' % s.peek(A0), '0A')
b.run(['PRINT AT 0,0; PAPER 1; INK 7; STRING$(8, " ");', 'PAPER 3: PAPER 8: INK 4: PLOT 8, 191'])
check('PLOT after PAPER 8 keeps the paper', '%02X' % s.peek(A0 + 1), '0C')
b.run(['PRINT AT 0,0; PAPER 1; INK 7; STRING$(8, " ");', 'INK 8: PAPER 5: PLOT 16, 191: DRAW 7, 0'])
check('DRAW with INK 8 keeps the ink', '%02X' % s.peek(A0 + 2), '2F')
b.run(['PRINT AT 0,0; PAPER 1; INK 7; BRIGHT 1; FLASH 1; STRING$(8, " ");', 'BRIGHT 8: FLASH 8: INK 2: PAPER 6: PLOT 24, 191'])
check('PLOT with BRIGHT 8, FLASH 8 keeps both', '%02X' % s.peek(A0 + 3), 'F2')
b.run(['PRINT AT 0,0; PAPER 1; INK 7; STRING$(8, " ");', 'INK 2: PAPER 6: PLOT 0, 191'])
check('PLOT without 8 sets ink and paper', '%02X' % s.peek(A0), '32')
# v0.13: a PROC or FN named with a keyword is error 21 at the DEF line
check('DEF PROC run: Keyword as name', b.run(['PRINT 1', 'DEF PROC run(x)', 'ENDPROC'])[-1], 'Keyword as name, line 2')
check('DEF FN cos: Keyword as name', b.run(['DEF FN cos(x) = 1', 'PRINT 2'])[-1], 'Keyword as name, line 1')
check('DEF PROC span still fine', b.run(['DEF PROC span(x)', 'PRINT x', 'ENDPROC', 'span 7'])[-1], '7')
check('DEF cos (no FN): Keyword as name', b.run(['DEF cos(x) = 1'])[-1], 'Keyword as name, line 1')
check('DEF sq (no FN) still fine', b.run(['DEF sq(x) = x*x', 'PRINT sq(5)'])[-1], '25')
check('ERROR 21 reports Keyword as name', b.run(['ERROR 21'])[-1], 'Keyword as name, line 1')

fails = [k for k, v in res.items() if not v]
json.dump(dict(cases=res, failures=fails), open(os.path.join(ROOT, 'build/test_phase5.json'), 'w'), indent=1)
print('\n%d/%d passed' % (len(res) - len(fails), len(res)))
sys.exit(1 if fails else 0)
