#!/usr/bin/env python3
# test_phase4.py - the phase 4 line editor in the rig, driven by real key
# presses: AUTO entry, the LIST marker, cursor up/down, EDIT, DELETE,
# left/right insert, delete and insert lines, long lines.
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
from p3lib import Basic, SYM, ROOT
b = Basic(); s = b.s; res = {}
UP, DOWN, LEFT, RIGHT, EDIT, DEL = '7', '6', '5', '8', '1', '0'
def caps(k, n=1):
    for _ in range(n): s.press(['^', k]); s.frame(3)
def key_line(text): s.type(text); s.frame(2)
def enter(): s.press(['\n']); s.frame(30)
def rows(): return [r for r in b.screen() if r != '']
def prog_list():
    b.cls(); b.line('LIST'); r = rows(); return [x for x in r[1:] if x != ']']
def check(name, got, want):
    ok = got == want; res[name] = ok
    print('%-34s %s' % (name, 'ok' if ok else 'FAIL %r -> %r' % (want, got)))
b.line('NEW')
# typed program entry: AUTO, three lines, empty line
key_line('AUTO'); enter()
for t in ['PRINT "one"', 'PRINT "two"', 'PRINT "three"']: key_line(t); enter()
enter()
check('AUTO entry, marker on last line', prog_list(), ['PRINT "one"', 'PRINT "two"', '>PRINT "three"'])
check('prompt back to ] after AUTO', rows()[-1], ']')
caps(UP)
r = rows(); check('cursor up relists with marker', r[:3], ['PRINT "one"', '>PRINT "two"', 'PRINT "three"'])
caps(EDIT)
check('EDIT shows the line', rows()[-1], '* PRINT "two"')
caps(LEFT, 1); key_line('!'); enter()      # PRINT "two!"... cursor was at the end
check('EDIT + insert replaces line', prog_list(), ['PRINT "one"', '>PRINT "two!"', 'PRINT "three"'])
caps(EDIT); caps(EDIT); enter()
check('EDIT EDIT ENTER deletes line', prog_list(), ['>PRINT "one"', 'PRINT "three"'])
key_line('AUTO'); enter(); key_line('PRINT "mid"'); enter(); enter()
check('AUTO inserts after marker', prog_list(), ['PRINT "one"', '>PRINT "mid"', 'PRINT "three"'])
caps(UP); caps(UP)                         # above the first line
key_line('AUTO'); enter(); key_line('CLS'); enter(); enter()
check('insert at the top', prog_list(), ['>CLS', 'PRINT "one"', 'PRINT "mid"', 'PRINT "three"'])
caps(DOWN); caps(DOWN); caps(DOWN); caps(DOWN)
check('cursor down stops at the end', prog_list()[-1], '>PRINT "three"')
b.line('CLS'); key_line('PRINT 1234'); caps(LEFT, 2); caps(DEL); caps(RIGHT); key_line('9'); enter()
r = rows(); check('left, DELETE, right, insert', r[-2], '1394')   # PRINT 1234 -> PRINT 1394
b.line('CLS'); long = 'PRINT "' + 'abcdefghij' * 11 + '"'
key_line(long); enter(); r = rows()
check('126-char line, two rows', (len(long), r[-2]), (len(long), ('abcdefghij' * 11)[-46:]))
b.run(['PRINT 1', 'PRINT 1/0', 'PRINT 3'], 'RUN')
check('error line becomes current', prog_list(), ['PRINT 1', '>PRINT 1/0', 'PRINT 3'])
check('RUN still works after edits', b.run(['PRINT 6*7'], 'RUN')[1:], ['42'])
s.image().save(os.path.join(ROOT, 'docs/phase4/rig_editor.png'))
fails = [k for k, v in res.items() if not v]
json.dump(dict(cases=res, failures=fails), open(os.path.join(ROOT, 'build/test_phase4.json'), 'w'), indent=1)
print('\n%d/%d passed' % (len(res) - len(fails), len(res)))
sys.exit(1 if fails else 0)
