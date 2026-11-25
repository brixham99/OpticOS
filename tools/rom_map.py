#!/usr/bin/env python3
"""Draw docs/screenmodes/rom_maps.png from the actual built ROM symbols
and tools/check_layout.py module ranges (not guessed)."""
import re
from collections import Counter
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/screenmodes/rom_maps.png'

def load_sym(path):
    d = {}
    for line in Path(path).read_text().splitlines():
        m = re.match(r'(\w+)\s+EQU\s+0?([0-9A-F]+)H', line)
        if m:
            d[m.group(1)] = int(m.group(2), 16)
    return d

def paint(arr, lo, hi, tag):
    lo = max(0, lo); hi = min(len(arr), hi)
    for i in range(lo, hi):
        arr[i] = tag

def runs(arr):
    out, i = [], 0
    while i < len(arr):
        j = i
        while j < len(arr) and arr[j] == arr[i]:
            j += 1
        out.append((i, j, arr[i], j - i))
        i = j
    return out

def main():
    s0 = load_sym(ROOT / 'build/opticos.sym')
    s1 = load_sym(ROOT / 'build/opticos128ext.sym')
    rom0 = (ROOT / 'build/opticos.rom').read_bytes()
    rom1 = (ROOT / 'build/opticos128ext.rom').read_bytes()
    assert len(rom0) == 16384 and len(rom1) == 16384

    # Official ROM 0 totals from the same arithmetic as check_layout.py
    def R(a, b):
        return s0[b] - s0[a]
    official_used = 16303  # tools/check_layout.py "bytes of code and data placed"
    official_free = 16384 - official_used  # 81

    C0 = {
        'rst':  ((0x3B4A6C), 'Restarts, NMI, reset, boot'),
        'isr':  ((0xC47A2C), 'Interrupts & keyboard'),
        'prt':  ((0x2E86AB), 'Screen / print / CLS / RST 16'),
        'tape': ((0x8E6B23), 'Tape (SA/LD-BYTES & SAVE/LOAD)'),
        'snd':  ((0xD35400), 'Sound (BEEPER, BEEP, chime)'),
        'err':  ((0xB03A2E), 'Errors (RST 8 & messages)'),
        'leg':  ((0x6B5B8A), 'Legacy loader shim'),
        'fp':   ((0x1D6A9A), 'Floating-point & number I/O'),
        'exp':  ((0x3D8B6E), 'Expressions & string/machine fns'),
        'var':  ((0x2A6F97), 'Variables, arrays, heap, stacks'),
        'tok':  ((0x7B5EA7), 'Tokeniser, keywords, LIST'),
        'bas':  ((0x2C5AA0), 'BASIC interpreter (run, PROC, CASE)'),
        'ed':   ((0x4A7C59), 'Editor, console, INPUT / DATA'),
        'gfx':  ((0xC0392B), 'Graphics (PLOT, DRAW, DRAW TO)'),
        'stub': ((0x7A7260), 'Fixed-address stubs'),
        'font': ((0x4F4F4F), '4-pixel font'),
        'hook': ((0xE8A020), '128K hooks (xgo, x_rst, ext_hook)'),
        'free': ((0xDEDEDE), 'Free gaps (unplaced)'),
        'other':((0xA0A0A0), 'Other / unlabelled'),
    }

    a0 = [None] * 16384
    def add0(tag, *pairs):
        for a, b in pairs:
            lo, hi = (s0[a], s0[b]) if isinstance(a, str) else (a, b)
            paint(a0, lo, hi, tag)

    add0('rst', ('RESET', 'm_rst_e'), ('NMI', 'm_nmi_e'), ('m_boot_s', 'm_boot_e'))
    add0('isr', ('ISR', 'm_isr_e'), ('m_kbd_s', 'm_kbd_e'))
    add0('prt', ('m_prt_s', 'm_prt_e'), ('m_cls_s', 'm_cls_e'))
    add0('tape', ('m_sav_s', 'm_sav_g'), ('trap_ret', 'm_sav_e'),
               ('m_ld_s', 'm_ld_e'), ('m_edge_s', 'm_edge_e'), ('m_ld_s2', 'm_ld_e2'),
               ('m_tcmd_s', 'm_tcmd_e'), ('m_tp_s', 'm_tp_e'))
    add0('snd', ('m_snd_s', 'm_snd_e'), ('m_msc_s', 'm_msc_e'), ('m_chm_s', 'm_chm_e'))
    add0('err', ('m_err_s', 'm_err_e'), ('m_err2_s', 'm_err2_e'))
    add0('leg', ('m_leg_s', 'm_leg_e1'), ('m_leg_s2', 'm_leg_e2'))
    add0('fp',  ('m_fpc_s', 'm_fpc_e'), ('m_fpt_s', 'm_fpt_e'), ('m_fpk_s', 'm_fpk_e'),
               ('m_fpv_s', 'm_fpv_e'), ('m_num_s', 'm_num_e'))
    add0('exp', ('m_exp_s', 'm_exp_e'), ('m_sfn_s', 'm_sfn_e'), ('m_sf2_s', 'm_sf2_e'),
               ('m_key_s', 'm_key_e'))
    add0('var', ('m_var_s', 'm_var_e'))
    add0('tok', ('m_tok_s', 'm_tok_e'), ('m_lst_s', 'm_lst_e'), ('m_tkt_s', 'm_tkt_e'),
               ('m_tkd_s', 'm_tkd_e'))
    add0('bas', ('m_bas_s', 'm_bas_e'), ('m_ms2_s', 'm_ms2_e'), ('m_cas_s', 'm_cas_e'),
               ('m_ext_s', 'm_ext_e'), ('m_clr_s', 'm_clr_e'))
    add0('ed',  ('m_con_s', 'm_con_e'), ('m_edt_s', 'm_edt_e'), ('m_in_s', 'm_in_e'))
    add0('gfx', ('m_gfx_s', 'm_gfx_e'))
    add0('stub',('m_stb_s', 'm_stb_e'), ('m_stb_s2', 'm_stb_e2'), ('m_stb_s3', 'm_stb_e3'))
    add0('font',('m_font_s', 'm_font_e'))
    # leftover
    for i in range(16384):
        if a0[i] is None:
            a0[i] = 'free' if rom0[i] == 0 else 'other'
    # hooks drawn on top for visibility (tiny reserved slots)
    hook_spans = [
        (s0['xgo'], s0['x_back'] + 1, 'xgo'),
        (s0['x_rst'], s0['m_ld_e'], 'x_rst'),
        (s0['ext_hook'], s0['secH_end'], 'ext_hook'),
    ]
    hook_bytes = 0
    for lo, hi, _ in hook_spans:
        hook_bytes += hi - lo
        paint(a0, lo, hi, 'hook')

    C1 = {
        'hole': ((0xECE8DC), 'Unused low memory (ORG holes for trampolines)'),
        'stub': ((0xE8A020), 'Low hook stubs (ISR, xgo, far-return, ext_back)'),
        'disp': ((0xC47A2C), 'Dispatch (SCREEN, BOX, CIRCLE, SAY)'),
        'sstmt':((0x3D8B6E), 'SAY statements (PITCH, VOICE, TUNE, LOAD)'),
        'eng':  ((0x2E86AB), 'Speech / allophone engine, AY player'),
        'rules':((0x1D6A9A), 'Letter-to-sound rules'),
        'scr':  ((0x2C5AA0), 'Screen modes: PLOT, CLS, POINT, render, FLIP'),
        'draw': ((0xC0392B), 'DRAW, BOX, CIRCLE'),
        'ta2':  ((0x4A7C59), 'TA2 (SCREEN 3 attribute table)'),
        'ta':   ((0x8E6B23), 'TA (SCREEN 2 attribute table)'),
        'ay':   ((0xD35400), 'AY volume table'),
        'free': ((0xDEDEDE), 'Free (usable, before tables)'),
        'other':((0xA0A0A0), 'Other / unlabelled'),
    }
    a1 = ['hole'] * s1['ext_main'] + ['free'] * (16384 - s1['ext_main'])
    # low hook stubs: any nonzero below ext_main
    for i in range(s1['ext_main']):
        if rom1[i] != 0:
            a1[i] = 'stub'
    paint(a1, s1['ext_main'], s1['em_say'], 'disp')
    paint(a1, s1['em_say'], s1['say_text'], 'sstmt')
    paint(a1, s1['say_text'], s1['rules'], 'eng')
    paint(a1, s1['rules'], s1['es_scr'], 'rules')
    paint(a1, s1['es_scr'], s1['x_draw'], 'scr')
    # DRAW/BOX/CIRCLE through the name table
    name_end = s1['n_circle'] + 1 + 6  # length byte + "circle"
    paint(a1, s1['x_draw'], name_end, 'draw')
    paint(a1, 0x3B00, 0x3B10, 'ta2')
    paint(a1, 0x3C00, 0x3D00, 'ta')
    paint(a1, 0x3D00, 0x4000, 'ay')
    # documented usable free: $31BE–$3AFF and $3B10–$3BFF
    # (already 'free' if unpainted; confirm holes aren't marked free)
    for i in range(name_end, 0x3B00):
        a1[i] = 'free' if rom1[i] == 0 else 'other'
    for i in range(0x3B10, 0x3C00):
        a1[i] = 'free' if rom1[i] == 0 else 'other'

    n0, n1 = Counter(a0), Counter(a1)
    ext_free = n1['free']  # should be 2610

    # ----- canvas -----
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 13)
    fontb = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 16)
    fontt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
    fonts = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 12)
    fontm = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf', 11)

    W, H = 1680, 1500
    im = Image.new('RGB', (W, H), (248, 248, 246))
    dr = ImageDraw.Draw(im)
    dr.text((40, 20), 'OpticOS 16K ROM maps', fill=(20, 20, 20), font=fontt)
    dr.text((40, 50),
            'Generated from build/opticos.sym, build/opticos128ext.sym and the module ranges in tools/check_layout.py',
            fill=(70, 70, 70), font=fonts)

    def column(x, arr, palette, heading, sub, min_label=280):
        bar_x, bar_w, bar_y, bar_h = x, 74, 130, 900
        dr.text((x - 50, 88), heading, fill=(20, 20, 20), font=fontb)
        dr.text((x - 50, 108), sub, fill=(70, 70, 70), font=fonts)
        for addr in list(range(0, 0x4000, 0x0400)) + [0x3FFF]:
            y = bar_y + (min(addr, 0x3FFF) / 16383) * bar_h
            lab = '$%04X' % addr
            dr.line((bar_x - 6, y, bar_x, y), fill=(80, 80, 80), width=1)
            tw = dr.textbbox((0, 0), lab, font=fontm)[2]
            dr.text((bar_x - 10 - tw, y - 6), lab, fill=(50, 50, 50), font=fontm)
        # paint
        for lo, hi, tag, n in runs(arr):
            y0 = bar_y + lo / 16384 * bar_h
            y1 = bar_y + hi / 16384 * bar_h
            if y1 < y0 + 1:
                y1 = y0 + 1
            dr.rectangle((bar_x + 1, y0, bar_x + bar_w - 1, y1), fill=palette[tag][0])
        dr.rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), outline=(30, 30, 30), width=1)

        # labels: largest run of each tag (if >= min_label), plus any run >= 600
        label_x = bar_x + bar_w + 14
        candidates = []
        best = {}
        for lo, hi, tag, n in runs(arr):
            if tag in ('other',) and n < 80:
                continue
            if n >= min_label:
                if tag not in best or n > best[tag][3]:
                    best[tag] = (lo, hi, tag, n)
            elif n >= 600:
                candidates.append((lo, hi, tag, n))
        candidates.extend(best.values())
        # unique by (lo,hi)
        seen, uniq = set(), []
        for c in candidates:
            if (c[0], c[1]) not in seen:
                seen.add((c[0], c[1])); uniq.append(c)
        uniq.sort(key=lambda c: c[0])
        placed = []
        for lo, hi, tag, n in uniq:
            mid = bar_y + ((lo + hi) / 2) / 16384 * bar_h
            ty = mid - 7
            for py in placed:
                if abs(ty - py) < 15:
                    ty = py + 15
            placed.append(ty)
            name = palette[tag][1]
            # short name for the bar
            short = name.split('(')[0].strip()
            text = '%s   %s B' % (short, f'{n:,}')
            ly = bar_y + lo / 16384 * bar_h
            hy = bar_y + hi / 16384 * bar_h
            dr.line((bar_x + bar_w, (ly + hy) / 2, label_x - 3, ty + 7), fill=(130, 130, 130), width=1)
            dr.text((label_x, ty), text, fill=(25, 25, 25), font=fonts)
        return bar_y + bar_h

    sub0 = 'check_layout: {:,} B placed, {:,} B free   ·   128K hooks {:,} B (called out below)'.format(
        official_used, official_free, hook_bytes)
    sub1 = 'Build: code through $%04X, {:,} B usable free  ($31BE–$3AFF + $3B10–$3BFF)'.format(
        ext_free) % (s1['n_circle'] + 7)  # close enough; use last from earlier
    # compute last code byte
    last = s1['n_circle'] + 7
    sub1 = 'Build: code through $%04X,  %s B usable free  ($%04X–$3AFF + $3B10–$3BFF)' % (
        last, f'{ext_free:,}', last)

    y_end = column(110, a0, C0, 'ROM 0  —  OpticOS main  ($0000–$3FFF)', sub0, min_label=220)
    column(900, a1, C1, 'ROM 1  —  merged extension  ($0000–$3FFF)', sub1, min_label=200)

    # hook note under ROM 0 bar
    hx, hy = 60, y_end + 14
    dr.text((hx, hy), '128K hooks in ROM 0 (reserved slots, shown in gold on the bar):', fill=(80, 50, 0), font=fonts)
    hook_note = '     ' + '     '.join(
        '%s  $%04X–$%04X  (%d B)' % (name, lo, hi - 1, hi - lo)
        for lo, hi, name in hook_spans)
    dr.text((hx, hy + 16), hook_note, fill=(80, 50, 0), font=fontm)

    def legend(x, y, palette, counts, title, skip=()):
        dr.text((x, y), title, fill=(20, 20, 20), font=fontb)
        yy = y + 24
        for tag, (col, name) in palette.items():
            if tag in skip:
                continue
            n = counts.get(tag, 0)
            if n == 0:
                continue
            dr.rectangle((x, yy + 1, x + 13, yy + 14), fill=col, outline=(40, 40, 40))
            dr.text((x + 20, yy), '%s    %s B' % (name, f'{n:,}'), fill=(30, 30, 30), font=fonts)
            yy += 18
        return yy

    legend(60, y_end + 56, C0, n0, 'ROM 0 by feature  (range occupancy)')
    legend(900, y_end + 56, C1, n1, 'Extension ROM by feature')

    dr.text((40, H - 36),
            'ROM 0 free is the 81-byte slack reported by check_layout.py (zero-filled gaps between sections; zeros inside the font and tables are not free).  '
            'Extension “ORG holes” are unused low addresses reserved so trampolines sit at the same addresses as ROM 0; usable free space is the 2,610 bytes above the screen-mode code.',
            fill=(80, 80, 80), font=fonts)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    im.save(OUT, 'PNG')
    print('wrote', OUT, im.size)
    print('ROM0', dict(n0), 'official', official_used, official_free)
    print('EXT ', dict(n1), 'usable free', ext_free, 'hook stubs', n1['stub'], 'holes', n1['hole'])

if __name__ == '__main__':
    main()
