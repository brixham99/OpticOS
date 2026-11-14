#!/usr/bin/env python3
"""Phase 2 maths tests for OpticOS in the headless rig.

  python3 tools/rig/test_maths.py [--n 2000] [--seed 1]

Every routine is run on the Z80 core against mpmath references (200-bit).
Errors are in ULPs of the 32-bit mantissa of the correctly rounded result
(ulp(x) = 2^(e-32) for x in [2^(e-1), 2^e)); for SIN/COS/TAN near their
zeros and LN near 1 the absolute error is also given, in units of 2^-32.
Writes build/maths_results.json and build/maths_results.md.
"""
import os, sys, json, random, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mlib import *
N = int(sys.argv[sys.argv.index('--n') + 1]) if '--n' in sys.argv else 2000
random.seed(int(sys.argv[sys.argv.index('--seed') + 1]) if '--seed' in sys.argv else 1)
m = M()
OUT = os.path.join(ROOT, 'build')
results, fails = {}, []

def rflt(lo=-30, hi=30):
    """Random exact 5-byte float with exponent 2^lo..2^hi, random sign."""
    mi = random.getrandbits(31) | 1 << 31
    v = mp.ldexp(mp.mpf(mi), random.randint(lo, hi) - 32)
    return -v if random.random() < .5 else v
def rint(lim=65535): return mp.mpf(random.randint(-lim, lim))
def rnd_in(a, b):
    """Random representable value uniform in [a, b)."""
    return decode(encode(mp.mpf(a) + (mp.mpf(b) - a) * random.random()))

class Stat:
    def __init__(s, name):
        s.name, s.n, s.maxu, s.sumu, s.maxabs, s.ts, s.bad, s.worst = name, 0, 0, 0, 0, [], 0, None
    def add(s, x, got, ref, t, absmode=False):
        s.n += 1; s.ts.append(t)
        err = abs(got - ref)
        u = err / ulp(ref) if ref != 0 else (0 if err == 0 else mp.inf)
        a = err * 2**32
        if a > s.maxabs: s.maxabs = a
        if absmode: u = min(u, a)
        if u > s.maxu: s.maxu, s.worst = u, (x, got, ref)
        s.sumu += u
    def row(s):
        return dict(op=s.name, n=s.n, max_ulp=float(s.maxu), mean_ulp=float(s.sumu / max(s.n, 1)),
                    max_abs_2m32=float(s.maxabs), t_min=min(s.ts), t_mean=int(statistics.mean(s.ts)),
                    t_max=max(s.ts), failures=s.bad,
                    worst=None if s.worst is None else [mp.nstr(v, 12) for v in s.worst])

def fail(name, msg):
    if len(fails) < 200: fails.append('%s: %s' % (name, msg))

def canon_ok(b, v):
    return (b[0] == 0) == (v == int(v) and abs(v) <= 65535)

# ------------------------------------------------------------ binary ops
EDGE = [0, 1, -1, 2, 0.5, -0.5, 65535, -65535, 65536, -65536, 32767, 32768, -32768, 255, 256,
        mp.mpf(1) / 3, mp.pi, -mp.e, mp.mpf(2)**-100, mp.mpf(2)**100, mp.mpf(10)**30, 1e-30,
        65535.5, -65535.5, 0.25, 3, -7, 100000, 1e9]
EDGE = [decode(encode(x)) for x in EDGE]
OPS = {'fp_add': lambda a, b: a + b, 'fp_sub': lambda a, b: a - b,
       'fp_mul': lambda a, b: a * b, 'fp_div': lambda a, b: a / b}
BIG = mp.ldexp(1, 127)
def gen2():
    pairs = [(a, b) for a in EDGE for b in EDGE]
    for _ in range(N):
        k = random.random()
        if k < .25: pairs.append((rint(), rint()))
        elif k < .35: pairs.append((rint(255), rint(255)))
        elif k < .45:
            a = rflt(); pairs.append((a, decode(encode(a * (1 + mp.ldexp(random.randint(-40, 40), -30))))))
        else: pairs.append((rflt(), rflt()))
    return pairs
for op, f in OPS.items():
    st = Stat(op)
    for a, b in gen2():
        got, e, t = m.bin(op, a, b)
        if op == 'fp_div' and b == 0:
            if e != 5: st.bad += 1; fail(op, '%s/0 gave error %r' % (a, e))
            continue
        ref = f(a, b)
        if abs(ref) >= BIG * (1 - mp.ldexp(1, -33)):
            if e != 6: st.bad += 1; fail(op, '%s,%s overflow gave %r' % (a, b, e))
            continue
        if abs(ref) < mp.ldexp(1, -129):        # underflow to zero allowed
            if e is None and decode(got) in (0,) or e is None: continue
        if e is not None: st.bad += 1; fail(op, '%s,%s error %r' % (a, b, e)); continue
        g = decode(got)
        if not canon_ok(got, g): st.bad += 1; fail(op, '%s,%s non-canonical %s' % (a, b, got.hex()))
        st.add((a, b), g, ref, t)
    results[op] = st.row()

# power: integer and real exponents
st = Stat('fp_pow')
cases = [(rnd_in(-4, 4), mp.mpf(random.randint(-12, 12))) for _ in range(N // 2)]
cases += [(rnd_in(0.01, 100), rnd_in(-8, 8)) for _ in range(N // 2)]
cases += [(2, 0.5), (0, 0), (0, 3), (10, 9), (2, 16), (2, -1), (-2, 3), (1.5, 2)]
for a, b in cases:
    a = decode(encode(a)); b = decode(encode(b))
    got, e, t = m.bin('fp_pow', a, b)
    if a == 0 and b < 0: continue
    if a == 0 and b == 0: ref = mp.mpf(1)
    else: ref = mp.power(a, b)
    if e is not None: st.bad += 1; fail('fp_pow', '%s^%s error %r' % (a, b, e)); continue
    st.add((a, b), decode(got), ref, t)
results['fp_pow'] = st.row()

# compare
st = Stat('fp_cmp'); bad = 0
for a, b in gen2():
    got, e, t = m.bin('fp_cmp', a, b)
    r = m.s.regs()['AF'] >> 8
    exp = 0xFF if a < b else (0 if a == b else 1)
    if r != exp: st.bad += 1; fail('fp_cmp', '%s ? %s gave %02x' % (a, b, r))
    st.n += 1; st.ts.append(t)
results['fp_cmp'] = st.row()

# ------------------------------------------------------------ unary functions
def un_test(name, ref, gen, absmode=False, errdom=None, edge=()):
    st = Stat(name)
    xs = [decode(encode(x)) for x in edge] + [gen() for _ in range(N)]
    for x in xs:
        got, e, t = m.un(name, x)
        if errdom and errdom(x):
            if e != 11: st.bad += 1; fail(name, '%s should give ERR_ARG, gave %r' % (x, e))
            continue
        r = ref(x)
        if abs(r) >= BIG:
            if e != 6: st.bad += 1; fail(name, '%s overflow gave %r' % (x, e))
            continue
        if e is not None: st.bad += 1; fail(name, '%s error %r' % (mp.nstr(x, 12), e)); continue
        g = decode(got)
        if not canon_ok(got, g): st.bad += 1; fail(name, '%s non-canonical %s' % (x, got.hex()))
        if abs(r) < mp.ldexp(1, -128): r = mp.mpf(0) if abs(g) < mp.ldexp(1, -127) else r
        st.add(x, g, r, t, absmode)
    results[name] = st.row()

def mix(*gens): return lambda: random.choice(gens)()
un_test('fp_neg', lambda x: -x, mix(rflt, rint), edge=EDGE)
un_test('fp_abs', abs, mix(rflt, rint), edge=EDGE)
un_test('fp_sgn', mp.sign, mix(rflt, rint), edge=EDGE)
un_test('fp_int', mp.floor, mix(lambda: rflt(-5, 40), rint, lambda: rnd_in(-70000, 70000)), edge=EDGE)
un_test('fp_sqr', mp.sqrt, mix(lambda: abs(rflt(-60, 60)), lambda: abs(rint())),
        errdom=lambda x: x < 0, edge=[0, 1, 2, 4, 0.25, 65535, 1e30, 1e-30, -1])
TRIG = mix(lambda: rnd_in(-7, 7), lambda: rnd_in(-1000, 1000), lambda: rflt(-20, 2), lambda: rnd_in(-100000, 100000))
TE = [0, mp.pi / 2, mp.pi, -mp.pi, 2 * mp.pi, 1, -1, 1e-10, 100, 1000]
un_test('fp_sin', mp.sin, TRIG, absmode=True, edge=TE)
un_test('fp_cos', mp.cos, TRIG, absmode=True, edge=TE)
un_test('fp_tan', mp.tan, TRIG, absmode=True, edge=[0, 1, -1, 1e-10, 0.785398, 1.5, 100])
un_test('fp_atn', mp.atan, mix(lambda: rflt(-30, 30), lambda: rnd_in(-3, 3), rint),
        edge=[0, 1, -1, 1e-20, 1e20, mp.sqrt(3), 2 - mp.sqrt(3), 65535])
un_test('fp_exp', mp.exp, mix(lambda: rnd_in(-88, 88), lambda: rnd_in(-1, 1), lambda: rflt(-30, 0)),
        edge=[0, 1, -1, 88, -88, 88.7, 89, -89.5, 1e-10, 10])
POS = mix(lambda: abs(rflt(-60, 60)), lambda: rnd_in(0.5, 2), lambda: mp.mpf(random.randint(1, 65535)))
un_test('fp_ln', mp.ln, POS, absmode=True, errdom=lambda x: x <= 0,
        edge=[1, 2, 0.5, mp.e, 10, 65535, 1e30, 1e-30, 1.0000001, 0, -1])
un_test('fp_log', mp.log10, POS, absmode=True, errdom=lambda x: x <= 0,
        edge=[1, 10, 100, 1000, 1e9, 0.1, 1e-5, 2, 0])

# ------------------------------------------------------------ integer conversion
st = Stat('fp_set_int')
for v in [0, 1, -1, 32767, -32768, 255, -256] + [random.randint(-32768, 32767) for _ in range(N)]:
    r, e, t = m.run('fp_set_int', HL=A, DE=v & 0xFFFF)
    g = decode(m.s.block(A, 5))
    if g != v or m.s.peek(A) != 0: st.bad += 1; fail('fp_set_int', '%d -> %s' % (v, m.s.block(A, 5).hex()))
    st.n += 1; st.ts.append(t)
results['fp_set_int'] = st.row()
st = Stat('fp_get_int')
for x in EDGE + [rnd_in(-70000, 70000) for _ in range(N)] + [rint() for _ in range(N // 4)]:
    m.s.load(A, encode(x)); r, e, t = m.run('fp_get_int', HL=A)
    ex = int(mp.floor(x + mp.mpf(0.5))) if x >= 0 else -int(mp.floor(-x + mp.mpf(0.5)))
    cf = r['AF'] & 1
    if abs(ex) > 65535:
        if not cf: st.bad += 1; fail('fp_get_int', '%s no carry' % x)
    else:
        de = r['DE']
        if cf or de != ex & 0xFFFF: st.bad += 1; fail('fp_get_int', '%s -> %04x cf %d (want %d)' % (x, de, cf, ex))
    st.n += 1; st.ts.append(t)
results['fp_get_int'] = st.row()

# ------------------------------------------------------------ number -> string
def ref_str(x):
    """The documented format: 9 significant digits rounded, trailing zeros
    stripped, fixed point for 1e-5 <= |x| < 1e9, else d.ddddE+n."""
    if x == 0: return '0'
    s = '-' if x < 0 else ''; x = abs(x)
    e = int(mp.floor(mp.log10(x)))
    d = int(mp.nint(x / mp.mpf(10) ** (e - 8)))
    if d >= 10**9: d //= 10; e += 1
    if d < 10**8: d = int(mp.nint(x / mp.mpf(10) ** (e - 9))); e -= 1
    ds = str(d).rstrip('0') or '0'
    if -5 <= e <= 8:
        if e >= 0:
            ip = ds[:e + 1].ljust(e + 1, '0'); fp = ds[e + 1:]
            return s + ip + ('.' + fp if fp else '')
        return s + '0.' + '0' * (-e - 1) + ds
    return s + ds[0] + ('.' + ds[1:] if len(ds) > 1 else '') + 'E' + ('-' if e < 0 else '+') + str(abs(e))
def strval(x):
    global m
    m.s.load(A, encode(x))
    try: r, e, t = m.run('fp_str', HL=A, limit=2_000_000)
    except TimeoutError:
        m = M(); return '<hang>', 'hang', 0
    n = r['BC'] >> 8; return m.s.block(r['HL'], n).decode('latin-1'), e, t
st = Stat('fp_str'); exact = 0; digit_off = 0
xs = [decode(encode(x)) for x in EDGE + [0.1, 1e-5, 9.99999e-6, 123456789, 999999999, 1e10, 1e-10, 1e38, -1e-38, 0.000123]]
xs += [rflt(-100, 100) for _ in range(N)] + [rint() for _ in range(N // 4)] + [rnd_in(-1000, 1000) for _ in range(N // 4)]
for x in xs:
    s_, e, t = strval(x)
    if e is not None: st.bad += 1; fail('fp_str', '%s error %r' % (x, e)); continue
    want = ref_str(x)
    st.n += 1; st.ts.append(t)
    if s_ == want: exact += 1; continue
    try: gv = mp.mpf(s_)
    except Exception: st.bad += 1; fail('fp_str', '%s -> %r unparsable' % (x, s_)); continue
    wv = mp.mpf(want)
    if abs(gv - wv) > abs(wv) * mp.mpf('1.1e-8') or (x == int(x) and abs(x) <= 65535):
        st.bad += 1; fail('fp_str', '%s -> %r want %r' % (mp.nstr(x, 12), s_, want))
    else: digit_off += 1
r_ = st.row(); r_.update(exact=exact, last_digit_off=digit_off); results['fp_str'] = r_
# decimals of up to 8 significant digits must print exactly as written
nice_ok, nice_n, nice_bad = 0, 0, []
for _ in range(N):
    d = random.randint(1, 99999999); e = random.randint(-30, 30)
    want = ref_str(mp.mpf(d) * mp.mpf(10) ** e)
    x = decode(encode(mp.mpf(want)))
    s_, e_, t = strval(x); nice_n += 1
    if s_ == want: nice_ok += 1
    elif len(nice_bad) < 8: nice_bad.append((want, s_))
results['nice'] = dict(op='decimals of <= 8 digits print as written', n=nice_n, ok=nice_ok, examples=nice_bad)

# ------------------------------------------------------------ string -> number
st = Stat('fp_val')
texts = ['0', '1', '12', '1.5', '.5', '3E8', '2.5e-3', '65535', '65536', '1E10', '123456789012',
         '0.000001', '1e38', '3.14159265358979', '1.', '7e+2']
for _ in range(N):
    k = random.random()
    if k < .3: texts.append(str(random.randint(0, 99999)))
    elif k < .7: texts.append(mp.nstr(abs(rflt(-60, 60)), random.randint(1, 11)).replace('e', random.choice('eE')))
    else: texts.append('%d.%0*d' % (random.randint(0, 9999), random.randint(1, 6), random.randint(0, 999999)))
for tx in texts:
    m.s.load(TXT, tx.encode() + b'\r')
    r, e, t = m.run('fp_val', HL=TXT, DE=A)
    ref = mp.mpf(tx.rstrip('.') if tx.endswith('.') else tx)
    if abs(ref) >= BIG:
        if e != 6: st.bad += 1; fail('fp_val', '%s gave %r' % (tx, e))
        continue
    if e is not None or r['AF'] & 1: st.bad += 1; fail('fp_val', '%r error %r' % (tx, e)); continue
    if r['HL'] != TXT + len(tx): st.bad += 1; fail('fp_val', '%r stopped at +%d' % (tx, r['HL'] - TXT))
    g = m.s.block(A, 5); gv = decode(g)
    if not canon_ok(g, gv): st.bad += 1; fail('fp_val', '%r non-canonical' % tx)
    st.add(tx, gv, ref, t)
results['fp_val'] = st.row()

# round trip VAL(STR$ x) for 9-digit decimals
rt_ok = rt4 = 0
for _ in range(N // 4):
    x = rnd_in(-1e6, 1e6)
    s_, e, t = strval(x)
    m.s.load(TXT, s_.lstrip('-').encode() + b'\r'); m.run('fp_val', HL=TXT, DE=B)
    g = decode(m.s.block(B, 5)) * (-1 if s_.startswith('-') else 1)
    if abs(g - x) <= ulp(x): rt_ok += 1
    if abs(g - x) <= 4 * ulp(x): rt4 += 1
results['roundtrip'] = dict(op='VAL(STR$ x) within 1 ulp', n=N // 4, ok=rt_ok, ok4=rt4)

# ------------------------------------------------------------ RND
vals, ts = [], []
for _ in range(N):
    r, e, t = m.run('fp_rnd', HL=A); v = decode(m.s.block(A, 5)); vals.append(v); ts.append(t)
okr = all(0 <= v < 1 for v in vals)
mean = float(sum(vals) / len(vals)); buckets = [0] * 10
for v in vals: buckets[int(v * 10)] += 1
chi = sum((b - len(vals) / 10) ** 2 / (len(vals) / 10) for b in buckets)
m.run('fp_randomize', DE=1234); a1 = [m.run('fp_rnd', HL=A) and m.s.block(A, 5) for _ in range(5)]
m.run('fp_randomize', DE=1234); a2 = [m.run('fp_rnd', HL=A) and m.s.block(A, 5) for _ in range(5)]
results['fp_rnd'] = dict(op='fp_rnd', n=N, in_range=okr, mean=mean, chi2_10bins=chi, repeatable=a1 == a2,
                         t_min=min(ts), t_mean=int(statistics.mean(ts)), t_max=max(ts), failures=0 if okr and a1 == a2 and chi < 30 else 1)
if results['fp_rnd']['failures']: fail('fp_rnd', str(results['fp_rnd']))

# ------------------------------------------------------------ console PRINT
FONT = open(os.path.join(ROOT, 'font/font4x8.bin'), 'rb').read()
SHOTS = os.path.join(ROOT, 'docs/phase2'); os.makedirs(SHOTS, exist_ok=True)
CON = [('PRINT "Hello, World!"', ['Hello, World!']),
       ('PRINT 2+2, SQR 2, "Hi";"!"', ['4               1.41421356      Hi!']),
       ('? 1/3;" ";PI;" ";-2^2', ['0.333333333 3.14159265 -4']),
       ('? (1+2)*3, 10/4, 7-10, 2^10', ['9               2.5             -3              1024']),
       ('? SIN(PI/6), COS 0, ATN 1*4, EXP 1', ['0.5             1               3.14159265      2.71828183']),
       ('print int -2.5;" ";abs -3;" ";sgn -9;" ";ln 10;" ";1e-5,1e9', ['-3 3 -1 2.30258509 0.00001      1E+9']),
       ('? "say ""hi""";', ['say "hi"']),
       ('? 1/0', ['Division by zero']), ('? 1E38*10', ['Overflow']),
       ('? SQR -1', ['Bad argument']), ('? 2+', ['Syntax error']), ('foo', ['No such PROC or FN'])]
con = {}
s2 = Spectrum(ROM); s2.frame(200)
def screen(sp): return [r.rstrip('\x7f').rstrip() for r in sp.text_rows(FONT)]
for i, (line, want) in enumerate(CON):
    if i == 7:
        s2.image().save(os.path.join(SHOTS, 'rig_hello.png'))
        s2.type('CLS\n'); s2.frame(5)
        ok = screen(s2)[0] == ']'; con['CLS clears and prompts at the top'] = ok
        if not ok: fail('console', 'CLS: %r' % screen(s2)[:2])
    s2.type(line + '\n'); s2.frame(5)
    rows = screen(s2); r = rows.index('] ' + line) if ('] ' + line) in rows else -1
    got = rows[r + 1:r + 1 + len(want)] if r >= 0 else None
    ok = got == want and rows[r + 1 + len(want)] == ']'
    con[line] = ok
    if not ok: fail('console', '%r -> %r' % (line, got))
s2.image().save(os.path.join(SHOTS, 'rig_errors.png'))
results['console'] = dict(op='console PRINT/CLS', n=len(con), ok=sum(con.values()), cases=con)

# ------------------------------------------------------------ report
json.dump(dict(n=N, results=results, failures=fails), open(os.path.join(OUT, 'maths_results.json'), 'w'), indent=1)
md = ['| Op | Cases | Max ulp | Mean ulp | Max abs (2^-32) | T min | T mean | T max | Fail |', '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
for k, r in results.items():
    if 'max_ulp' in r:
        md.append('| %s | %d | %.3f | %.3f | %.3f | %d | %d | %d | %d |' % (k, r['n'], r['max_ulp'], r['mean_ulp'], r['max_abs_2m32'], r['t_min'], r['t_mean'], r['t_max'], r['failures']))
    elif 't_min' in r:
        md.append('| %s | %d | - | - | - | %d | %d | %d | %d |' % (k, r['n'], r['t_min'], r['t_mean'], r['t_max'], r['failures']))
md.append('')
r = results['fp_str']; md.append('fp_str: %d/%d exactly match the reference format; %d differ by one in the 9th digit.' % (r['exact'], r['n'], r['last_digit_off']))
r = results['nice']; md.append('Decimals of up to 8 significant digits (1e-30..1e38) print exactly as written: %d/%d.' % (r['ok'], r['n']))
r = results['roundtrip']; md.append('VAL(STR$ x) (9 digits cannot hold 32 bits exactly): %d/%d come back within 1 ulp, %d/%d within 4 ulp.' % (r['ok'], r['n'], r['ok4'], r['n']))
r = results['console']; md.append('Console PRINT / ? / CLS / errors: %d/%d lines as expected.' % (r['ok'], r['n']))
r = results['fp_rnd']; md.append('RND: %d values all in [0,1): %s; mean %.4f; chi-square (10 bins, 9 dof) %.2f; RANDOMIZE n repeatable: %s.' % (r['n'], r['in_range'], r['mean'], r['chi2_10bins'], r['repeatable']))
open(os.path.join(OUT, 'maths_results.md'), 'w').write('\n'.join(md) + '\n')
print('\n'.join(md))
print('\n%d failure(s)' % len(fails)); print('\n'.join(fails[:60]))
sys.exit(1 if fails else 0)
