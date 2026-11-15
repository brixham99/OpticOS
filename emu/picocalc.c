/* picocalc.c - the PicoCalc machine that runs build/opticos_pc.rom: the
 * shared Z80 core (z80core.h) at 3.5 MHz with a 50 Hz interrupt, 64K RAM
 * (16K write-protected ROM), and these devices:
 *
 *   port $FE  in: Spectrum key matrix (A8-A15 select rows), out: bit 4 beeper
 *   port $1F  in: 0 (no joystick)
 *   port $D1  out: the display, register B (DV_* in src/sysvars.inc)
 *
 * The display is a 320x320 1-bit bitmap with one Spectrum attribute byte per
 * 4x8 character cell (80x40).  Glyphs come from the ROM's own 4x8 font at
 * $3E80.  This file is the device model only: the rig (tools/rig/pcrig.py)
 * reads the bitmap and attributes directly, and the firmware draws them on
 * the LCD.
 */
#include <stdint.h>
#include <string.h>

#define CONTEND(a)
#include "z80core.h"

#define PC_W 320
#define PC_H 320
#define PC_COLS 80
#define PC_ROWS 40
#define FONT 0x3E80

enum { DV_COL, DV_ROW, DV_ATTR, DV_MASK, DV_FLAG, DV_GLYPH, DV_CELL, DV_SCRL, DV_CLS,
       DV_CUR, DV_XL, DV_XH, DV_YL, DV_YH, DV_PLOT, DV_LINE, DV_MOVE };

static u8 bits[PC_H][PC_W / 8];        /* bit 7 = leftmost pixel */
static u8 attrs[PC_ROWS][PC_COLS];
static u8 keyrows[8];
static int beepstate, beeps;
static struct { u8 col, row, attr, mask, flag; int x, y, px, py; } dv;

u8 *pc_bits(void){ return &bits[0][0]; }
u8 *pc_attrs(void){ return &attrs[0][0]; }

/* attribute merge: bits set in mask keep the cell's own value */
static void cell_attr(int col, int row){
  u8 *a = &attrs[row][col]; *a = dv.attr ^ ((dv.attr ^ *a) & dv.mask);
}

static void glyph(u8 ch){
  if (dv.col >= PC_COLS || dv.row >= PC_ROWS || ch < 32 || ch > 127) return;
  const u8 *f = &mem[FONT + 8 * ((ch - 32) >> 1)];
  int shift = (dv.col & 1) ? 0 : 4;               /* even columns: high nibble */
  for (int r = 0; r < 8; r++) {
    u8 g = (ch & 1) ? f[r] & 15 : f[r] >> 4;
    if (dv.flag & 4) g = ~g & 15;                  /* INVERSE */
    u8 *b = &bits[dv.row * 8 + r][dv.col >> 1];
    if (dv.flag & 1) *b ^= g << shift;             /* OVER */
    else *b = (*b & ~(15 << shift)) | g << shift;
  }
  cell_attr(dv.col, dv.row);
}

/* the cell at COL, ROW inverted (the console cursor) */
static void cursor(void){
  if (dv.col >= PC_COLS || dv.row >= PC_ROWS) return;
  int shift = (dv.col & 1) ? 0 : 4;
  for (int r = 0; r < 8; r++) bits[dv.row * 8 + r][dv.col >> 1] ^= 15 << shift;
}

/* (x, y) from the bottom left; INVERSE resets, OVER flips */
static void plot(int x, int y){
  if (x < 0 || x >= PC_W || y < 0 || y >= PC_H) return;
  int py = PC_H - 1 - y;
  u8 *b = &bits[py][x >> 3], m = 0x80 >> (x & 7);
  if (dv.flag & 4) *b &= ~m; else if (dv.flag & 1) *b ^= m; else *b |= m;
  cell_attr(x >> 2, py >> 3);
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
  }
}

static u8 port_in(u16 port){
  if ((port & 0xFF) == 0x1F) return 0;
  if ((port & 0xFF) == 0xFE) {
    u8 r = 0x1F, hi = port >> 8;
    for (int i = 0; i < 8; i++) if (!(hi & (1 << i))) r &= keyrows[i];
    return r | 0xA0;
  }
  return 0xFF;
}
static void port_out(u16 port, u8 v){
  if ((port & 0xFF) == 0xFE) {
    int b = (v >> 4) & 1; if (b != beepstate) { beeps++; beepstate = b; }
  } else if ((port & 0xFF) == 0xD1) display(port >> 8, v);
}
static void frame_end(void){}

void z_init(void){
  core_reset();
  memset(keyrows, 0x1F, sizeof keyrows);
  memset(bits, 0, sizeof bits); memset(attrs, 0, sizeof attrs); memset(&dv, 0, sizeof dv);
  beepstate = beeps = 0;
}
void z_key(int row, int bit, int down){ if (down) keyrows[row] &= ~(1 << bit); else keyrows[row] |= (1 << bit); }
int z_beeps(void){ int b = beeps; beeps = 0; return b; }
