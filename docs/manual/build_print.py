#!/usr/bin/env python3
"""Print edition of the manual (ring bound, printed double-sided), written to docs/manual/print/:

  OpticOS_Manual_A5_cover.pdf     one page, 154 x 216 mm: A5 plus 3 mm bleed on every edge (TrimBox set)
  OpticOS_Manual_A5_interior.pdf  exactly A5 (148 x 210 mm), no bleed, every page but the front cover,
                                  padded with blank pages to a multiple of 4; page 1 (the title page) is a recto

Cover: Nathan's ring-bound layout (print/cover_source_ringbound.pdf) re-set at 154 x 216 mm. His page maps onto
the trim box; his background JPEG (with his horizontal stretch) is scaled to cover the bleed; his logo image and
his text (vector, the embedded Aptos subset and his exact text runs) keep their relative places. Only the
copyright line moves, up to 5 mm inside the trim (his is 2.6 mm). The left-hand text is 13.7 mm inside the
trim, clear of the 12 mm ring-hole zone.

Interior: laid out afresh from manual.md and template.html at A5 (not shrunk), with a binding gutter: inner
margin 20 mm (left on odd pages, right on even pages), outer 12 mm; the headers, page numbers and images follow.
Listings never wrap: a code box too wide is set smaller, but never below 6 pt; a line still too long at 6 pt is
broken, the rest going on the next line after a "→" (in assembler, as a "; →" comment), with a note under the box.
Chrome rounds page sizes to 0.01 in, so the exact page boxes are set afterwards with pypdf.

Needs pypdf besides build.py's markdown:  pip install pypdf markdown;  plus Google Chrome and poppler-utils.
Usage:  python3 docs/manual/build_print.py"""
import os, re, sys, math, html as htmllib
from pypdf import PdfReader, PdfWriter
from pypdf.generic import RectangleObject, DecodedStreamObject, NameObject
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build
HERE = build.HERE
OUT = os.path.join(HERE, 'print')
PT = 72 / 25.4                       # points per mm
TRIM = (148, 210); BLEED = 3         # mm
INNER, OUTER = 20, 12                # mm, binding gutter and outside margin
MIN_CODE = 6.0                       # pt, smallest code size

def cover(src_pdf, out_pdf, min_inside=5.0):
    sp = PdfReader(src_pdf).pages[0]
    SW, SH = float(sp.mediabox.width), float(sp.mediabox.height)
    c = sp.get_contents().get_data().decode('latin-1')
    runs = re.findall(r'/F1 ([\d.]+) Tf\s+1 0 0 1 ([\d.]+) ([\d.]+) Tm.*?(\[.*?\]) TJ', c, re.S)
    bg = re.search(r'([\d.]+) 0 0 ([\d.]+) ([\d.]+) ([\d.]+) cm\s*/Image6 Do', c).groups()
    logo = re.search(r'([\d.]+) 0 0 ([\d.]+) ([\d.]+) ([\d.]+) cm\s*/Image7 Do', c).groups()
    assert len(runs) == 7, runs
    b = BLEED * PT; W = (TRIM[0] + 2 * BLEED) * PT; H = (TRIM[1] + 2 * BLEED) * PT
    sx, sy = TRIM[0] * PT / SW, TRIM[1] * PT / SH; k = math.sqrt(sx * sy)   # his page -> the trim box
    X = lambda x: b + x * sx; Y = lambda y: b + y * sy
    bw = W; bh = float(bg[1]) * W / float(bg[0])                            # his background aspect, as wide as the bleed
    ops = ['q %.4f 0 0 %.4f 0 %.4f cm /Image6 Do Q' % (bw, bh, (H - bh) / 2)]
    lw, lh, lx, ly = map(float, logo)
    ops.append('q %.4f 0 0 %.4f %.4f %.4f cm /Image7 Do Q' % (lw * k, lh * k, X(lx), Y(ly)))
    for size, x, y, tj in runs:
        size, x, y = float(size), float(x), float(y)
        ny = Y(y)
        if y < 0.1 * SH:   # the copyright line: at least min_inside mm above the trim (Aptos descender about 0.25 em)
            ny = max(ny, b + min_inside * PT + 0.25 * size * k)
        ops.append('BT /F1 %.3f Tf 1 g 1 0 0 1 %.4f %.4f Tm %s TJ ET' % (size * k, X(x), ny, tj))
    wr = PdfWriter(); p = wr.add_page(sp)
    for key in ('/StructParents', '/Tabs', '/CropBox', '/BleedBox', '/TrimBox', '/ArtBox'):
        if key in p: del p[key]
    s = DecodedStreamObject(); s.set_data('\n'.join(ops).encode('latin-1')); p.replace_contents(s)
    p.mediabox = RectangleObject([0, 0, W, H]); p.cropbox = RectangleObject([0, 0, W, H])
    p[NameObject('/BleedBox')] = RectangleObject([0, 0, W, H])
    p[NameObject('/TrimBox')] = RectangleObject([b, b, W - b, H - b])
    wr.add_metadata({'/Title': 'OpticOS User Manual: cover (A5 with 3 mm bleed, ring bound)'})
    with open(out_pdf, 'wb') as f: wr.write(f)
    print('cover: %s, background %d x %d px at %.0f x %.0f ppi, logo at %.0f ppi' % (
        out_pdf, 1152, 1728, 1152 / (bw / 72), 1728 / (bh / 72), 409 / (lw * k / 72)))

# --- code boxes: 148 mm - 20 - 12 mm margins - 2 x 3 mm padding - 2 pt rule; JetBrains Mono is 0.6 em a character
CODE_W = (TRIM[0] - INNER - OUTER - 6) * PT - 2
def capacity(size): return int(CODE_W / (0.6 * size) * 0.985)

def outside_strings(line, i):
    return line[:i].count('"') % 2 == 0

def break_line(line, n, asm):
    """Break a listing line longer than n characters; the rest goes on a continuation line."""
    if len(line) <= n: return [line]
    if asm:
        ci = line.index(';')            # only comments are long in the assembler listing
        bars = [i for i, ch in enumerate(line) if ch == '|']
        inside_art = lambda i: len(bars) >= 2 and bars[0] < i < bars[-1]
        cands = [i for i in range(ci + 2, min(n, len(line) - 1) + 1) if line[i] == ' ' and line[i - 1] != ' ' and not inside_art(i)]
        if len(bars) >= 2 and bars[-1] + 1 <= n: cands = [bars[-1] + 1]   # keep a |...| drawing whole, break after it
        i = max(cands); rest = ' ' * ci + '; \u2192 ' + line[i:].strip()
    else:
        ind = len(line) - len(line.lstrip())
        cands = [i for i in range(ind + 1, min(n, len(line) - 1) + 1) if line[i] == ' ' and line[i - 1] in ';:,' and outside_strings(line, i)]
        i = max(cands); rest = ' ' * (ind + 2) + '\u2192 ' + line[i:].strip()
    return [line[:i].rstrip()] + break_line(rest, n, asm)

SIZES = []
KEEP_OPEN, KEEP_CLOSE = '\x01', '\x02'   # placeholders for <span class="keep">, survive html escaping
def fit_code(body):
    out, pos = [], 0
    for m in re.finditer(r'<pre>(<code[^>]*>)?(.*?)(</code>)?</pre>', body, re.S):
        before = body[:m.start()]
        asm = before.rfind('<div class="asm"') > before.rfind('</div>')
        base = 6.0 if asm else 7.6
        lines = htmllib.unescape(m.group(2)).split('\n')
        longest = max(len(l) for l in lines)
        size = min(base, CODE_W / (0.6 * longest) * 0.985)
        note = ''
        if size < MIN_CODE:
            size = MIN_CODE
            new = []
            for l in lines:
                parts = break_line(l, capacity(size), asm)
                # a broken line and its continuations stay together on one page
                new.append(KEEP_OPEN + '\n'.join(parts) + KEEP_CLOSE if len(parts) > 1 else l)
            note = ('<p class="contnote">\u2192 continues a comment from the line above.</p>' if asm else
                    '<p class="contnote">A line that starts with \u2192 continues the line above: type both parts as one line.</p>')
            lines = new
        SIZES.append(size)
        style = 'white-space: pre;' + (' font-size: %.2fpt;' % size if size < base else '')
        out.append(body[pos:m.start()] + '<pre style="%s">%s%s%s</pre>%s' % (
            style, m.group(1) or '', htmllib.escape('\n'.join(lines), quote=False).replace(KEEP_OPEN, '<span class="keep">').replace(KEEP_CLOSE, '</span>'),
            m.group(3) or '', note))
        pos = m.end()
    return ''.join(out) + body[pos:]

def interior():
    t = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read()
    t, n = re.subn(r'@page \{ size: 420pt 595.28pt;[^\n]*?\*/', '@page { size: 148mm 210mm; /* A5, print interior */', t); assert n == 1
    gutter = ('@page :right { margin-left: %dmm; margin-right: %dmm; }   /* odd pages (rectos): the gutter on the left */\n'
              '@page :left { margin-left: %dmm; margin-right: %dmm; }    /* even pages (versos): the gutter on the right */\n'
              '.keep { display: inline-block; break-inside: avoid; }\n'
              '.contnote { font-size: 7pt; font-style: italic; color: #444; margin: -2mm 0 3mm; text-align: left; }\n'
              % (INNER, OUTER, OUTER, INNER))
    t, n = re.subn(r'(@page front \{)', gutter + r'\1', t); assert n == 1
    t, n = re.subn(r'<section class="cover front">.*?</section>\n', '', t, flags=re.S); assert n == 1   # the cover is printed separately
    html = os.path.join(HERE, 'manual_print.html')
    raw = os.path.join(OUT, '.interior_raw.pdf')
    build.build(t, html, raw, os.path.join(OUT, '.pages.json'), fit_code)
    w, h = TRIM[0] * PT, TRIM[1] * PT
    wr = PdfWriter()
    for p in PdfReader(raw).pages:
        # Chrome's page is 420 x 594.96 pt; set exactly A5, centred on it (0.24 pt off each side, 0.16 pt added top and bottom)
        pw, ph = float(p.mediabox.width), float(p.mediabox.height)
        x0, y0 = (pw - w) / 2, (ph - h) / 2
        box = RectangleObject([x0, y0, x0 + w, y0 + h])
        p.mediabox = box; p.cropbox = box; p.trimbox = box
        wr.add_page(p)
    content = len(wr.pages)
    while len(wr.pages) % 4: wr.add_blank_page(w, h)
    wr.add_metadata({'/Title': 'OpticOS User Manual: A5 print interior (ring bound, double-sided)'})
    out = os.path.join(OUT, 'OpticOS_Manual_A5_interior.pdf')
    with open(out, 'wb') as f: wr.write(f)
    os.remove(raw)
    print('interior: %s, %d pages + %d blank = %d; code sizes %.2f-%.2f pt, %d boxes set smaller' % (
        out, content, len(wr.pages) - content, len(wr.pages), min(SIZES), max(SIZES), sum(1 for s in SIZES if s < 7.6 and s != 6.0)))

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    cover(os.path.join(OUT, 'cover_source_ringbound.pdf'), os.path.join(OUT, 'OpticOS_Manual_A5_cover.pdf'))
    interior()
