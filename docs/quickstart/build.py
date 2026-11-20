#!/usr/bin/env python3
"""Build the OpticOS QuickStart sheet for The Spectrum (A5 portrait):
  OpticOS_QuickStart_A5_trim.pdf   148 x 210 mm, the trimmed page
  OpticOS_QuickStart_A5_bleed.pdf  154 x 216 mm, 3 mm bleed all round (colour bands run into it)
  OpticOS_QuickStart_A5.png        a preview of the trim version
from quickstart.html (headless Chrome, as the manual). Text is kept at least
5 mm inside the trim (the page box is 8 mm in; verify() checks the text in the
PDF). The boot screen is the manual's Fuse grab (docs/manual/img/boot.png).
Needs google-chrome, poppler-utils and Python 3 with segno (QR codes)."""
import os, re, subprocess, segno
HERE = os.path.dirname(os.path.abspath(__file__))
LOGO = os.path.join(HERE, 'optica_logo.svg')
LINKS = {'QR_OPTICOS': 'https://github.com/brixham99/OpticOS', 'QR_DINO': 'https://github.com/brixham99/ZX-Dino',
         'QR_BAT': 'https://github.com/brixham99/happy-bat'}
MM = 72 / 25.4

def cropped_logo():
    """the logo SVG with its viewBox cut down to the drawing (it sits on an A4 artboard)"""
    s = open(LOGO, encoding='utf-8').read()
    s = re.sub(r'width="[^"]*in" height="[^"]*in"\s+viewBox="[^"]*"', 'viewBox="34 95 778 368"', s, count=1)
    open(os.path.join(HERE, 'optica_logo_crop.svg'), 'w', encoding='utf-8').write(s)

def qr(url):
    svg = segno.make(url, error='m').svg_inline(scale=1, border=0, dark='#1a1a1a')
    return re.sub(r'<svg ', '<svg viewBox="0 0 %d %d" ' % ((segno.make(url, error='m').symbol_size(border=0)[0],) * 2), svg, count=1) \
        if 'viewBox' not in svg else svg

def build(bleed, pdf):
    html = open(os.path.join(HERE, 'quickstart.html'), encoding='utf-8').read().replace('{{BLEED}}', bleed)
    for k, u in LINKS.items(): html = html.replace('{{%s}}' % k, qr(u))
    tmp = os.path.join(HERE, '_build_%s.html' % bleed)
    open(tmp, 'w', encoding='utf-8').write(html)
    subprocess.run(['google-chrome', '--headless', '--no-sandbox', '--disable-gpu', '--no-pdf-header-footer',
                    '--print-to-pdf=' + pdf, 'file://' + tmp], check=True, stderr=subprocess.DEVNULL)
    os.remove(tmp)

def verify(pdf, bleed_mm):
    info = subprocess.run(['pdfinfo', pdf], capture_output=True, text=True).stdout
    w, h = map(float, re.search(r'Page size:\s+([\d.]+) x ([\d.]+)', info).groups())
    pages = int(re.search(r'Pages:\s+(\d+)', info).group(1))
    assert pages == 1, pdf + ': %d pages' % pages
    exp = ((148 + 2 * bleed_mm) * MM, (210 + 2 * bleed_mm) * MM)
    assert abs(w - exp[0]) < 1 and abs(h - exp[1]) < 1, (pdf, w, h, exp)
    bbox = subprocess.run(['pdftotext', '-bbox', pdf, '-'], capture_output=True, text=True).stdout
    words = [tuple(map(float, m)) for m in re.findall(r'xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)"', bbox)]
    b = bleed_mm * MM
    x0 = min(x for x, _, _, _ in words) - b; y0 = min(y for _, y, _, _ in words) - b
    x1 = 148 * MM - (max(x for _, _, x, _ in words) - b); y1 = 210 * MM - (max(y for _, _, _, y in words) - b)
    m = min(x0, y0, x1, y1) / MM
    print('%s: %.1f x %.1f mm, 1 page, text at least %.1f mm inside the trim (left %.1f, top %.1f, right %.1f, bottom %.1f)' % (
        os.path.basename(pdf), w / MM, h / MM, m, x0 / MM, y0 / MM, x1 / MM, y1 / MM))
    assert m >= 5, 'text closer than 5 mm to the trim'

if __name__ == '__main__':
    cropped_logo()
    trim = os.path.join(HERE, 'OpticOS_QuickStart_A5_trim.pdf'); bleed = os.path.join(HERE, 'OpticOS_QuickStart_A5_bleed.pdf')
    build('0mm', trim); build('3mm', bleed)
    verify(trim, 0); verify(bleed, 3)
    subprocess.run(['pdftoppm', '-png', '-r', '200', '-singlefile', trim, os.path.join(HERE, 'OpticOS_QuickStart_A5')], check=True)
    print('wrote', os.path.basename(trim), os.path.basename(bleed), 'OpticOS_QuickStart_A5.png')
