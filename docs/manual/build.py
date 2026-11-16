#!/usr/bin/env python3
"""Build docs/manual/OpticOS_User_Manual.pdf from manual.md (python markdown + headless Chrome).
build_print.py reuses these functions for the A5 print edition (docs/manual/print/)."""
import os, re, json, subprocess, markdown
HERE = os.path.dirname(os.path.abspath(__file__))

def body_html():
    md = open(os.path.join(HERE, 'manual.md'), encoding='utf-8').read()
    md = re.sub(r'```\nINCLUDE (\S+)\n```', lambda m: '```\n' + open(os.path.join(HERE, 'examples', m.group(1))).read().rstrip() + '\n```', md)
    n = [0]
    def chap(m):   # number the chapters
        n[0] += 1
        return '<h1 id="c%d"><span class="num">%d</span>%s</h1>' % (n[0], n[0], m.group(1))
    body = markdown.markdown(md, extensions=['tables', 'fenced_code', 'md_in_html'])
    return re.sub(r'<h1>(.*?)</h1>', chap, body)

def page_html(template, pages, filt=None):
    body = body_html()
    if filt: body = filt(body)
    titles = re.findall(r'<h1 id="c(\d+)"><span class="num">\d+</span>(.*?)</h1>', body)
    toc = '\n'.join('<li><a href="#c%s"><span>%s</span><em>%s</em><b>%s</b></a></li>' % (i, i, t, pages.get(i, '')) for i, t in titles)
    return template.replace('{{TOC}}', toc).replace('{{BODY}}', body)

def chrome_pdf(html_path, pdf):
    subprocess.run(['google-chrome', '--headless', '--no-sandbox', '--disable-gpu', '--no-pdf-header-footer',
                    '--print-to-pdf=' + pdf, 'file://' + html_path], check=True, stderr=subprocess.DEVNULL)

def page_count(pdf):
    return int(re.search(r'Pages:\s+(\d+)', subprocess.run(['pdfinfo', pdf], capture_output=True, text=True).stdout).group(1))

def chapter_pages(pdf):
    found = {}
    for p in range(1, page_count(pdf) + 1):
        txt = subprocess.run(['pdftotext', '-f', str(p), '-l', str(p), pdf, '-'], capture_output=True, text=True).stdout
        for m in re.finditer(r'CHAPTER (\d+)', txt): found.setdefault(m.group(1), str(p))
    return found

def build(template, html_out, pdf_out, pages_file, filt=None):
    """Write the HTML and PDF, rebuilding until the contents page numbers match the PDF."""
    for _ in range(4):
        pages = json.load(open(pages_file)) if os.path.exists(pages_file) else {}
        open(html_out, 'w', encoding='utf-8').write(page_html(template, pages, filt))
        chrome_pdf(html_out, pdf_out)
        found = chapter_pages(pdf_out)
        if found == pages: return page_count(pdf_out)
        json.dump(found, open(pages_file, 'w'))
    raise SystemExit('contents page numbers did not settle')

if __name__ == '__main__':
    template = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read()
    pdf = os.path.join(HERE, 'OpticOS_User_Manual.pdf')
    n = build(template, os.path.join(HERE, 'manual.html'), pdf, os.path.join(HERE, '.pages.json'))
    print('wrote', pdf, n, 'pages')
