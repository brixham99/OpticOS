#!/usr/bin/env python3
# test_phase3.py - OpticBASIC interpreter tests (phase 3) in the rig.
# Lines are injected into the console's line buffer; "> text" adds a
# program line.  Writes build/test_phase3.json and a screenshot.
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
from p3lib import Basic, SYM, ROOT
T = []
def case(name, prog, cmd, want): T.append((name, prog, cmd, want))
case('ELSEIF chain', ['x=2', 'IF x=1', 'PRINT "one"', 'ELSEIF x=2', 'PRINT "two"', 'ELSE', 'PRINT "other"', 'ENDIF'], 'RUN', ['two'])
case('ELSE branch', ['x=7', 'IF x=1', 'PRINT "one"', 'ELSEIF x=2', 'PRINT "two"', 'ELSE', 'PRINT "other"', 'ENDIF'], 'RUN', ['other'])
case('nested IF', ['FOR i=1 TO 3', 'IF i>1', 'IF i=3', 'PRINT "c";', 'ELSE', 'PRINT "b";', 'ENDIF', 'ELSE', 'PRINT "a";', 'ENDIF', 'NEXT'], 'RUN', ['abc'])
case('one-line IF/ELSE', ['FOR x=1 TO 5 STEP 4', 'IF x>3 THEN PRINT "big" ELSE PRINT "small"', 'NEXT'], 'RUN', ['small', 'big'])
case('WHILE', ['i=0', 'WHILE i<3', 'PRINT i;', 'i=i+1', 'WEND', 'PRINT "!"'], 'RUN', ['012!'])
case('WHILE false at once', ['WHILE 0', 'PRINT "no"', 'WEND', 'PRINT "done"'], 'RUN', ['done'])
case('REPEAT/UNTIL', ['i=0', 'REPEAT', 'i=i+1', 'PRINT i;', 'UNTIL i=3'], 'RUN', ['123'])
case('FOR STEP -3', [], 'FOR i=10 TO 1 STEP -3: PRINT i;" ";: NEXT', ['10 7 4 1'])
case('nested FOR, NEXT v', ['FOR i=1 TO 2', 'FOR j=1 TO 3', 'PRINT i*j;', 'NEXT j', 'NEXT i'], 'RUN', ['123246'])
case('FN one line', ['DEF sq(x)=x*x', 'PRINT sq(7);sq(sq(2))'], 'RUN', ['4916'])
case('FN recursive', ['DEF fact(n)', 'IF n<2 THEN RETURN 1', 'RETURN n*fact(n-1)', 'ENDFN', 'PRINT fact(10)'], 'RUN', ['3628800'])
case('PROC bare name + args', ['DEF greet(n$, k)', 'PRINT "Hi ";n$;k', 'ENDPROC', 'greet "Bob", 2', 'greet("Al", 3)'], 'RUN', ['Hi Bob2', 'Hi Al3'])
case('PROC recursion', ['DEF down(n)', 'IF n>0 THEN PRINT n;: down n-1', 'ENDPROC', 'down 4'], 'RUN', ['4321'])
case('dynamic LOCAL', ['x=1', 'DEF p', 'LOCAL x', 'x=5', 'q', 'ENDPROC', 'DEF q', 'PRINT x', 'ENDPROC', 'p', 'PRINT x'], 'RUN', ['5', '1'])
case('LOCAL string restored', ['a$="out"', 'DEF p(a$)', 'a$=a$+"!"', 'PRINT a$', 'ENDPROC', 'p "in"', 'PRINT a$'], 'RUN', ['in!', 'out'])
case('TRY/CATCH', ['TRY', 'PRINT 1/0', 'PRINT "not here"', 'CATCH', 'PRINT "caught ";ERR', 'ENDTRY', 'PRINT "after"'], 'RUN', ['caught 5', 'after'])
case('TRY no error', ['TRY', 'PRINT "ok"', 'CATCH', 'PRINT "no"', 'ENDTRY', 'PRINT "after"'], 'RUN', ['ok', 'after'])
case('ERROR n', ['TRY', 'ERROR 42', 'CATCH', 'PRINT ERR', 'ENDTRY'], 'RUN', ['42'])
case('error in FN caught', ['DEF f(x)', 'RETURN 1/x', 'ENDFN', 'TRY', 'PRINT f(0)', 'CATCH', 'PRINT "c";ERR', 'ENDTRY', 'PRINT f(4)'], 'RUN', ['c5', '0.25'])
case('nested TRY rethrow', ['TRY', 'TRY', 'ERROR 7', 'CATCH', 'PRINT "in";ERR', 'ERROR 9', 'ENDTRY', 'CATCH', 'PRINT "out";ERR', 'ENDTRY'], 'RUN', ['in7', 'out9'])
case('uncaught error, line', ['PRINT 1', 'PRINT 1/0'], 'RUN', ['1', 'Division by zero, line 2'])
case('arrays 1D', ['DIM a(5), b$(2)', 'FOR i=0 TO 5', 'a(i)=i*i', 'NEXT', 'b$(1)="x"', 'PRINT a(5);a(3);b$(1);LEN b$(0)'], 'RUN', ['259x0'])
case('arrays 2D, int', ['DIM m(2,3), n%(4)', 'm(1,2)=7', 'n%(4)=-9', 'PRINT m(1,2);m(2,3);n%(4)'], 'RUN', ['70-9'])
case('bad subscript', ['DIM a(5)', 'a(6)=1'], 'RUN', ['Bad subscript, line 2'])
case('string functions', [], 'PRINT LEFT$("hello",2);RIGHT$("hello",3);MID$("hello",2,3)', ['helloell'])
case('string functions 2', [], 'PRINT ASC "A";CHR$ 66;STR$ 12;VAL "3.5"+1;LEN ""', ['65B124.50'])
case('string compare', [], 'PRINT "abc"<"abd";"b">"a";"a"="a";"ab"<"a"', ['-1-1-10'])
case('string GC stress', ['k$="keep"', 's$=""', 'FOR i=1 TO 1500', 't$=STR$ i+"abcdefghijklmnopqrstuvwxyz"', 's$=RIGHT$(s$+t$,60)', 'NEXT', 'PRINT LEN s$;RIGHT$(s$,5);k$;i'], 'RUN', ['60vwxyzkeep1501'])
case('hex and binary', [], 'PRINT &FF;" ";%101;" ";$10;" ";&7fff', ['255 5 16 32767'])
case('integer vars', [], 'a%=7/2: b%=-3: PRINT a%;b%;a%*b%', ['4-3-12'])
case('DIV MOD', [], 'PRINT 7 DIV 2;" ";7 MOD 3;" ";-7 DIV 2;" ";-7 MOD 2', ['3 1 -3 -1'])
case('logic and shifts', [], 'PRINT 6 AND 3;6 OR 1;NOT 0;1<<4;256>>2;5 XOR 1', ['27-116644'])
case('MAX MIN', [], 'PRINT MAX(3,9,2);MIN(3,9,2)', ['92'])
case('power right-assoc', [], 'PRINT 2^3^2;-2^2', ['512-4'])
case('TRUE FALSE PI', [], 'PRINT TRUE;FALSE;INT PI', ['-103'])
case('PRINT TAB comma', [], 'PRINT TAB(5);"x";TAB(10);"y"', ['     x    y'])
case('comments', ['REM a comment', "' another", 'PRINT "x" : REM trailing'], 'RUN', ['x'])
case('no such variable', [], 'PRINT zz', ['No such variable'])
case('type mismatch', [], 'a$=1', ['Type mismatch'])
case('unclosed block', ['PRINT 1', 'IF 1', 'PRINT 2'], 'RUN', ['Block structure, line 2'])
case('stray ENDIF', ['PRINT 1', 'ENDIF'], 'RUN', ['Block structure, line 2'])
case('ENDPROC outside', [], 'ENDPROC', ['Not in a PROC or FN'])
case('NEXT without FOR', [], 'NEXT', ['NEXT but no FOR'])
case('no such PROC', [], 'frob 1', ['No such PROC or FN'])
case('END and STOP', ['PRINT 1', 'STOP', 'PRINT 2'], 'RUN', ['1', 'Stopped, line 2'])
case('vars cleared by RUN', ['PRINT q'], 'q=5: RUN', ['No such variable, line 1'])
PROG = ['REM structured demo', 'DEF fib(n)', 'IF n<2 THEN RETURN n', 'RETURN fib(n-1)+fib(n-2)', 'ENDFN',
        'DEF show(a$,n)', 'LOCAL i', 'FOR i=1 TO n', 'PRINT a$;" ";i;" ";fib(i)', 'NEXT', 'ENDPROC',
        'x=&10+%11', 'WHILE x>17', 'x=x-1', 'WEND', 'TRY', 'show "fib",x-12', 'CATCH', 'PRINT "err ";ERR', 'ENDTRY']
LISTED = ['REM structured demo', 'DEF fib(n)', '  IF n<2 THEN RETURN n', '  RETURN fib(n-1)+fib(n-2)', 'ENDFN',
          'DEF show(a$,n)', '  LOCAL i', '  FOR i=1 TO n', '    PRINT a$;" ";i;" ";fib(i)', '  NEXT', 'ENDPROC',
          'x=$10+%11', 'WHILE x>17', '  x=x-1', 'WEND', 'TRY', '  show "fib",x-12', 'CATCH', '  PRINT "err ";ERR', '>ENDTRY']
case('LIST indents and spacing', PROG, 'LIST', LISTED)
case('demo program', PROG, 'RUN', ['fib 1 1', 'fib 2 1', 'fib 3 2', 'fib 4 3', 'fib 5 5'])

b = Basic(); res = {}; fails = []
for name, prog, cmd, want in T:
    try:
        rows = b.run(prog, cmd)
        got = rows[1:]
    except Exception as e:
        got = ['EXC ' + str(e)]; b = Basic()
    ok = got == want; res[name] = ok
    print('%-28s %s' % (name, 'ok' if ok else 'FAIL %r -> %r' % (want, got)))
    if not ok: fails.append(name)
# RST $28 runs OpticOS's maths byte-code (v0.8): END_ at once returns after it
s = b.s; b.line('CLS'); s.load(0x7000, b'\xef\xe0\x3e\x2a\xc9')    # rst $28: END_: ld a,42: ret
r = s.call(0x7000, ret=0x7100, SP=0x7200, limit=1_000_000)
s.setregs(PC=SYM['console'])
ok = r['PC'] == 0x7100 and (r['AF'] >> 8) == 42; res['RST $28 runs byte-code'] = ok
print('%-28s %s' % ('RST $28 runs byte-code', 'ok' if ok else 'FAIL %r' % r))
if not ok: fails.append('RST $28')
# a long-running loop: time per iteration
b.line('NEW'); b.enter(['FOR i=1 TO 1000: a=a+i: NEXT', 'PRINT a'])
t0 = s.regs() and __import__('rig').lib.z_tstates(); b.line('RUN'); t1 = __import__('rig').lib.z_tstates()
res['FOR loop T-states per iteration'] = (t1 - t0) // 1000
print('FOR 1000 iterations: %d T-states each' % ((t1 - t0) // 1000))
b.run(PROG, 'RUN'); b.s.image().save(os.path.join(ROOT, 'docs/phase3/rig_demo.png'))
json.dump(dict(cases=res, failures=fails), open(os.path.join(ROOT, 'build/test_phase3.json'), 'w'), indent=1)
print('\n%d/%d passed' % (len(T) + 1 - len(fails), len(T) + 1))
sys.exit(1 if fails else 0)
