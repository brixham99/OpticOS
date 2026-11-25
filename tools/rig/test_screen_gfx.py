#!/usr/bin/env python3
"""Unit tests for SCREEN 1/2 DRAW (Bresenham), BOX and CIRCLE, plus a
framebuffer comparison of the Union Flag against a Python-rendered reference.

These call the extension ROM's lineto / boxfill / circ / plot_cl / render0 in
the 48K rig: bank 7's framebuffer and lists sit at the same addresses, and the
routines do not page while drawing.

  python3 tools/rig/test_screen_gfx.py
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import Spectrum

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
EXTROM = os.path.join(ROOT, 'build/opticos128ext.rom')
SHOTS = os.path.join(ROOT, 'docs/screenmodes')
SYM = {}
for line in open(os.path.join(ROOT, 'build/opticos128ext.sym')):
    m = re.match(r'(\w+)\s+EQU\s+0?([0-9A-F]+)H', line)
    if m:
        SYM[m.group(1)] = int(m.group(2), 16)

SMODE, COORDS = 0x5CA0, 0x5C7D
LN_X0, LN_X1, BX_W, BX_H = 0x5CA1, 0x5CA3, 0x5CA5, 0x5CA6
FBP, DFLP = 0xDC00, 0xE800
LIST0, LIST1, VARS = 0xEB00, 0xF200, 0xF900
lp0, lp1, pcol, modev = VARS, VARS + 2, VARS + 6, VARS + 9

results = []
def check(name, ok, detail=''):
    results.append((name, bool(ok), detail))
    print('%-56s %s  %s' % (name, 'PASS' if ok else 'FAIL', detail))

def pal(c):
    """Spectrum colour 0-15 as RGB (bright for 8-15, black stays black)."""
    def ch(bit):
        if not (c & bit):
            return 0
        return 255 if (c & 8) else 215
    return (ch(2), ch(4), ch(1))

# ---------------------------------------------------------------------------
# framebuffer helpers
# ---------------------------------------------------------------------------
def limits(md):
    return (64, 48) if md == 1 else (32, 24)

def ytotop(md, y):
    return (47 if md == 1 else 23) - y

def pix_addr(md, x, row):
    if md == 2:
        return ((0xDC + 4 * (row >> 3)) << 8) | (((row & 7) << 5) | x)
    low = (((row >> 1) & 7) << 5) | (x >> 1)
    page = 0xDC + 4 * (row >> 4) + 2 * (row & 1) + (x & 1)
    return (page << 8) | low

def fb_get(s, md):
    w, h = limits(md)
    out = [[0] * w for _ in range(h)]
    for row in range(h):
        for x in range(w):
            out[row][x] = s.peek(pix_addr(md, x, row))
    return out

def fb_counts(fb, x0, y0, x1, y1):
    """Colour histogram in the inclusive pixel rectangle (origin top-left)."""
    from collections import Counter
    c = Counter()
    for row in fb[y0:y1 + 1]:
        for v in row[x0:x1 + 1]:
            c[v] += 1
    return c

# ---------------------------------------------------------------------------
# Python reference: Bresenham and box, in the same (x, row) space as the Z80
# ---------------------------------------------------------------------------
def bresenham(x0, y0, x1, y1, md):
    """Inclusive line from (x0,y0) to (x1,y1), bottom-left origin, clipped."""
    w, h = limits(md)
    r0, r1 = ytotop(md, y0), ytotop(md, y1)
    dx, dy = x1 - x0, r1 - r0
    adx, ady = abs(dx), abs(dy)
    sx = 0 if dx == 0 else (1 if dx > 0 else -1)
    sy = 0 if dy == 0 else (1 if dy > 0 else -1)
    if adx >= ady:
        major, minor, ms, ns = adx, ady, (sx, 0), (0, sy)
    else:
        major, minor, ms, ns = ady, adx, (0, sy), (sx, 0)
    x, r = x0, r0
    pts = []
    def add(xx, rr):
        if 0 <= xx < w and 0 <= rr < h:
            pts.append((xx, rr))
    add(x, r)
    if major == 0:
        return pts
    err = major // 2
    for _ in range(major):
        err += minor
        if err >= major:
            err -= major
            x += ns[0]; r += ns[1]
        x += ms[0]; r += ms[1]
        add(x, r)
    return pts

def box_pts(x, y, wdt, hgt, md):
    maxx, maxy = (63, 47) if md == 1 else (31, 23)
    if x > maxx:
        return []
    if y > maxy:
        return []
    x1 = x + wdt - 1
    if x1 > maxx or x1 < x:  # overflow or too wide
        x1 = maxx
    y1 = y + hgt - 1
    if y1 > maxy or y1 < y:
        y1 = maxy
    pts = []
    r0, r1 = ytotop(md, y1), ytotop(md, y)  # top row .. bottom row
    for row in range(r0, r1 + 1):
        for xx in range(x, x1 + 1):
            pts.append((xx, row))
    return pts

# ---------------------------------------------------------------------------
# Python-rendered Union Flag (same construction as flags128.bas flag())
# ---------------------------------------------------------------------------
def dband_pts(w, h, top, i0, i1, d0, d1, md):
    """Both saltire arms, rows i0..i1 from the top, span [xa+d0, xa+d1].

    If xa is odd the run is shifted left one pixel so mode-1 edges sit on
    the 2x2 attribute grid.
    """
    pts = []
    for i in range(i0, i1 + 1):
        y = top - i
        for xa in (2 * i, w - 1 - 2 * i):
            a, b = xa + d0, xa + d1
            if xa % 2:
                a -= 1
                b -= 1
            if a < 0: a = 0
            if b > w - 1: b = w - 1
            if a <= b:
                pts.extend(bresenham(a, y, b, y, md))
    return pts

def flag_offsets(h):
    """White / red span offsets, as in flags128.bas."""
    if h < 24:
        return dict(wd0=-3, wd1=4, rt0=-1, rt1=0, rb0=1, rb1=2)
    return dict(wd0=-6, wd1=7, rt0=-4, rt1=0, rb0=1, rb1=5)

def flag_cross(h):
    """White / red cross half-widths, as in flags128.bas."""
    return max(1, (h + 2) // 6), max(1, (h + 4) // 10)

def flag_fb(w, h, top, md):
    ww, hh = limits(md)
    fb = [[0] * ww for _ in range(hh)]
    def paint(pts, c):
        for x, r in pts:
            fb[r][x] = c
    bot = top - h + 1
    o = flag_offsets(h)
    m = h // 2
    paint(box_pts(0, bot, w, h, md), 1)             # blue field
    paint(dband_pts(w, h, top, 0, h - 1, o['wd0'], o['wd1'], md), 7)
    paint(dband_pts(w, h, top, 0, m - 1, o['rt0'], o['rt1'], md), 2)
    paint(dband_pts(w, h, top, m, h - 1, o['rb0'], o['rb1'], md), 2)
    cw, cr = flag_cross(h)
    paint(box_pts(w // 2 - cw, bot, 2 * cw, h, md), 7)
    paint(box_pts(0, bot + h // 2 - cw, w, 2 * cw, md), 7)
    paint(box_pts(w // 2 - cr, bot, 2 * cr, h, md), 2)
    paint(box_pts(0, bot + h // 2 - cr, w, 2 * cr, md), 2)
    return fb

def hi_res_flag(W=256, H=128, wd0=-6, wd1=7, rt0=-4, rt1=0, rb0=1, rb1=5, align=4):
    """High-res flag with the same offset saltire as flags128.bas.

    Offsets are in destination (chunky) pixels; they are scaled so a 256x128
    render downsamples onto a 64x32 or 32x16 grid with the same proportions.
    """
    pix = [[1] * W for _ in range(H)]
    sx = W / 64 if W else 1  # default: mode-1 scale (64 wide)
    # callers pass already-scaled offsets in dest pixels of this H,W:
    mid = H / 2
    for i in range(H):
        # slope 2 on a 2:1 flag
        for xa in (2 * i, W - 1 - 2 * i):
            def span(d0, d1, c, xa=xa, align=align):
                a = int(round(xa + d0))
                b = int(round(xa + d1))
                if xa % 2:
                    a -= align
                    b -= align
                if a < 0: a = 0
                if b > W - 1: b = W - 1
                if a <= b:
                    for x in range(a, b + 1):
                        pix[i][x] = c
            span(wd0, wd1, 7)
            if i < mid:
                span(rt0, rt1, 2)
            else:
                span(rb0, rb1, 2)
    cw, cr = max(1, H / 6), max(1, H / 10)
    mx, my = W / 2, H / 2
    for y in range(H):
        for x in range(W):
            if abs(x - (mx - 0.5)) < cw or abs((H - 1 - y) - (my - 0.5)) < cw:
                pix[y][x] = 7
            if abs(x - (mx - 0.5)) < cr or abs((H - 1 - y) - (my - 0.5)) < cr:
                pix[y][x] = 2
    return pix


def downsample(src, dw, dh):
    """Majority colour in each block (ties: first of 1, 2, 7, else mode)."""
    sh, sw = len(src), len(src[0])
    bx, by = sw / dw, sh / dh
    out = [[0] * dw for _ in range(dh)]
    for r in range(dh):
        for c in range(dw):
            x0, x1 = int(c * bx), int((c + 1) * bx)
            y0, y1 = int(r * by), int((r + 1) * by)
            hist = {0: 0, 1: 0, 2: 0, 7: 0}
            for y in range(y0, max(y1, y0 + 1)):
                for x in range(x0, max(x1, x0 + 1)):
                    hist[src[y][x]] = hist.get(src[y][x], 0) + 1
            # prefer chromatic colours if tied with black padding (shouldn't)
            out[r][c] = max(hist, key=lambda k: (hist[k], 1 if k else -1))
    return out

def fb_to_image(fb, cell=8, pad=8):
    from PIL import Image
    h, w = len(fb), len(fb[0])
    im = Image.new('RGB', (w * cell + 2 * pad, h * cell + 2 * pad), (0, 0, 0))
    px = im.load()
    for r in range(h):
        for c in range(w):
            col = pal(fb[r][c])
            for dy in range(cell):
                for dx in range(cell):
                    px[pad + c * cell + dx, pad + r * cell + dy] = col
    return im

def diffs(a, b):
    n = 0
    h, w = len(a), len(a[0])
    for r in range(h):
        for c in range(w):
            if a[r][c] != b[r][c]:
                n += 1
    return n

# ---------------------------------------------------------------------------
# Z80 harness
# ---------------------------------------------------------------------------
def machine():
    s = Spectrum(EXTROM)
    s.setregs(IFF1=0, IFF2=0, IM=1, I=0, SP=0x5FE0)
    return s

def setup(s, md, colour=7):
    s.poke(SMODE, md)
    s.poke(modev, md)
    s.poke(pcol, colour)
    s.load(FBP, bytes(3072))
    s.load(DFLP, bytes(768))
    s.poke(lp0, LIST0 & 255); s.poke(lp0 + 1, LIST0 >> 8)
    s.poke(lp1, LIST1 & 255); s.poke(lp1 + 1, LIST1 >> 8)

def zline(s, x0, y0, x1, y1, colour=None):
    if colour is not None:
        s.poke(pcol, colour)
    s.poke(LN_X0, x0); s.poke(LN_X0 + 1, y0)
    s.poke(LN_X1, x1); s.poke(LN_X1 + 1, y1)
    s.call(SYM['lineto'], IFF1=0, IFF2=0)

def zbox(s, x, y, wdt, hgt, colour=None):
    if colour is not None:
        s.poke(pcol, colour)
    s.poke(COORDS, x); s.poke(COORDS + 1, y)
    s.poke(BX_W, wdt); s.poke(BX_H, hgt)
    s.call(SYM['boxfill'], IFF1=0, IFF2=0, BC=(x << 8) | x, DE=(0 << 8) | y)

def midcircle(cx, cy, r, md):
    """Midpoint circle, bottom-left origin, clipped; points as (x, row)."""
    w, h = limits(md)
    pts = set()
    def add(x, y):
        if 0 <= x < w and 0 <= y < h:
            pts.add((x, ytotop(md, y)))
    if r == 0:
        add(cx, cy)
        return pts
    x, y = 0, r
    d = 3 - 2 * r
    while x <= y:
        for ox, oy in ((x, y), (-x, y), (x, -y), (-x, -y),
                       (y, x), (-y, x), (y, -x), (-y, -x)):
            add(cx + ox, cy + oy)
        if d > 0:
            y -= 1
            d += 4 * (x - y) + 10
        else:
            d += 4 * x + 6
        x += 1
    return pts

def zcirc(s, cx, cy, r, colour=None):
    if colour is not None:
        s.poke(pcol, colour)
    s.poke(LN_X0, cx); s.poke(LN_X0 + 1, cy)
    s.poke(BX_W, r)
    s.call(SYM['circ'], IFF1=0, IFF2=0)

def painted(s, md):
    """Set of (x, row) whose colour is not 0."""
    fb = fb_get(s, md)
    return {(x, r) for r, row in enumerate(fb) for x, v in enumerate(row) if v}

# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------
OCTANTS = [
    # name, x0, y0, x1, y1  (bottom-left origin, mode 1: 64x48)
    ('E  horizontal +dx',      10, 20, 40, 20),
    ('W  horizontal -dx',      40, 20, 10, 20),
    ('N  vertical +dy',        20, 5,  20, 30),
    ('S  vertical -dy',        20, 30, 20, 5),
    ('NE octant |dx|>|dy|',    5,  10, 40, 20),
    ('NE octant |dy|>|dx|',    5,  10, 20, 40),
    ('NW octant |dx|>|dy|',    40, 10, 5,  20),
    ('NW octant |dy|>|dx|',    20, 10, 5,  40),
    ('SE octant |dx|>|dy|',    5,  30, 40, 20),
    ('SE octant |dy|>|dx|',    5,  40, 20, 10),
    ('SW octant |dx|>|dy|',    40, 30, 5,  20),
    ('SW octant |dy|>|dx|',    20, 40, 5,  10),
    ('short +dx at high row',  0,  16, 12, 16),   # used to staircase (row>=len)
    ('single pixel',           15, 15, 15, 15),
]

def t_draw_octants():
    s = machine()
    for md in (1, 2):
        for name, x0, y0, x1, y1 in OCTANTS:
            # skip points that are off-mode-2
            w, h = limits(md)
            if max(x0, x1) >= w or max(y0, y1) >= h or min(x0, y0, x1, y1) < 0:
                if md == 2:
                    continue
            setup(s, md, 7)
            zline(s, x0, y0, x1, y1, 7)
            got = painted(s, md)
            want = set(bresenham(x0, y0, x1, y1, md))
            extra = got - want
            missing = want - got
            ok = got == want
            detail = ''
            if not ok:
                detail = 'extra=%s missing=%s got=%d want=%d' % (
                    sorted(extra)[:8], sorted(missing)[:8], len(got), len(want))
            check('DRAW md%d %s' % (md, name), ok, detail)

def t_draw_clip():
    # BASIC DRAW rejects a high byte, so endpoints are 0-255.  Clipping is
    # about x past the mode width and y past the mode height (the top).
    # Negative coordinates never reach lineto.
    s = machine()
    cases = [
        ('end off right',        50, 20, 80, 20, 1),
        ('start off right, -dx', 80, 20, 50, 20, 1),
        ('end off top',          20, 40, 20, 60, 1),
        ('start off top, -dy',   20, 60, 20, 40, 1),
        ('diagonal off right',   50, 10, 80, 25, 1),
        ('diagonal off top',     10, 40, 25, 60, 1),
        ('fully off to the right', 70, 10, 90, 20, 1),
        ('fully off above',      10, 50, 20, 70, 1),
        ('md2 end off right',    20, 10, 40, 10, 2),
        ('md2 end off top',      10, 20, 10, 30, 2),
        ('md2 diagonal clip',    24, 18, 40, 28, 2),
    ]
    for name, x0, y0, x1, y1, md in cases:
        setup(s, md, 7)
        zline(s, x0, y0, x1, y1, 7)
        got = painted(s, md)
        want = set(bresenham(x0, y0, x1, y1, md))
        ok = got == want
        check('DRAW clip %s' % name, ok,
              '' if ok else 'extra=%s missing=%s got=%d want=%d' % (
                  sorted(got - want)[:6], sorted(want - got)[:6],
                  len(got), len(want)))

def t_box_edges():
    s = machine()
    cases = [
        ('md1 full width',     1, 0, 16, 64, 32),
        ('md1 1x1 at origin',  1, 0, 0, 1, 1),
        ('md1 top-right cell', 1, 63, 47, 1, 1),
        ('md1 clips right',    1, 60, 20, 10, 4),
        ('md1 clips top',      1, 10, 44, 4, 10),
        ('md1 left column',    1, 0, 10, 1, 8),
        ('md1 bottom row',     1, 5, 0, 10, 1),
        ('md2 full width',     2, 0, 8, 32, 16),
        ('md2 clips right',    2, 28, 8, 8, 4),
        ('md2 1x1 top-right',  2, 31, 23, 1, 1),
        ('md2 off to the right', 2, 40, 8, 4, 4),
    ]
    for name, md, x, y, wdt, hgt in cases:
        setup(s, md, 2)
        zbox(s, x, y, wdt, hgt, 2)
        got = painted(s, md)
        want = set(box_pts(x, y, wdt, hgt, md))
        ok = got == want
        check('BOX %s' % name, ok,
              '' if ok else 'extra=%d missing=%d got=%d want=%d e.g. %s' % (
                  len(got - want), len(want - got), len(got), len(want),
                  sorted(got - want)[:6] or sorted(want - got)[:6]))

def t_box_no_wrap():
    """A full-width BOX must not spill a wrapped pixel at x=0 of another row."""
    s = machine()
    setup(s, 1, 1)
    zbox(s, 0, 16, 64, 32, 1)
    fb = fb_get(s, 1)
    spill = [(x, r) for r in range(48) for x in range(64)
             if fb[r][x] and not (0 <= x < 64 and 0 <= r < 32)]
    # flag sits at top=47, h=32 -> rows 0..31.  Anything in rows 32-47 is spill.
    check('BOX md1 full width stays in rows 0-31', spill == [],
          'spill %s' % spill[:8])
    n = sum(fb[r][x] == 1 for r in range(32) for x in range(64))
    check('BOX md1 full width is exactly 64x32', n == 64 * 32, 'n=%d' % n)

    setup(s, 2, 1)
    zbox(s, 0, 8, 32, 16, 1)
    fb = fb_get(s, 2)
    spill = [(x, r) for r in range(24) for x in range(32)
             if fb[r][x] and not (0 <= r < 16)]
    check('BOX md2 full width stays in rows 0-15', spill == [],
          'spill %s' % spill[:8])
    n = sum(fb[r][x] == 1 for r in range(16) for x in range(32))
    check('BOX md2 full width is exactly 32x16', n == 32 * 16, 'n=%d' % n)

def zflag(s, w, h, top, md):
    """Drive flag() through the Z80 primitives (integer endpoints)."""
    setup(s, md, 0)
    bot = top - h + 1
    zbox(s, 0, bot, w, h, 1)
    o = flag_offsets(h)
    m = h // 2
    def zdband(i0, i1, d0, d1, c):
        s.poke(pcol, c)
        for i in range(i0, i1 + 1):
            y = top - i
            for xa in (2 * i, w - 1 - 2 * i):
                a, b = xa + d0, xa + d1
                if xa % 2:
                    a -= 1
                    b -= 1
                if a < 0: a = 0
                if b > w - 1: b = w - 1
                if a <= b:
                    zline(s, a, y, b, y, c)
    zdband(0, h - 1, o['wd0'], o['wd1'], 7)
    zdband(0, m - 1, o['rt0'], o['rt1'], 2)
    zdband(m, h - 1, o['rb0'], o['rb1'], 2)
    cw, cr = flag_cross(h)
    zbox(s, w // 2 - cw, bot, 2 * cw, h, 7)
    zbox(s, 0, bot + h // 2 - cw, w, 2 * cw, 7)
    zbox(s, w // 2 - cr, bot, 2 * cr, h, 2)
    zbox(s, 0, bot + h // 2 - cr, w, 2 * cr, 2)

def counterchange_ok(fb, w, h):
    """Red is offset left in the top half, right in the bottom half, on both arms.

    This is the SCREEN 0 rule: at a given row, mean x of red in a white+red
    run is left of the run's centre at the top, and right of it at the bottom.
    """
    def side(row, x0, x1):
        cells = [(x, row[x]) for x in range(max(0, x0), min(len(row), x1 + 1))]
        reds = [x for x, c in cells if c == 2]
        whites = [x for x, c in cells if c == 7]
        if not reds or not whites:
            return None
        mid = (min(x for x, c in cells if c in (2, 7)) +
               max(x for x, c in cells if c in (2, 7))) / 2
        return sum(reds) / len(reds) - mid

    # sample a row in each arm, away from the cross and the very edge
    top_i, bot_i = max(2, h // 8), min(h - 3, h - h // 8)
    # fb rows are from the top of the mode; flag occupies rows 0..h-1
    issues = []
    for name, i, expect in (
        ('TL top \\', top_i, 'left'),
        ('TR top /', top_i, 'left'),
        ('BL bot /', bot_i, 'right'),
        ('BR bot \\', bot_i, 'right'),
    ):
        xa = (2 * i) if name.startswith('T') and '\\' in name or name.startswith('B') and '\\' in name else (w - 1 - 2 * i)
        # classify by the diagonal: \ is 2*i, / is w-1-2*i
        if '\\' in name:
            xa = 2 * i
        else:
            xa = w - 1 - 2 * i
        off = side(fb[i], xa - 6, xa + 6)
        if off is None:
            issues.append('%s: no red+white' % name)
        elif expect == 'left' and off >= 0:
            issues.append('%s: red offset %+0.2f, want left' % (name, off))
        elif expect == 'right' and off <= 0:
            issues.append('%s: red offset %+0.2f, want right' % (name, off))
    return (not issues, '; '.join(issues) if issues else 'left at top, right at bottom')

def quadrant_blue_ok(fb, w, h):
    """The four blue fields (between the saltire and the cross) have blue.

    The saltire itself occupies the literal corners, so we sample just
    above/below the horizontal bar, near the hoist and fly — those four
    pockets stay blue in this construction.
    """
    cw = max(1, h // 6)
    # flag occupies rows 0..h-1.  Horizontal white bar is centred, height 2*cw.
    mid = h // 2  # row of the geometric centre (from the top)
    # white bar covers rows mid-cw .. mid+cw-1 (approx; integer placement
    # follows bot + h//2 - cw in bottom-left space, which is the same).
    above = mid - cw - 2
    below = mid + cw + 1
    bw, bh = max(3, w // 16), 2
    left, right = 2, w - 2 - bw
    spots = [(above, left), (above, right), (below, left), (below, right)]
    out = []
    for r0, c0 in spots:
        nblue = sum(fb[r][c] == 1 for r in range(r0, r0 + bh)
                    for c in range(c0, c0 + bw))
        out.append(nblue)
    return out, bh * bw

def t_flag_reference():
    os.makedirs(SHOTS, exist_ok=True)
    s = machine()
    specs = [
        (1, 64, 32, 47, 'flag_ref_mode1.png', 'flag_got_mode1.png'),
        (2, 32, 16, 23, 'flag_ref_mode2.png', 'flag_got_mode2.png'),
    ]
    for md, w, h, top, refn, gotn in specs:
        want = flag_fb(w, h, top, md)
        zflag(s, w, h, top, md)
        got = fb_get(s, md)
        n = diffs(got, want)
        check('flag md%d framebuffer matches Python reference' % md,
              n == 0, '%d pixels differ' % n)
        # no ink outside the flag rectangle (rows 0..h-1, x 0..w-1)
        spill = [(x, r) for r in range(limits(md)[1]) for x in range(limits(md)[0])
                 if got[r][x] and (r >= h or x >= w)]
        check('flag md%d no pixels spill outside the flag' % md,
              spill == [], 'spill %s' % spill[:8])
        blues, area = quadrant_blue_ok(got, w, h)
        # each corner block should be mostly blue (saltire may clip a sliver)
        check('flag md%d blue field in all four corners' % md,
              all(b >= area // 3 for b in blues), 'blue counts %s / %d' % (blues, area))
        ok_cc, detail_cc = counterchange_ok(got, w, h)
        check('flag md%d saltire counterchange matches SCREEN 0' % md,
              ok_cc, detail_cc)
        # vertical thickness of the white+red band, away from the cross
        ths=[]
        mid_lo, mid_hi = h//2 - max(3, h//8), h//2 + max(3, h//8)
        for x in list(range(4, w//2-8)) + list(range(w//2+8, w-4)):
            y=0
            while y<h:
                if got[y][x] in (2,7):
                    y0=y
                    while y<h and got[y][x] in (2,7):
                        y+=1
                    if not (y0>=mid_lo and y-1<=mid_hi):
                        ths.append(y-y0)
                else:
                    y+=1
        if ths:
            med=sorted(ths)[len(ths)//2]
            expect=6 if md==1 else 3
            check('flag md%d saltire vertical thickness ~%d' % (md, expect),
                  med>=expect, 'median %d samples %s' % (med, ths[:8]))
        if md==1:
            n3=0
            for cy in range(0, h, 2):
                for cx in range(0, w, 2):
                    cols={got[cy+dy][cx+dx] for dy in range(2) for dx in range(2) if cy+dy<h and cx+dx<w}
                    cols.discard(0)
                    if len(cols)>=3:
                        n3+=1
            check('flag md1 no 3-colour 2x2 attribute cells', n3==0, 'n3=%d' % n3)
        # downsampled hi-res reference, same band widths as this mode
        # (mode 2 uses a 1-cell red in a 3-cell white band).
        if h < 24:
            # 8-cell white, 2-cell red, scaled 32 -> 256 (*8)
            hi_m = hi_res_flag(256, 128, wd0=-24, wd1=32, rt0=-8, rt1=0, rb0=8, rb1=16, align=8)
        else:
            # 14-pixel white, 5-pixel red, scaled 64 -> 256 (*4)
            hi_m = hi_res_flag(256, 128, wd0=-24, wd1=28, rt0=-16, rt1=0, rb0=4, rb1=20, align=4)
        canvas = [row[:] for row in hi_m] + [[0] * 256 for _ in range(192 - 128)]
        dw, dh = limits(md)
        ds = downsample(canvas, dw, dh)
        nd = diffs(got, ds)
        # not required to be pixel-identical (low-res scanlines vs majority
        # of a hi-res raster), but should be close — used as a sanity bound.
        # mode 1 is 64x32 (1/4 of 256x128); mode 2 is 32x16, where majority
        # sampling of the diagonals naturally diverges more from a scanline
        # raster, so allow a quarter of the canvas.
        bound = (dw * dh) // (8 if md == 1 else 4)
        check('flag md%d close to downsampled hi-res Union Flag' % md,
              nd <= bound, '%d / %d pixels differ (bound %d)' % (nd, dw * dh, bound))
        fb_to_image(want, cell=8 if md == 1 else 16).save(os.path.join(SHOTS, refn))
        fb_to_image(got,  cell=8 if md == 1 else 16).save(os.path.join(SHOTS, gotn))
        fb_to_image(ds,   cell=8 if md == 1 else 16).save(
            os.path.join(SHOTS, 'flag_downsample_mode%d.png' % md))

        # also render onto the Spectrum display and confirm it is a clean
        # 8x8 (md2) / 4x4 (md1, two pixels per 8x8 cell) grid: every cell's
        # 8 bitmap rows, where they have ink, are identical, and attributes
        # are consistent across the cell.
        s.poke(modev, md)
        s.load(0x4000, bytes(0x1800))   # CLS bitmap; SCREEN 2 is attr-only
        try:
            s.call(SYM['render0'], IFF1=0, IFF2=0, limit=20_000_000)
            grid_ok, detail = screen_is_cell_grid(s, md, h)
            check('flag md%d rendered screen is a clean cell grid' % md,
                  grid_ok, detail)
            nred, detail_r = screen_saltire_red(s, md, w, h)
            check('flag md%d rendered screen has a red saltire' % md,
                  nred > 0, detail_r)
        except Exception as e:
            check('flag md%d rendered screen is a clean cell grid' % md,
                  False, str(e))
            check('flag md%d rendered screen has a red saltire' % md,
                  False, str(e))

def screen_saltire_red(s, md, w, h):
    """Count red pixels on the diagonals, excluding the St George cross.

    This would have been silent if the BASIC listing drew the band in INK
    (white) after a one-pixel red PLOT: the framebuffer test calls lineto
    with an explicit colour, so it cannot catch that by itself.
    """
    cw = max(1, h // 6)
    # display file: mode 1 is 4x4 screen pixels per chunky pixel; mode 2 is 8x8
    red = 0
    mem = s.mem
    for sy in range(h * (4 if md == 1 else 8)):
        a = 0x4000 | ((sy & 0xC0) << 5) | ((sy & 7) << 8) | ((sy & 0x38) << 2)
        cy = sy >> 3
        for sx in range(w * (4 if md == 1 else 8)):
            cx = sx >> 3
            # skip the cross
            if md == 1:
                if abs((sx // 4) - w // 2) < cw: continue
                if abs((sy // 4) - h // 2) < cw: continue
            else:
                if abs(cx - w // 2) < cw: continue
                if abs(cy - h // 2) < cw: continue
            at = mem[0x5800 + cy * 32 + cx]
            ink, paper = at & 7, (at >> 3) & 7
            bit = (mem[a + cx] >> (7 - (sx & 7))) & 1
            col = ink if bit else paper
            if col == 2:
                red += 1
    return red, '%d red pixels on the diagonals' % red

def screen_is_cell_grid(s, md, flag_h):
    """Mode 2: each used cell is a flat 8x8 of one paper colour (no ink pixels).
    Mode 1: each cell is a 2x2 of 4x4 pixel blocks (the chunky pattern).
    Also: no coloured cells below the flag."""
    mem = s.mem
    # attributes
    spill_cells = []
    flag_rows = flag_h if md == 2 else (flag_h + 1) // 2  # 16 or 16 cells
    for cy in range(24):
        for cx in range(32):
            at = mem[0x5800 + cy * 32 + cx]
            if cy >= (16 if True else 0) and cy >= flag_rows:
                # below the flag: expect paper 0, no ink
                if at & 0x38:  # paper not black
                    spill_cells.append((cx, cy, at))
    if spill_cells:
        return False, 'attr spill below flag: %s' % spill_cells[:8]
    if md == 2:
        # bitmap in the flag area should be clear (attribute-only mode)
        ink = 0
        for y in range(flag_h * 8):
            a = 0x4000 | ((y & 0xC0) << 5) | ((y & 7) << 8) | ((y & 0x38) << 2)
            ink += sum(1 for x in range(32) if mem[a + x])
        if ink:
            return False, 'mode 2 has %d ink bytes; expected attribute-only' % ink
        # every on-flag cell is one of paper 0/1/2/7 (blue/red/white), 8x8
        bad = []
        for cy in range(flag_h):
            for cx in range(32):
                at = mem[0x5800 + cy * 32 + cx]
                paper = (at >> 3) & 7
                bright = bool(at & 0x40)
                inkc = at & 7
                if inkc != paper:
                    bad.append((cx, cy, at))
        if bad:
            return False, 'mode 2 attr ink!=paper: %s' % bad[:6]
        return True, '32x%d cells, attribute-only, no spill' % flag_h
    # mode 1: 2x2 chunky — in each cell, the four 4x4 corners may differ,
    # but within a 4x4 corner all pixels share a colour (pattern is $00,$0F,
    # $F0,$FF per 4-pixel nibble group, and all 8 bit-rows come in two
    # identical groups of 4).  A "smaller than 4x4" block would show as a
    # ragged bitmap.  We just check the 8 rows are 4+4 identical.
    ragged = 0
    for cy in range(flag_h // 2):
        for cx in range(32):
            rows = []
            for ry in range(8):
                y = cy * 8 + ry
                a = 0x4000 | ((y & 0xC0) << 5) | ((y & 7) << 8) | ((y & 0x38) << 2)
                rows.append(mem[a + cx])
            if rows[0] != rows[1] or rows[0] != rows[2] or rows[0] != rows[3]:
                ragged += 1
            if rows[4] != rows[5] or rows[4] != rows[6] or rows[4] != rows[7]:
                ragged += 1
    if ragged:
        return False, '%d ragged 4-row groups (not 4x4 chunky)' % ragged
    return True, '64x%d chunky, 4x4 cells clean, no spill' % flag_h

def t_circle():
    s = machine()
    cases = [
        # name, md, cx, cy, r
        ('md1 r=0 at centre',          1, 32, 24, 0),
        ('md1 r=1',                    1, 32, 24, 1),
        ('md1 r=5',                    1, 32, 24, 5),
        ('md1 r=10',                   1, 32, 24, 10),
        ('md1 r=23 near full height',  1, 32, 24, 23),
        ('md2 r=0 at centre',          2, 16, 12, 0),
        ('md2 r=1',                    2, 16, 12, 1),
        ('md2 r=6',                    2, 16, 12, 6),
        ('md2 r=11 near full height',  2, 16, 12, 11),
        ('md1 r=0 off the top-right',  1, 80, 60, 0),
        ('md1 clipped at origin',      1, 0,  0,  8),
        ('md1 clipped at top-right',   1, 63, 47, 8),
        ('md1 clipped at bottom-left', 1, 0,  0,  1),
        ('md2 clipped at origin',      2, 0,  0,  5),
        ('md2 clipped at top-right',   2, 31, 23, 5),
        ('md1 centre off, arc visible',1, 70, 24, 20),
        ('md2 centre off, arc visible',2, 40, 12, 16),
    ]
    for name, md, cx, cy, r in cases:
        setup(s, md, 7)
        zcirc(s, cx, cy, r, 7)
        got = painted(s, md)
        want = midcircle(cx, cy, r, md)
        extra, missing = got - want, want - got
        check('CIRCLE %s matches midpoint reference' % name,
              got == want,
              'extra %s missing %s n=%d want=%d' % (
                  list(extra)[:6], list(missing)[:6], len(got), len(want)))
    # r=0 on-screen is exactly one pixel
    setup(s, 1, 2)
    zcirc(s, 10, 10, 0, 2)
    fb = fb_get(s, 1)
    n = sum(1 for row in fb for v in row if v)
    check('CIRCLE r=0 paints exactly one pixel',
          n == 1 and fb[ytotop(1, 10)][10] == 2, 'n=%d' % n)
    # a clipped circle must not write outside the framebuffer
    setup(s, 1, 7)
    zcirc(s, 0, 0, 20, 7)
    w, h = limits(1)
    spill = [(x, r) for r, row in enumerate(fb_get(s, 1))
             for x, v in enumerate(row) if v and not (0 <= x < w and 0 <= r < h)]
    check('CIRCLE clipped at origin has no spill', spill == [], 'spill %s' % spill[:6])
    # eight-way symmetry for an in-bounds circle
    setup(s, 1, 7)
    zcirc(s, 32, 24, 12, 7)
    pts = painted(s, 1)
    def bl(x, row):
        return x, 47 - row
    bad = []
    for x, row in pts:
        cx, cy = bl(x, row)
        for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            ox, oy = cx - 32, cy - 24
            tx, ty = 32 + sx * ox, 24 + sy * oy
            tr = ytotop(1, ty)
            if (tx, tr) not in pts:
                bad.append((cx, cy, tx, ty))
    check('CIRCLE md1 r=12 is 4-way symmetric about the centre',
          bad == [], 'missing images %s' % bad[:6])

def main():
    t_draw_octants()
    t_draw_clip()
    t_box_edges()
    t_box_no_wrap()
    t_circle()
    t_flag_reference()
    nfail = sum(1 for _, ok, _ in results if not ok)
    print('\n%d tests, %d failed' % (len(results), nfail))
    return 0 if nfail == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
