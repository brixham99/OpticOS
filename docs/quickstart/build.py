#!/usr/bin/env python3
"""Build the OpticOS QuickStart for The Spectrum: one A4 sheet, printed on both
sides and folded to A5, giving four A5 pages (p1 cover, p2 Part 1 Getting
started, p3 Part 2 Loading tapes, p4 game controls and links).

  OpticOS_QuickStart_A4_imposed.pdf  2 A4 landscape pages, for printing:
                                     side 1 = p4 | p1, side 2 = p2 | p3.
                                     Print double-sided, FLIP ON SHORT EDGE,
                                     then fold in half with p1 on the front.
  OpticOS_QuickStart_A5_reader.pdf   the 4 A5 pages in reading order
  OpticOS_QuickStart_side1.png, _side2.png   previews of the two A4 sides

Source: quickstart.html (shared CSS plus one <template> per page). The screen
grabs in img/ come from real Fuse (fuse_quickstart.py). Text stays 10 mm from
the outer edges and 13 mm from the fold; verify() checks at least 5 mm.
Needs google-chrome, poppler-utils and Python 3 with segno (QR codes)."""
import os, re, subprocess, segno
HERE = os.path.dirname(os.path.abspath(__file__))
LINKS = {'QR_OPTICOS': 'https://github.com/brixham99/OpticOS', 'QR_DINO': 'https://github.com/brixham99/ZX-Dino',
         'QR_BAT': 'https://github.com/brixham99/happy-bat'}
MM = 72 / 25.4
SRC = open(os.path.join(HERE, 'quickstart.html'), encoding='utf-8').read()
HEAD = SRC.split('<!-- ====')[0]
PAGES = dict(re.findall(r'<template id="(p\d)">(.*?)</template>', SRC, re.S))
SIDE = {'p1': 'R', 'p2': 'L', 'p3': 'R', 'p4': 'L'}    # which half of the A4 each page sits on

def cropped_logo():
    """the logo SVG with its viewBox cut to the drawing (it sits on an A4 artboard)"""
    s = open(os.path.join(HERE, 'optica_logo.svg'), encoding='utf-8').read()
    s = re.sub(r'width="[^"]*in" height="[^"]*in"\s+viewBox="[^"]*"', 'viewBox="34 95 778 368"', s, count=1)
    open(os.path.join(HERE, 'optica_logo_crop.svg'), 'w', encoding='utf-8').write(s)

def qr(url):
    q = segno.make(url, error='m'); n = q.symbol_size(border=0)[0]
    svg = q.svg_inline(scale=1, border=0, dark='#1a1a1a')
    return svg if 'viewBox' in svg else svg.replace('<svg ', '<svg viewBox="0 0 %d %d" ' % (n, n), 1)

def page(p, solo):
    body = PAGES[p]
    for k, u in LINKS.items(): body = body.replace('{{%s}}' % k, qr(u))
    return '<div class="pg %s%s">%s</div>' % (SIDE[p], ' solo' if solo else '', body)

def pdf(name, size, pages_html):
    html = HEAD.replace('{{PAGESIZE}}', size).replace('{{PAGES}}', pages_html)
    tmp = os.path.join(HERE, '_build.html'); open(tmp, 'w', encoding='utf-8').write(html)
    out = os.path.join(HERE, name)
    subprocess.run(['google-chrome', '--headless', '--no-sandbox', '--disable-gpu', '--no-pdf-header-footer',
                    '--print-to-pdf=' + out, 'file://' + tmp], check=True, stderr=subprocess.DEVNULL)
    os.remove(tmp); return out

def verify(path, w_mm, h_mm, n, folds):
    info = subprocess.run(['pdfinfo', path], capture_output=True, text=True).stdout
    w, h = map(float, re.search(r'Page size:\s+([\d.]+) x ([\d.]+)', info).groups())
    pages = int(re.search(r'Pages:\s+(\d+)', info).group(1))
    assert pages == n and abs(w - w_mm * MM) < 1.5 and abs(h - h_mm * MM) < 1.5, (path, pages, w / MM, h / MM)
    worst = 99
    for pg in range(1, n + 1):
        bbox = subprocess.run(['pdftotext', '-bbox', '-f', str(pg), '-l', str(pg), path, '-'], capture_output=True, text=True).stdout
        for x0, y0, x1, y1 in re.findall(r'xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)"', bbox):
            x0, y0, x1, y1 = (float(v) / MM for v in (x0, y0, x1, y1))
            d = min(x0, y0, w_mm - x1, h_mm - y1)
            for f in folds: d = min(d, abs(x0 - f) if x0 >= f else abs(f - x1) if x1 <= f else -1)
            worst = min(worst, d)
    print('%s: %d pages %.0f x %.0f mm; text at least %.1f mm from the edges%s' % (
        os.path.basename(path), n, w_mm, h_mm, worst, ' and the fold' if folds else ''))
    assert worst >= 5, 'text inside the 5 mm safe area'

if __name__ == '__main__':
    cropped_logo()
    imposed = pdf('OpticOS_QuickStart_A4_imposed.pdf', '297mm 210mm',
                  ''.join('<div class="sheet">%s%s</div>' % (page(a, False), page(b, False)) for a, b in (('p4', 'p1'), ('p2', 'p3'))))
    reader = pdf('OpticOS_QuickStart_A5_reader.pdf', '148.5mm 210mm', ''.join(page(p, True) for p in ('p1', 'p2', 'p3', 'p4')))
    verify(imposed, 297, 210, 2, [148.5]); verify(reader, 148.5, 210, 4, [])
    for i in (1, 2):
        subprocess.run(['pdftoppm', '-png', '-r', '150', '-f', str(i), '-l', str(i), '-singlefile', imposed,
                        os.path.join(HERE, 'OpticOS_QuickStart_side%d' % i)], check=True)
    print('print the imposed PDF double-sided, flip on SHORT edge; fold with p1 (the cover) on the front')
