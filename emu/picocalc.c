/* picocalc.c - the PicoCalc machine that runs build/opticos_pc.rom: the
 * shared Z80 core (z80core.h) at 3.5 MHz with a 50 Hz interrupt, 64K RAM
 * (16K write-protected ROM), and these devices:
 *
 *   port $FE  in: Spectrum key matrix (A8-A15 select rows), out: bit 4 beeper
 *   port $1F  in: 0 (no joystick)
 *   port $D1  the display, register B (DV_* in src/sysvars.inc; byte access
 *             for machine code below); in: the hit latch
 *   port $D3  the storage device, register B (ST_*): SAVE, LOAD and VERIFY
 *             blocks as files of TAP blocks, and CAT
 *
 * The display is a 320x320 1-bit bitmap with one Spectrum attribute byte per
 * 8x8 character cell (40x40).  Glyphs come from the display's own 8x8 font
 * (font8x8.h); the ROM's 4x8 font is the Spectrum build's.  This file is
 * the device model only: the rig (tools/rig/rig.py)
 * reads the bitmap and attributes directly, and the firmware draws them on
 * the LCD.
 */
#include <stdint.h>
#include <string.h>

#define CONTEND(a)
#include "z80core.h"
#include "font8x8.h"
#include "storage.h"
#include <stdlib.h>
#include <strings.h>

#define PC_W 320
#define PC_H 320
#define PC_COLS 40
#define PC_ROWS 40

enum { DV_COL, DV_ROW, DV_ATTR, DV_MASK, DV_FLAG, DV_GLYPH, DV_CELL, DV_SCRL, DV_CLS,
       DV_CUR, DV_XL, DV_XH, DV_YL, DV_YH, DV_PLOT, DV_LINE, DV_MOVE,
       /* byte access, for machine code (the ROM doesn't use it): the PicoCalc's
        * answer to the Spectrum's screen memory.  A byte is 8 pixels of a line,
        * bit 7 leftmost; column 0-39, line 0-319 from the top. */
       DV_BCOL,     /* A = byte column, for this line and the lines after (DV_NEXT) */
       DV_BLL, DV_BLH,  /* the line, low and high byte */
       DV_BPUT,     /* store A at the column, then the next column */
       DV_BXOR,     /* XOR A in, then the next column; the hit latch ORs in A AND the old byte */
       DV_HIT,      /* IN: the hit latch, which is then cleared (OUT clears it too) */
       DV_NEXT,     /* the next line, back at the column DV_BCOL set */
       DV_RLD,      /* scroll the line 4 pixels left, A's low nibble coming in at
                     * the right; then the next line */
       DV_PAT,      /* add A to the row pattern (up to 8 bytes; DV_BCOL empties it) */
       DV_FILL };   /* store the row pattern at the column on A lines (0 = 256)
                     * from the line; then the line after them */

static u8 bits[PC_H][PC_W / 8];        /* bit 7 = leftmost pixel */
static u8 attrs[PC_ROWS][PC_COLS];
static u8 keyrows[8];
static int beepstate, beeps;
/* the beeper's edges, for sound: when (T-states since reset, mod 2^32) and
 * the level after it; the firmware drains them each frame (pc_edges) */
#define NEDGE 4096
static u32 edge_t[NEDGE];
static u8 edge_v[NEDGE];
static int nedge;
static struct { u8 col, row, attr, mask, flag; int x, y, px, py; u8 bcol, bcol0, hit, pat[8], npat; u16 bline; } dv;

u8 *pc_bits(void){ return &bits[0][0]; }
u8 *pc_attrs(void){ return &attrs[0][0]; }
const u8 *pc_font(void){ return &font8x8[0][0]; }

/* attribute merge: bits set in mask keep the cell's own value */
static void cell_attr(int col, int row){
  u8 *a = &attrs[row][col]; *a = dv.attr ^ ((dv.attr ^ *a) & dv.mask);
}

static void glyph(u8 ch){
  if (dv.col >= PC_COLS || dv.row >= PC_ROWS || ch < 32 || ch > 127) return;
  const u8 *f = font8x8[ch - 32];
  for (int r = 0; r < 8; r++) {
    u8 g = f[r];
    if (dv.flag & 4) g = ~g;                       /* INVERSE */
    u8 *b = &bits[dv.row * 8 + r][dv.col];
    if (dv.flag & 1) *b ^= g; else *b = g;         /* OVER */
  }
  cell_attr(dv.col, dv.row);
}

/* the cell at COL, ROW inverted (the console cursor) */
static void cursor(void){
  if (dv.col >= PC_COLS || dv.row >= PC_ROWS) return;
  for (int r = 0; r < 8; r++) bits[dv.row * 8 + r][dv.col] ^= 0xFF;
}

/* (x, y) from the bottom left; INVERSE resets, OVER flips */
static void plot(int x, int y){
  if (x < 0 || x >= PC_W || y < 0 || y >= PC_H) return;
  int py = PC_H - 1 - y;
  u8 *b = &bits[py][x >> 3], m = 0x80 >> (x & 7);
  if (dv.flag & 4) *b &= ~m; else if (dv.flag & 1) *b ^= m; else *b |= m;
  cell_attr(x >> 3, py >> 3);
}

/* from (px, py) to (x, y), not plotting the first point: the ROM's Spectrum
 * DRAW algorithm (src/gfx.asm, ln_to), so both machines draw the same pixels */
static void line(int x, int y){
  int dx = x - dv.px, dy = y - dv.py;
  int sx = dx < 0 ? -1 : 1, sy = dy < 0 ? -1 : 1;
  int ax = dx < 0 ? -dx : dx, ay = dy < 0 ? -dy : dy;
  int n, m, mjx, mjy, mnx, mny;                    /* major length, minor length, steps */
  if (ay >= ax) { n = ay; m = ax; mjx = 0; mjy = sy; mnx = sx; mny = 0; }
  else          { n = ax; m = ay; mjx = sx; mjy = 0; mnx = 0; mny = sy; }
  int cx = dv.px, cy = dv.py, e = n / 2;
  for (int i = 0; i < n; i++) {
    e += m;
    if (e >= n) { e -= n; cx += mnx; cy += mny; }
    cx += mjx; cy += mjy;
    plot(cx, cy);
  }
  dv.px = x; dv.py = y;
}

static void display(u8 reg, u8 v){
  switch (reg) {
  case DV_COL: dv.col = v; break;
  case DV_ROW: dv.row = v; break;
  case DV_ATTR: dv.attr = v; break;
  case DV_MASK: dv.mask = v; break;
  case DV_FLAG: dv.flag = v; break;
  case DV_GLYPH: glyph(v); break;
  case DV_CELL: if (dv.col < PC_COLS && dv.row < PC_ROWS) attrs[dv.row][dv.col] = v; break;
  case DV_SCRL:
    memmove(bits[0], bits[8], sizeof bits - sizeof bits[0] * 8);
    memset(bits[PC_H - 8], 0, sizeof bits[0] * 8);
    memmove(attrs[0], attrs[1], sizeof attrs - sizeof attrs[0]);
    memset(attrs[PC_ROWS - 1], v, sizeof attrs[0]);
    break;
  case DV_CLS: memset(bits, 0, sizeof bits); memset(attrs, v, sizeof attrs); break;
  case DV_CUR: cursor(); break;
  case DV_XL: dv.x = (dv.x & 0xFF00) | v; break;
  case DV_XH: dv.x = (dv.x & 0xFF) | v << 8; break;
  case DV_YL: dv.y = (dv.y & 0xFF00) | v; break;
  case DV_YH: dv.y = (dv.y & 0xFF) | v << 8; break;
  case DV_PLOT: plot(dv.x, dv.y); dv.px = dv.x; dv.py = dv.y; break;
  case DV_LINE: line(dv.x, dv.y); break;
  case DV_MOVE: dv.px = dv.x; dv.py = dv.y; break;
  case DV_BCOL: dv.bcol = dv.bcol0 = v; dv.npat = 0; break;
  case DV_BLL: dv.bline = (dv.bline & 0xFF00) | v; break;
  case DV_BLH: dv.bline = (dv.bline & 0xFF) | v << 8; break;
  case DV_BPUT: case DV_BXOR:
    if (dv.bcol < PC_W / 8 && dv.bline < PC_H) {
      u8 *b = &bits[dv.bline][dv.bcol];
      if (reg == DV_BPUT) *b = v; else { dv.hit |= *b & v; *b ^= v; }
    }
    dv.bcol++;
    break;
  case DV_HIT: dv.hit = 0; break;
  case DV_NEXT: dv.bline++; dv.bcol = dv.bcol0; break;
  case DV_RLD:
    if (dv.bline < PC_H) {
      u8 *b = bits[dv.bline];
      for (int i = 0; i < PC_W / 8 - 1; i++) b[i] = b[i] << 4 | b[i + 1] >> 4;
      b[PC_W / 8 - 1] = b[PC_W / 8 - 1] << 4 | (v & 15);
    }
    dv.bline++;
    break;
  case DV_PAT: if (dv.npat < 8) dv.pat[dv.npat++] = v; break;
  case DV_FILL:
    for (int n = v ? v : 256; n--; dv.bline++)
      for (int i = 0; i < dv.npat; i++)
        if (dv.bcol0 + i < PC_W / 8 && dv.bline < PC_H) bits[dv.bline][dv.bcol0 + i] = dv.pat[i];
    break;
  }
}
static u8 display_in(u8 reg){
  if (reg == DV_HIT) { u8 h = dv.hit; dv.hit = 0; return h; }
  return 0xFF;
}

/* ---- storage: each file is a "tape" of TAP blocks (2-byte length, flag,
 * data, XOR parity), named <name>.tap after the header SAVE writes.  As on a
 * real tape, LOAD reads on through the open file, so a loader followed by
 * LOAD "" CODE finds its next block, and the files in name order make one
 * long tape: at the end of a file LOAD reads on into the next, and goes
 * round from the first file once before giving up.  LOAD "name" looks for
 * the block called name along that tape; if name is a file's name instead
 * (or its first 10 characters), it loads that file's first block of the
 * wanted type, so LOAD "OpticOS_examples" loads "examples" from it.  The ROM's SA-BYTES / LD-BYTES hand a
 * block over with OUT (B = ST_SAVE / ST_LOAD; A = flag, IX = start,
 * DE = length, carry = LOAD rather than VERIFY) and read the status back. */
enum { ST_SAVE, ST_LOAD, ST_DIR };
enum { ST_OK, ST_NOMATCH, ST_NONE };          /* status: done; not this block; no block / no card */
#define LG_WANT 0x5B40                        /* src/sysvars.inc: the wanted type, */
#define LG_NAME 0x5B41                        /* and name ($FF = any) */
#define ST_MAXF 64
static st_file *tf;                           /* the open "tape" */
static char tname[ST_NAME];
static int twrite, tidx;                      /* tidx: the open file's place in name order */
static int twrapped;                          /* LOAD has gone round to the first file */
static u8 status;
static char listing[ST_MAXF * (ST_NAME + 1) + 16];
static int lpos;

/* the 10-character Spectrum name at mem[a] -> "name.tap" (trailing spaces
 * dropped, characters a FAT card can't hold made '_') */
static void file_name(u16 a, char *out){
  int n = 10;
  while (n && mem[(u16)(a + n - 1)] == ' ') n--;
  for (int i = 0; i < n; i++) {
    u8 c = mem[(u16)(a + i)];
    out[i] = (c < 33 || c > 126 || strchr("\\/:*?\"<>|", c)) ? '_' : c;
  }
  strcpy(out + n, n ? ".tap" : "_.tap");
}
static int is_tap(const char *n){
  size_t l = strlen(n);
  return l > 4 && n[l - 4] == '.' && (n[l - 3] | 32) == 't' && (n[l - 2] | 32) == 'a' && (n[l - 1] | 32) == 'p';
}
static int cmp_name(const void *a, const void *b){ return strcmp(a, b); }
/* the .tap files, sorted, in names (static: the firmware's core 0 stack is
 * small); -1 if there is no card */
static char names[ST_MAXF][ST_NAME];
static int tap_files(void){
  int n = st_list(names, ST_MAXF), k = 0;
  if (n < 0) return -1;
  for (int i = 0; i < n; i++) if (is_tap(names[i])) memmove(names[k++], names[i], ST_NAME);
  qsort(names, k, ST_NAME, cmp_name);
  return k;
}
static void tape_close(void){ if (tf) st_close(tf); tf = NULL; twrite = 0; }
static int tape_open(const char *name, int write){
  tape_close();
  if (!(tf = st_open(name, write))) return 0;
  strcpy(tname, name); twrite = write;
  return 1;
}

/* open the i-th .tap file in name order */
static int open_file(int i){
  int n = tap_files();
  if (i < 0 || i >= n || !tape_open(names[i], 0)) { tape_close(); return 0; }
  tidx = i;
  return 1;
}
/* the file whose name (without .tap) is want, or starts with it when want
 * has all 10 characters a name can have; -1 if none */
static int match_file(const char *want){
  int n = tap_files(), w = strlen(want);
  for (int i = 0; i < n; i++) {
    int k = strlen(names[i]) - 4;
    if ((k == w || (w == 10 && k > 10)) && !strncasecmp(names[i], want, w)) return i;
  }
  return -1;
}

static u8 save_block(u8 flag){
  u16 ix = rIX.w, len = rDE.w;
  if (flag == 0) {                            /* a header: start the file it names */
    char name[ST_NAME];
    file_name(ix + 1, name);
    if (!tape_open(name, 1)) return ST_NONE;
  } else if (!tf || !twrite) return ST_NONE;  /* data with no header before it */
  u8 h[3] = { (u8)(len + 2), (u8)((len + 2) >> 8), flag }, x = flag, buf[256];
  int ok = st_write(tf, h, 3) == 3;
  for (u32 i = 0; i < len && ok; ) {
    int n = len - i < sizeof buf ? (int)(len - i) : (int)sizeof buf;
    for (int j = 0; j < n; j++) x ^= buf[j] = mem[(u16)(ix + i + j)];
    ok = st_write(tf, buf, n) == n; i += n;
  }
  ok = ok && st_write(tf, &x, 1) == 1;
  if (flag != 0 || !ok) tape_close();         /* the data block ends the file */
  return ok ? ST_OK : ST_NONE;
}

/* skip n bytes of the open file */
static void skip(u32 n){ u8 b[256]; while (n) { int k = n < sizeof b ? n : sizeof b; if (st_read(tf, b, k) != k) return; n -= k; } }

/* LG_NAME := the name of the open file's first header of the given type,
 * if it has one; then back to the start of the file */
static void first_name(u8 type){
  u8 h[3], b[18];
  while (st_read(tf, h, 3) == 3) {
    u32 n = h[0] | h[1] << 8;
    if (n < 2) break;
    if (h[2] == 0 && n == 19) {
      if (st_read(tf, b, 18) != 18) break;    /* the header and its parity */
      if (b[0] == type) { memcpy(&mem[LG_NAME], b + 1, 10); break; }
    } else skip(n - 1);
  }
  st_rewind(tf);
}

static u8 load_block(u8 flag, int load){
  u16 ix = rIX.w, len = rDE.w;
  if (twrite) tape_close();
  if (flag == 0 && mem[LG_NAME] != 0xFF) {    /* LOAD "name": is name a file's? */
    char want[ST_NAME];
    file_name(LG_NAME, want);
    want[strlen(want) - 4] = 0;
    int i = match_file(want);
    if (i >= 0 && (!tf || strcmp(names[i], tname))) {
      if (!open_file(i)) return ST_NONE;
      twrapped = 0;
      first_name(mem[LG_WANT]);
    }
  }
  if (!tf) {                                  /* start at the first file */
    if (flag != 0 || !open_file(0)) return ST_NONE;
    twrapped = 0;
  }
  u8 h[3];
  while (st_read(tf, h, 3) != 3) {            /* the end of a file: on into the next */
    if (flag != 0) { tape_close(); return ST_NONE; }
    if (open_file(tidx + 1)) continue;
    if (!twrapped && open_file(0)) { twrapped = 1; continue; }
    tape_close(); return ST_NONE;
  }
  u32 blen = h[0] | h[1] << 8;
  if (blen < 2) { tape_close(); return ST_NONE; }
  if (h[2] != flag || blen != (u32)len + 2) {
    skip(blen - 1);
    if (flag != 0) tape_close();              /* (as a failed data block below) */
    return ST_NOMATCH;
  }
  u8 x = flag, buf[256], same = 1;
  for (u32 i = 0; i < len; ) {
    int n = len - i < sizeof buf ? (int)(len - i) : (int)sizeof buf;
    if (st_read(tf, buf, n) != n) { tape_close(); return ST_NONE; }
    for (int j = 0; j < n; j++) {
      u16 a = ix + i + j;
      x ^= buf[j];
      if (!load) same &= mem[a] == buf[j];
      else if (a >= 0x4000) mem[a] = buf[j];
    }
    i += n;
  }
  u8 p;
  if (st_read(tf, &p, 1) != 1) { tape_close(); return ST_NONE; }
  if (p != x || !same) {
    if (flag != 0) tape_close();              /* a failed LOAD / VERIFY: start afresh next time */
    return ST_NOMATCH;
  }
  if (flag != 0) twrapped = 0;
  return ST_OK;
}

/* CAT: the .tap files' names, one a line, as a string the ROM reads back */
static void list_files(void){
  int n = tap_files();
  char *o = listing;
  if (n < 0) o += sprintf(o, "No SD card\r");
  else if (n == 0) o += sprintf(o, "No files\r");
  for (int i = 0; i < n; i++) { names[i][strlen(names[i]) - 4] = 0; o += sprintf(o, "%s\r", names[i]); }
  *o = 0; lpos = 0;
}

static void storage(u8 reg, u8 v){
  switch (reg) {
  case ST_SAVE: status = save_block(v); break;
  case ST_LOAD: status = load_block(v, rAF.b.l & 1); break;
  case ST_DIR: list_files(); break;
  }
}
static u8 storage_in(u8 reg){
  if (reg == ST_DIR) return listing[lpos] ? (u8)listing[lpos++] : 0;
  return status;
}

static u8 port_in(u16 port){
  if ((port & 0xFF) == 0x1F) return 0;
  if ((port & 0xFF) == 0xD3) return storage_in(port >> 8);
  if ((port & 0xFF) == 0xD1) return display_in(port >> 8);
  if ((port & 0xFF) == 0xFE) {
    u8 r = 0x1F, hi = port >> 8;
    for (int i = 0; i < 8; i++) if (!(hi & (1 << i))) r &= keyrows[i];
    return r | 0xA0;
  }
  return 0xFF;
}
static void port_out(u16 port, u8 v){
  if ((port & 0xFF) == 0xFE) {
    int b = (v >> 4) & 1;
    if (b != beepstate) {
      beeps++; beepstate = b;
      if (nedge < NEDGE) { edge_t[nedge] = (u32)(TT + T); edge_v[nedge++] = b; }
    }
  } else if ((port & 0xFF) == 0xD1) display(port >> 8, v);
  else if ((port & 0xFF) == 0xD3) storage(port >> 8, v);
}
static void frame_end(void){}

void z_init(void){
  core_reset();
  memset(keyrows, 0x1F, sizeof keyrows);
  memset(bits, 0, sizeof bits); memset(attrs, 0, sizeof attrs); memset(&dv, 0, sizeof dv);
  beepstate = beeps = nedge = 0;
  tape_close(); status = 0; listing[0] = 0; lpos = 0;
}
void z_key(int row, int bit, int down){ if (down) keyrows[row] &= ~(1 << bit); else keyrows[row] |= (1 << bit); }
int z_beeps(void){ int b = beeps; beeps = 0; return b; }
/* the beeper edges since the last call (at most max): their times and the
 * level after each; the rest wait for the next call */
int pc_edges(u32 *t, u8 *v, int max){
  int n = nedge < max ? nedge : max;
  memcpy(t, edge_t, n * sizeof *t); memcpy(v, edge_v, n);
  memmove(edge_t, edge_t + n, (nedge - n) * sizeof *edge_t); memmove(edge_v, edge_v + n, nedge - n);
  nedge -= n;
  return n;
}
int pc_level(void){ return beepstate; }
/* sound samples: the beeper level averaged over each of n equal parts of the
 * len T-states from t0, scaled to 0-amp.  The edges (time, level after) are
 * in order; any at or after the end are applied at the end.  *level is the
 * level at t0, and becomes the level at the end. */
void pc_render(u32 t0, u32 len, int n, const u32 *et, const u8 *ev, int ne, int *level, u8 *out, int amp){
  int e = 0, lv = *level;
  for (int i = 0; i < n; i++) {
    u32 a = (u32)((uint64_t)len * i / n), b = (u32)((uint64_t)len * (i + 1) / n), t = a, hi = 0;
    for (; e < ne && et[e] - t0 < b; e++) {
      u32 x = et[e] - t0;
      if (x < t || x > len) x = t;                /* (from before t0) */
      if (lv) hi += x - t;
      t = x; lv = ev[e];
    }
    if (lv) hi += b - t;
    out[i] = b > a ? (u8)((uint64_t)hi * amp / (b - a)) : (u8)(lv ? amp : 0);
  }
  for (; e < ne; e++) lv = ev[e];
  *level = lv;
}
uint32_t pc_tstates(void){ return (u32)(TT + T); }
