#!/usr/bin/env python3
"""Check OpticOS ROM layout: fixed entry points, no section overruns,
exact 16 KB size.  Prints a per-module byte report against the spec
budget (spec section 8.2).  Usage: check_layout.py build/opticos.sym build/opticos.rom [--md out.md]"""
import re, sys
sym = {}
for line in open(sys.argv[1]):
    m = re.match(r'(\w+)\s+EQU\s+0?([0-9A-F]+)H', line)
    if m: sym[m.group(1)] = int(m.group(2), 16)
rom = open(sys.argv[2], 'rb').read()
ok = True
def fail(msg):
    global ok; ok = False; print('FAIL:', msg)
if len(rom) != 16384: fail('ROM is %d bytes, not 16384' % len(rom))
FIXED = {'RESET': 0x0000, 'RST8': 0x0008, 'RST16': 0x0010, 'RST24': 0x0018, 'RST32': 0x0020,
         'RST40': 0x0028, 'RST48': 0x0030, 'ISR': 0x0038, 'NMI': 0x0066, 'BEEPER': 0x03B5,
         'SA_BYTES': 0x04C2, 'LD_BYTES': 0x0556, 'LD_EDGE2': 0x05E3, 'LD_EDGE1': 0x05E7,
         'POKE_RET': 0x096F, 'CLS': 0x0D6B, 'CL_ALL': 0x0DAF, 'CHAN_OPEN': 0x1601,
         'PR_STRING': 0x203C, 'PIXEL_ADD': 0x22AA, 'm_font_s': 0x3E80}
for k, v in FIXED.items():
    if sym.get(k) != v: fail('%s at %s, expected %04X' % (k, hex(sym.get(k, -1)), v))
if (sym['PR_OUT'] >> 8) != 0x09: fail('PR_OUT must be in page $09 (POKE 23739,111)')
if rom[0x096F] != 0xC9: fail('no RET at $096F')
# each section end must not pass the next fixed point
LIMITS = [('m_isr_e', 0x0066), ('secB_end', 0x03B5), ('secC_end', 0x04C2),
          ('secD_end', 0x0556), ('secE_end', 0x05E3), ('secF_end', 0x096F), ('secG_end', 0x0D6B),
          ('secH_end', 0x0DAF), ('secI_end', 0x1601), ('secJ1_end', 0x203C), ('secJ2_end', 0x22AA),
          ('secK_end', 0x3E80)]
for lab, lim in LIMITS:
    if sym[lab] > lim: fail('%s ends at %04X, past %04X' % (lab, sym[lab], lim))
if sym['GLYPHBUF'] & 0xFF > 0xF8: fail('GLYPHBUF crosses a page')
# module report: (name, spec item, budget, [(start, end), ...])
def r(a, b): return sym[b] - sym[a]
MODS = [
  ('Restarts, NMI, reset, RAM test, sysvars, channels', '1', 380,
      r('RESET', 'm_rst_e') + r('NMI', 'm_nmi_e') + r('m_boot_s', 'm_boot_e') - (sym['chan_init'] - sym['banner'] + 12)),
  ('Boot banner + version text, calls', '2', 40, sym['chan_init'] - sym['banner'] + 12),
  ('Interrupt routine, keyboard scan, key tables', '3', 520, r('ISR', 'm_isr_e') + r('m_kbd_s', 'm_kbd_e')),
  ('64-column print, control codes, colours, scroll, CLS, RST 16', '4', 1000,
      r('m_prt_s', 'm_prt_e') + r('m_cls_s', 'm_cls_e') + 3),
  ('Tape low level: SA-BYTES, LD-BYTES, edges, tape_ret', '8', 380,
      r('m_sav_s', 'm_sav_e') + r('m_ld_s', 'm_ld_e') + r('m_edge_s', 'm_edge_e') + r('m_ld_s2', 'm_ld_e2')),
  ('Sound: BEEPER', '10', 160, r('m_snd_s', 'm_snd_e')),
  ('Errors: RST 8 handler and messages', '26', 450, r('m_err_s', 'm_err_e')),
  ('Tape commands: SAVE / LOAD / VERIFY, CODE, headers, name match', '9', 520, r('m_tcmd_s', 'm_tcmd_e') + r('m_tp_s', 'm_tp_e')),
  ('Legacy loader shim (interpreter, expressions, PRINT)', '27', 650, r('m_leg_s', 'm_leg_e1') + r('m_leg_s2', 'm_leg_e2')),
  ('Number output for the legacy shim and console (pr_dec, pr_hex)', '13', 550, r('m_num_s', 'm_num_e')),
  ('Float core (+ - * /, normalise, compare, conversions, small-int ops)', '12', 1100, r('m_fpc_s', 'm_fpc_e')),
  ('Number <-> string (STR$/PRINT formatting, VAL)', '13', 550, r('m_fpv_s', 'm_fpv_e')),
  ('Transcendentals, byte-code runner, coefficient tables', '14', 950, r('m_fpt_s', 'm_fpt_e') + r('m_fpk_s', 'm_fpk_e')),
  ('Expression evaluator and functions', '18', 1300, r('m_exp_s', 'm_exp_e')),
  ('Variables, arrays, string heap + GC, value and control stacks', '17', 1100, r('m_var_s', 'm_var_e')),
  ('Tokeniser, keyword table, LIST', '15', 1150, r('m_tok_s', 'm_tok_e') + r('m_lst_s', 'm_lst_e') + r('m_tkt_s', 'm_tkt_e') + r('m_tkd_s', 'm_tkd_e')),
  ('Interpreter: run loop, statements, prepass, PROC/FN, TRY', '19', 1900, r('m_bas_s', 'm_bas_e') + r('m_ms2_s', 'm_ms2_e')),
  ('CASE, EXIT, ERROR n [,msg$], CLEAR [n], PROC-name lookup', '19-20', 450,
      r('m_cas_s', 'm_cas_e') + r('m_ext_s', 'm_ext_e') + r('m_err2_s', 'm_err2_e') + r('m_clr_s', 'm_clr_e')),
  ('Direct mode and console: input line with insert/delete/cursor', '25', 250, r('m_con_s', 'm_con_e')),
  ('Line editor: marker, LIST around it, cursor up/down, EDIT', '24', 1400, r('m_edt_s', 'm_edt_e')),
  ('INPUT, DATA / READ / RESTORE', '25', 200, r('m_in_s', 'm_in_e')),
  ('Graphics: PLOT, DRAW, DRAW TO', '11', 620, r('m_gfx_s', 'm_gfx_e')),
  ('BEEP, OUT, DPOKE, CALL, SWAP; start-up chime', '10', 300, r('m_msc_s', 'm_msc_e') + r('m_chm_s', 'm_chm_e')),
  ('String and machine functions: INSTR STRING$ HEX$ UPPER$ ERR$ IN USR DPEEK KEY FREE', '18', 450, r('m_sfn_s', 'm_sfn_e') + r('m_sf2_s', 'm_sf2_e') + r('m_key_s', 'm_key_e')),
  ('Fixed-address stubs (CHAN-OPEN, PR-STRING, PIXEL-ADD, $096F)', '28', 200,
      r('m_stb_s', 'm_stb_e') + r('m_stb_s2', 'm_stb_e2') + r('m_stb_s3', 'm_stb_e3') + 1),
  ('4-pixel font', '7', 384, r('m_font_s', 'm_font_e') if 'm_font_e' in sym else 384),
]
used = sum(m[3] for m in MODS)
nonzero = sum(1 for b in rom if b)
lines = ['| Spec item | Module | Bytes used | Phase budget | % |', '|---|---|---:|---:|---:|']
for name, item, bud, n in MODS:
    lines.append('| %s | %s | %d | %d | %d%% |' % (item, name, n, bud, round(100 * n / bud)))
lines.append('| | **Total (modules built so far)** | **%d** | **%d** | |' % (used, sum(m[2] for m in MODS)))
lines.append('')
lines.append('ROM: 16,384 bytes; %d bytes of code and data placed, %d free (zero-filled gaps).' % (used, 16384 - used))
print('\n'.join(lines))
if '--md' in sys.argv:
    open(sys.argv[sys.argv.index('--md') + 1], 'w').write('\n'.join(lines) + '\n')
print('layout: OK' if ok else 'layout: FAILED')
sys.exit(0 if ok else 1)
