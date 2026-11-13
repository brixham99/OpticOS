#!/usr/bin/env python3
"""Build docs/manual/OpticOS_User_Manual.pdf from manual.md (python markdown + headless Chrome)."""
import os, re, subprocess, markdown
HERE = os.path.dirname(os.path.abspath(__file__))
md = open(os.path.join(HERE, 'manual.md'), encoding='utf-8').read()
md = re.sub(r'```\nINCLUDE (\S+)\n```', lambda m: '```\n' + open(os.path.join(HERE, 'examples', m.group(1))).read().rstrip() + '\n```', md)
# number the chapters
n = [0]
def chap(m):
    n[0] += 1
    return '<h1 id="c%d"><span class="num">%d</span>%s</h1>' % (n[0], n[0], m.group(1))
body = markdown.markdown(md, extensions=['tables', 'fenced_code', 'md_in_html'])
body = re.sub(r'<h1>(.*?)</h1>', chap, body)
titles = re.findall(r'<h1 id="c(\d+)"><span class="num">\d+</span>(.*?)</h1>', body)
import json
pages = json.load(open(os.path.join(HERE, '.pages.json'))) if os.path.exists(os.path.join(HERE, '.pages.json')) else {}
toc = '\n'.join('<li><a href="#c%s"><span>%s</span><em>%s</em><b>%s</b></a></li>' % (i, i, t, pages.get(i, '')) for i, t in titles)
html = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read()
html = html.replace('{{TOC}}', toc).replace('{{BODY}}', body)
out = os.path.join(HERE, 'manual.html')
open(out, 'w', encoding='utf-8').write(html)
pdf = os.path.join(HERE, 'OpticOS_User_Manual.pdf')
subprocess.run(['google-chrome', '--headless', '--no-sandbox', '--disable-gpu', '--no-pdf-header-footer',
                '--print-to-pdf=' + pdf, 'file://' + out], check=True, stderr=subprocess.DEVNULL)
# find each chapter's page and rebuild once if the contents page changed
found = {}
np = int(re.search(r'Pages:\s+(\d+)', subprocess.run(['pdfinfo', pdf], capture_output=True, text=True).stdout).group(1))
for p in range(1, np + 1):
    txt = subprocess.run(['pdftotext', '-f', str(p), '-l', str(p), pdf, '-'], capture_output=True, text=True).stdout
    for m in re.finditer(r'CHAPTER (\d+)', txt): found.setdefault(m.group(1), str(p))
if found != pages:
    json.dump(found, open(os.path.join(HERE, '.pages.json'), 'w'))
    subprocess.run(['python3', __file__], check=True)
else:
    print('wrote', pdf, np, 'pages')
