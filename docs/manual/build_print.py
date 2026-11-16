#!/usr/bin/env python3
"""Print edition of the manual, written to docs/manual/print/:

  OpticOS_Manual_A5_cover.pdf     one page, 154 x 216 mm: A5 plus 3 mm bleed on every edge
  OpticOS_Manual_A5_interior.pdf  exactly A5 (148 x 210 mm), no bleed, every page but the front cover,
                                  padded with blank pages to a multiple of 4

The interior is laid out afresh from manual.md and template.html with A5 page settings (not shrunk);
listings never wrap: a code box too wide for the page is set in a smaller size of JetBrains Mono.
The cover is Nathan's artwork (print/cover_artwork.png, 1920 x 2773) placed 140 mm wide (about 348 dpi)
so that its text and logo sit well inside the 3 mm safe area; the borders out to the bleed are the
artwork's own edges mirrored, taken from a copy with the text removed so no mirrored text appears.
Chrome rounds page sizes to 0.01 in, so the exact boxes are set afterwards with pypdf.

Needs pypdf, img2pdf, numpy and Pillow besides build.py's markdown:  pip install pypdf img2pdf numpy pillow markdown
Usage:  python3 docs/manual/build_print.py"""
import os, re, io, sys, html as htmllib
import numpy as np
from PIL import Image, ImageOps, ImageFilter
import img2pdf
from pypdf import PdfReader, PdfWriter
from pypdf.generic import RectangleObject
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build
HERE = build.HERE
OUT = os.path.join(HERE, 'print')
PT = 72 / 25.4                              # points per mm
TRIM = (148, 210); BLEED = 3; ART_W = 140   # mm

def text_free(art, boxes):
    """Replace the text and logo pixels inside boxes with nearby background (used for the mirrored borders only)."""
    a = np.asarray(art).astype(float); out = a.copy()
    def box1(x, r, ax):
        p = np.pad(x, [(r + 1, r) if i == ax else (0, 0) for i in range(2)], mode='edge')
        c = np.cumsum(p, axis=ax)
        return (np.take(c, range(2 * r + 1, c.shape[ax]), axis=ax) - np.take(c, range(0, c.shape[ax] - 2 * r - 1), axis=ax)) / (2 * r + 1)
    def blur(x, r=24):
        for _ in range(3): x = box1(box1(x, r, 0), r, 1)
        return x
    for (x0, y0, x1, y1) in boxes:
        reg = a[y0:y1, x0:x1]
        lo, hi = reg.min(axis=2), reg.max(axis=2)
        m = Image.fromarray(((lo > 45) | (hi - lo > 60)).astype('uint8') * 255).filter(ImageFilter.MaxFilter(21))
        keep = 1 - np.asarray(m).astype(float) / 255
        wk = blur(keep) + 1e-6
        fill = np.stack([blur(reg[..., ch] * keep) / wk for ch in range(3)], axis=2)
        out[y0:y1, x0:x1] = reg * keep[..., None] + fill * (1 - keep[..., None])
    return Image.fromarray(out.clip(0, 255).astype('uint8'))

def mirror_pad(art, plate, l, t, r, b):
    """art in the middle; the borders are mirrored from plate (the art without its text)."""
    W, H = art.size
    c = Image.new('RGB', (W + l + r, H + t + b))
    c.paste(ImageOps.mirror(plate.crop((0, 0, l, H))), (0, t))
    c.paste(ImageOps.mirror(plate.crop((W - r, 0, W, H))), (l + W, t))
    c.paste(plate, (l, t))
    row = c.crop((0, t, c.width, 2 * t)); c.paste(ImageOps.flip(row), (0, 0))
    row = c.crop((0, t + H - b, c.width, t + H)); c.paste(ImageOps.flip(row), (0, t + H))
    c.paste(art, (l, t))
    return c

def cover():
    src = Image.open(os.path.join(OUT, 'cover_artwork.png')).convert('RGB')
    src = src.crop((0, 0, src.width, src.height - 1))   # the artwork's last row is a grey hairline
    W, H = src.size; pxmm = W / ART_W
    w_mm, h_mm = TRIM[0] + 2 * BLEED, TRIM[1] + 2 * BLEED
    CW, CH = round(w_mm * pxmm), round(h_mm * pxmm)
    l = (CW - W) // 2; r = CW - W - l; t = (CH - H) // 2; b = CH - H - t
    boxes = [(0, 100, 760, 940), (1100, 2660, W, H), (1300, 230, W, 520)]   # title and list, copyright, logo
    canvas = mirror_pad(src, text_free(src, boxes), l, t, r, b)
    buf = io.BytesIO(); canvas.save(buf, 'JPEG', quality=95, subsampling=0, dpi=(round(pxmm * 25.4),) * 2)
    layout = img2pdf.get_layout_fun((img2pdf.mm_to_pt(w_mm), img2pdf.mm_to_pt(h_mm)), fit=img2pdf.FitMode.exact)
    out = os.path.join(OUT, 'OpticOS_Manual_A5_cover.pdf')
    open(out, 'wb').write(img2pdf.convert(buf.getvalue(), layout_fun=layout, title='OpticOS User Manual: cover (A5, 3 mm bleed)'))
    print('cover: %s, %d x %d px, %.0f dpi; art %d mm wide, borders %d/%d/%d/%d px' % (out, CW, CH, pxmm * 25.4, ART_W, l, t, r, b))

# Code boxes in the interior: 148 mm - 2 x 14 mm margins - 2 x 3 mm padding - 2 pt rule, JetBrains Mono 0.6 em a character
CODE_W = (TRIM[0] - 28 - 6) * PT - 2
def fit_code(body):
    """Never wrap a listing: a code box whose longest line would not fit is set smaller, just enough to fit."""
    out, pos, n = [], 0, 0
    for m in re.finditer(r'<pre>(.*?)</pre>', body, re.S):
        before = body[:m.start()]
        base = 6.0 if before.rfind('<div class="asm"') > before.rfind('</div>') else 7.6
        longest = max(len(htmllib.unescape(re.sub(r'<[^>]+>', '', l))) for l in m.group(1).split('\n'))
        size = min(base, CODE_W / (0.6 * longest) * 0.985)
        style = 'white-space: pre;' + (' font-size: %.2fpt;' % size if size < base else '')
        n += size < base
        out.append(body[pos:m.start()] + '<pre style="%s">' % style + m.group(1) + '</pre>'); pos = m.end()
    print('code boxes set smaller to fit:', n)
    return ''.join(out) + body[pos:]

def interior():
    t = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read()
    t, n = re.subn(r'@page \{ size: 420pt 595.28pt;[^\n]*?\*/', '@page { size: 148mm 210mm; /* A5, print interior */', t); assert n == 1
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
    wr.add_metadata({'/Title': 'OpticOS User Manual: A5 print interior'})
    out = os.path.join(OUT, 'OpticOS_Manual_A5_interior.pdf')
    with open(out, 'wb') as f: wr.write(f)
    os.remove(raw)
    print('interior: %s, %d pages + %d blank = %d' % (out, content, len(wr.pages) - content, len(wr.pages)))

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    cover(); interior()
