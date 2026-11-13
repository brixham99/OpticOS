/* z80.c - OpticOS headless rig: full Z80 core plus a 48K Spectrum shell.
 *
 * Covers the whole instruction set: main, CB, ED, DD/FD (IX/IY incl. the
 * undocumented IXH/IXL forms), DDCB/FDCB (incl. the undocumented register
 * copies), SLL, IN F,(C), OUT (C),0, the undocumented X/Y flags and MEMPTR
 * (WZ) for BIT n,(HL).  Spectrum side: 16K write-protected ROM, 50 Hz
 * INT (IM 0/1/2), keyboard matrix, Kempston, border/beeper/MIC out with an
 * edge recorder, EAR in fed from a pulse list (built from TAP files by
 * rig.py), approximate ULA contention.  A CP/M mode (BDOS at 5) runs
 * zexdoc/zexall.  Driven from Python via ctypes.
 */
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
typedef uint8_t u8; typedef uint16_t u16; typedef uint32_t u32; typedef int8_t s8;
typedef union { u16 w; struct { u8 l, h; } b; } pair;

static u8 mem[65536];
static pair rAF, rBC, rDE, rHL, rIX, rIY, rSP, rPC, rWZ, AF_, BC_, DE_, HL_;
static u8 I, R, R7;
static int IFF1, IFF2, IM, halted, ei_delay;
static long T;              /* T-state within the current frame */
static long long TT;        /* T-states at start of current frame */
static int rom_protect = 1, contention = 1, cpm = 0;
static u8 keyrows[8] = {0x1F,0x1F,0x1F,0x1F,0x1F,0x1F,0x1F,0x1F};
static u8 kempston;
static int border, beepstate, beeps, micstate;
static long halt_t;
static u8 sz53[256], sz53p[256], par[256];
static const u8 cdelay[8] = {6,5,4,3,2,1,0,0};
#define FRAME 69888

#define A rAF.b.h
#define F rAF.b.l
#define B rBC.b.h
#define C rBC.b.l
#define D rDE.b.h
#define E rDE.b.l
#define H rHL.b.h
#define L rHL.b.l
#define FC 0x01
#define FN 0x02
#define FP 0x04
#define F3 0x08
#define FH 0x10
#define F5 0x20
#define FZ 0x40
#define FS 0x80

/* ---------- EAR input (tape) ---------- */
static u32 *ear_p; static long ear_n, ear_i; static long long ear_next; static int ear_level, ear_on;
void z_ear_load(u32 *p, long n){ free(ear_p); ear_p = malloc(n > 0 ? n * 4 : 4); memcpy(ear_p, p, n * 4); ear_n = n; ear_i = 0; ear_on = 0; ear_level = 0; }
void z_ear_play(int on){ if (on && !ear_on && ear_i < ear_n) ear_next = TT + T + (ear_p[ear_i] & 0x7FFFFFFF); ear_on = on; }
long z_ear_pos(void){ return ear_i; }
static void ear_update(void){
  if (!ear_on) return;
  long long now = TT + T;
  while (ear_i < ear_n && ear_next <= now) {
    if (!(ear_p[ear_i] & 0x80000000u)) ear_level ^= 1;
    ear_i++;
    if (ear_i < ear_n) ear_next += ear_p[ear_i] & 0x7FFFFFFF; else ear_on = 0;
  }
}
/* ---------- MIC output recorder ---------- */
static u32 *mic_buf; static long mic_n, mic_cap; static long long mic_last; static int mic_rec, mic_bit = 3;
void z_mic_bit(int b){ mic_bit = b; }
void z_mic_record(int on){ mic_rec = on; mic_n = 0; mic_last = TT + T; }
long z_mic_count(void){ return mic_n; }
u32 *z_mic_buf(void){ return mic_buf; }

static inline void contend(u16 a){
  if (contention && (a & 0xC000) == 0x4000) {
    long t = T - 14335;
    if (t >= 0 && t < 192 * 224) { int p = t % 224; if (p < 128) T += cdelay[p & 7]; }
  }
}
static inline u8 rd(u16 a){ contend(a); return mem[a]; }
static inline void wr(u16 a, u8 v){ contend(a); if (a >= 0x4000 || !rom_protect) mem[a] = v; }
static inline u16 rd16(u16 a){ u8 l = rd(a); return l | (rd((u16)(a + 1)) << 8); }
static inline void wr16(u16 a, u16 v){ wr(a, v & 0xFF); wr((u16)(a + 1), v >> 8); }
static inline u8 fetch(void){ return rd(rPC.w++); }
static inline u16 fetch16(void){ u16 v = rd16(rPC.w); rPC.w += 2; return v; }
static inline void push(u16 v){ rSP.w -= 2; wr16(rSP.w, v); }
static inline u16 pop(void){ u16 v = rd16(rSP.w); rSP.w += 2; return v; }
static inline void incR(void){ R = (R + 1) & 0x7F; }

static u8 port_in(u16 port){
  if (cpm) return 0xFF;
  if ((port & 0xFF) == 0x1F) return kempston;
  if (!(port & 1)) {
    u8 r = 0x1F, hi = port >> 8;
    for (int i = 0; i < 8; i++) if (!(hi & (1 << i))) r &= keyrows[i];
    ear_update();
    return r | 0xA0 | (ear_level ? 0x40 : 0);
  }
  return 0xFF;
}
static void port_out(u16 port, u8 v){
  if (cpm) return;
  if (!(port & 1)) {
    border = v & 7;
    int b = (v >> 4) & 1; if (b != beepstate) { beeps++; beepstate = b; }
    int m = (v >> mic_bit) & 1;
    if (m != micstate) {
      micstate = m;
      if (mic_rec) {
        long long now = TT + T;
        if (mic_n >= mic_cap) { mic_cap = mic_cap ? mic_cap * 2 : 65536; mic_buf = realloc(mic_buf, mic_cap * 4); }
        mic_buf[mic_n++] = (u32)(now - mic_last); mic_last = now;
      }
    }
  }
}

/* ---------- ALU ---------- */
static void add8(u8 v, int c){ u32 r = A + v + c; F = ((r >> 8) & 1) | ((A ^ v ^ r) & FH) | ((((A ^ ~v) & (A ^ r)) & 0x80) ? FP : 0) | sz53[r & 0xFF]; A = r; }
static void sub8(u8 v, int c){ u32 r = (u32)A - v - c; F = ((r >> 8) & 1) | FN | ((A ^ v ^ r) & FH) | ((((A ^ v) & (A ^ r)) & 0x80) ? FP : 0) | sz53[r & 0xFF]; A = r; }
static void cp8(u8 v){ u8 a = A; sub8(v, 0); A = a; F = (F & ~(F3 | F5)) | (v & (F3 | F5)); }
static void alu(int op, u8 v){
  switch (op) {
    case 0: add8(v, 0); break; case 1: add8(v, F & FC); break;
    case 2: sub8(v, 0); break; case 3: sub8(v, F & FC); break;
    case 4: A &= v; F = sz53p[A] | FH; break;
    case 5: A ^= v; F = sz53p[A]; break;
    case 6: A |= v; F = sz53p[A]; break;
    case 7: cp8(v); break;
  }
}
static u8 inc8(u8 v){ u8 r = v + 1; F = (F & FC) | sz53[r] | ((r & 0x0F) ? 0 : FH) | (r == 0x80 ? FP : 0); return r; }
static u8 dec8(u8 v){ u8 r = v - 1; F = (F & FC) | FN | sz53[r] | ((v & 0x0F) ? 0 : FH) | (r == 0x7F ? FP : 0); return r; }
static u16 add16(u16 a, u16 b){ u32 r = a + b; rWZ.w = a + 1; F = (F & (FS | FZ | FP)) | ((r >> 16) & 1) | (((a ^ b ^ r) >> 8) & FH) | ((r >> 8) & (F3 | F5)); return r; }
static u16 adc16(u16 a, u16 b){ u32 r = a + b + (F & FC); rWZ.w = a + 1; u16 x = r;
  F = ((r >> 16) & 1) | (((a ^ b ^ r) >> 8) & FH) | ((((a ^ ~b) & (a ^ r)) & 0x8000) ? FP : 0) | ((x >> 8) & (FS | F3 | F5)) | (x ? 0 : FZ); return x; }
static u16 sbc16(u16 a, u16 b){ u32 r = (u32)a - b - (F & FC); rWZ.w = a + 1; u16 x = r;
  F = FN | ((r >> 16) & 1) | (((a ^ b ^ r) >> 8) & FH) | ((((a ^ b) & (a ^ r)) & 0x8000) ? FP : 0) | ((x >> 8) & (FS | F3 | F5)) | (x ? 0 : FZ); return x; }
static u8 rot(int op, u8 v){
  u8 r, c;
  switch (op) {
    case 0: c = v >> 7; r = (v << 1) | c; break;             /* RLC */
    case 1: c = v & 1; r = (v >> 1) | (c << 7); break;        /* RRC */
    case 2: c = v >> 7; r = (v << 1) | (F & FC); break;       /* RL */
    case 3: c = v & 1; r = (v >> 1) | ((F & FC) << 7); break; /* RR */
    case 4: c = v >> 7; r = v << 1; break;                    /* SLA */
    case 5: c = v & 1; r = (v >> 1) | (v & 0x80); break;      /* SRA */
    case 6: c = v >> 7; r = (v << 1) | 1; break;              /* SLL */
    default: c = v & 1; r = v >> 1; break;                    /* SRL */
  }
  F = sz53p[r] | c; return r;
}
static void bit8(int b, u8 v, u8 xy){
  u8 r = v & (1 << b);
  F = (F & FC) | FH | (xy & (F3 | F5)) | (r ? (r & FS) : (FZ | FP));
}
static void daa(void){
  u8 a = A, cor = 0, c = F & FC;
  if ((F & FH) || (a & 0x0F) > 9) cor |= 0x06;
  if (c || a > 0x99) { cor |= 0x60; c = FC; }
  if (F & FN) { F = (F & FN) | (((a ^ (a - cor)) & FH)); A = a - cor; }
  else { F = ((a ^ (a + cor)) & FH); A = a + cor; }
  F |= c | sz53p[A];
}
static int cond(int y){
  switch (y) {
    case 0: return !(F & FZ); case 1: return F & FZ; case 2: return !(F & FC); case 3: return F & FC;
    case 4: return !(F & FP); case 5: return F & FP; case 6: return !(F & FS); default: return F & FS;
  }
}

/* ---------- register access with index mode ---------- */
static pair *XY;   /* HL, IX or IY for the current instruction */
static int idx;    /* 0 = no prefix */
static u8 getr(int r){
  switch (r) { case 0: return B; case 1: return C; case 2: return D; case 3: return E;
    case 4: return XY->b.h; case 5: return XY->b.l; case 7: return A; }
  return 0;
}
static void setr(int r, u8 v){
  switch (r) { case 0: B = v; break; case 1: C = v; break; case 2: D = v; break; case 3: E = v; break;
    case 4: XY->b.h = v; break; case 5: XY->b.l = v; break; case 7: A = v; break; }
}
static u8 getr_plain(int r){ pair *s = XY; XY = &rHL; u8 v = getr(r); XY = s; return v; }
static void setr_plain(int r, u8 v){ pair *s = XY; XY = &rHL; setr(r, v); XY = s; }
static u16 memaddr(void){ /* address for (HL) / (IX+d) */
  if (!idx) return rHL.w;
  s8 d = (s8)fetch(); T += 8; rWZ.w = XY->w + d; return rWZ.w;
}
static pair *rp(int p){ switch (p) { case 0: return &rBC; case 1: return &rDE; case 2: return XY; } return &rSP; }
static pair *rp2(int p){ switch (p) { case 0: return &rBC; case 1: return &rDE; case 2: return XY; } return &rAF; }

static void do_cb(void){
  u16 a = 0; u8 op, v;
  if (idx) { s8 d = (s8)fetch(); a = XY->w + d; rWZ.w = a; op = fetch(); T += 4; }
  else { op = fetch(); incR(); }
  int x = op >> 6, y = (op >> 3) & 7, z = op & 7;
  if (idx || z == 6) {
    if (!idx) a = rHL.w;
    v = rd(a);
    if (x == 1) { bit8(y, v, idx ? (a >> 8) : rWZ.b.h); T += 8; return; }
    if (x == 0) v = rot(y, v); else if (x == 2) v &= ~(1 << y); else v |= 1 << y;
    wr(a, v); T += 11;
    if (idx && z != 6) setr_plain(z, v);
    return;
  }
  v = getr(z);
  if (x == 0) setr(z, rot(y, v));
  else if (x == 1) bit8(y, v, v);
  else if (x == 2) setr(z, v & ~(1 << y));
  else setr(z, v | (1 << y));
  T += 4;
}

static void blockop(int y, int z){
  /* y: 4=I 5=D 6=IR 7=DR ; z: 0 LD 1 CP 2 IN 3 OUT */
  int dir = (y & 1) ? -1 : 1, rep = y >= 6;
  switch (z) {
  case 0: { u8 v = rd(rHL.w); wr(rDE.w, v); rHL.w += dir; rDE.w += dir; rBC.w--;
    u8 n = v + A; F = (F & (FS | FZ | FC)) | (rBC.w ? FP : 0) | (n & F3) | ((n << 4) & F5);
    T += 12; if (rep && rBC.w) { rPC.w -= 2; rWZ.w = rPC.w + 1; T += 5; } break; }
  case 1: { u8 v = rd(rHL.w), r = A - v; rHL.w += dir; rBC.w--; rWZ.w += dir;
    F = (F & FC) | FN | (sz53[r] & ~(F3 | F5)) | ((A ^ v ^ r) & FH) | (rBC.w ? FP : 0);
    u8 n = r - ((F & FH) ? 1 : 0); F |= (n & F3) | ((n << 4) & F5);
    T += 12; if (rep && rBC.w && r) { rPC.w -= 2; rWZ.w = rPC.w + 1; T += 5; } break; }
  case 2: { rWZ.w = rBC.w + dir; u8 v = port_in(rBC.w); wr(rHL.w, v); B--; rHL.w += dir;
    u32 k = v + ((C + dir) & 0xFF);
    F = sz53[B] | ((v & 0x80) ? FN : 0) | (k > 255 ? (FH | FC) : 0) | (par[(k & 7) ^ B] ? FP : 0);
    T += 12; if (rep && B) { rPC.w -= 2; T += 5; } break; }
  case 3: { u8 v = rd(rHL.w); B--; rWZ.w = rBC.w + dir; port_out(rBC.w, v); rHL.w += dir;
    u32 k = v + L;
    F = sz53[B] | ((v & 0x80) ? FN : 0) | (k > 255 ? (FH | FC) : 0) | (par[(k & 7) ^ B] ? FP : 0);
    T += 12; if (rep && B) { rPC.w -= 2; T += 5; } break; }
  }
}

static void do_ed(void){
  u8 op = fetch(); incR();
  int x = op >> 6, y = (op >> 3) & 7, z = op & 7, p = y >> 1, q = y & 1;
  XY = &rHL; idx = 0;
  if (x == 1) {
    switch (z) {
    case 0: { rWZ.w = rBC.w + 1; u8 v = port_in(rBC.w); if (y != 6) setr(y, v); F = (F & FC) | sz53p[v]; T += 8; return; }
    case 1: rWZ.w = rBC.w + 1; port_out(rBC.w, y == 6 ? 0 : getr(y)); T += 8; return;
    case 2: if (q) rHL.w = adc16(rHL.w, rp(p)->w); else rHL.w = sbc16(rHL.w, rp(p)->w); T += 11; return;
    case 3: { u16 a = fetch16(); rWZ.w = a + 1; if (q) rp(p)->w = rd16(a); else wr16(a, rp(p)->w); T += 16; return; }
    case 4: { u8 v = A; A = 0; sub8(v, 0); T += 4; return; }
    case 5: IFF1 = IFF2; rPC.w = pop(); rWZ.w = rPC.w; T += 10; return;
    case 6: { static const int m[8] = {0,0,1,2,0,0,1,2}; IM = m[y]; T += 4; return; }
    case 7:
      switch (y) {
      case 0: I = A; T += 5; return;
      case 1: R = A & 0x7F; R7 = A & 0x80; T += 5; return;
      case 2: A = I; F = (F & FC) | sz53[A] | (IFF2 ? FP : 0); T += 5; return;
      case 3: A = (R & 0x7F) | R7; F = (F & FC) | sz53[A] | (IFF2 ? FP : 0); T += 5; return;
      case 4: { u8 v = rd(rHL.w); wr(rHL.w, (A << 4) | (v >> 4)); A = (A & 0xF0) | (v & 0x0F); F = (F & FC) | sz53p[A]; rWZ.w = rHL.w + 1; T += 14; return; }
      case 5: { u8 v = rd(rHL.w); wr(rHL.w, (v << 4) | (A & 0x0F)); A = (A & 0xF0) | (v >> 4); F = (F & FC) | sz53p[A]; rWZ.w = rHL.w + 1; T += 14; return; }
      default: T += 4; return;
      }
    }
  }
  if (x == 2 && z <= 3 && y >= 4) { blockop(y, z); return; }
  T += 4; /* NONI */
}

static void exec(void){
  u8 op = fetch(); incR();
  idx = 0; XY = &rHL;
  while (op == 0xDD || op == 0xFD) {
    idx = op == 0xDD ? 1 : 2; XY = idx == 1 ? &rIX : &rIY; T += 4;
    op = fetch(); incR();
  }
  if (op == 0xED) { T += 4; do_ed(); return; }
  if (op == 0xCB) { T += 4; do_cb(); return; }
  int x = op >> 6, y = (op >> 3) & 7, z = op & 7, p = y >> 1, q = y & 1;
  switch (x) {
  case 0:
    switch (z) {
    case 0:
      switch (y) {
      case 0: T += 4; return;
      case 1: { pair t = rAF; rAF = AF_; AF_ = t; T += 4; return; }
      case 2: { s8 d = (s8)fetch(); if (--B) { rPC.w += d; rWZ.w = rPC.w; T += 13; } else T += 8; return; }
      case 3: { s8 d = (s8)fetch(); rPC.w += d; rWZ.w = rPC.w; T += 12; return; }
      default: { s8 d = (s8)fetch(); if (cond(y - 4)) { rPC.w += d; rWZ.w = rPC.w; T += 12; } else T += 7; return; }
      }
    case 1:
      if (!q) { rp(p)->w = fetch16(); T += 10; } else { XY->w = add16(XY->w, rp(p)->w); T += 11; }
      return;
    case 2:
      switch (y) {
      case 0: wr(rBC.w, A); rWZ.b.l = rBC.w + 1; rWZ.b.h = A; T += 7; return;
      case 1: A = rd(rBC.w); rWZ.w = rBC.w + 1; T += 7; return;
      case 2: wr(rDE.w, A); rWZ.b.l = rDE.w + 1; rWZ.b.h = A; T += 7; return;
      case 3: A = rd(rDE.w); rWZ.w = rDE.w + 1; T += 7; return;
      case 4: { u16 a = fetch16(); wr16(a, XY->w); rWZ.w = a + 1; T += 16; return; }
      case 5: { u16 a = fetch16(); XY->w = rd16(a); rWZ.w = a + 1; T += 16; return; }
      case 6: { u16 a = fetch16(); wr(a, A); rWZ.b.l = a + 1; rWZ.b.h = A; T += 13; return; }
      case 7: { u16 a = fetch16(); A = rd(a); rWZ.w = a + 1; T += 13; return; }
      }
    case 3: if (!q) rp(p)->w++; else rp(p)->w--; T += 6; return;
    case 4: case 5:
      if (y == 6) { u16 a = memaddr(); u8 v = rd(a); wr(a, z == 4 ? inc8(v) : dec8(v)); T += 11; }
      else { setr(y, z == 4 ? inc8(getr(y)) : dec8(getr(y))); T += 4; }
      return;
    case 6:
      if (y == 6) { u16 a; if (idx) { s8 d = (s8)fetch(); a = XY->w + d; rWZ.w = a; T += 5; } else a = rHL.w; wr(a, fetch()); T += 10; }
      else { setr(y, fetch()); T += 7; }
      return;
    case 7:
      switch (y) {
      case 0: A = (A << 1) | (A >> 7); F = (F & (FS | FZ | FP)) | (A & (F3 | F5 | FC)); break;
      case 1: F = (F & (FS | FZ | FP)) | (A & FC); A = (A >> 1) | (A << 7); F |= A & (F3 | F5); break;
      case 2: { u8 c = A >> 7; A = (A << 1) | (F & FC); F = (F & (FS | FZ | FP)) | (A & (F3 | F5)) | c; break; }
      case 3: { u8 c = A & 1; A = (A >> 1) | (F << 7); F = (F & (FS | FZ | FP)) | (A & (F3 | F5)) | c; break; }
      case 4: daa(); break;
      case 5: A = ~A; F = (F & (FS | FZ | FP | FC)) | FH | FN | (A & (F3 | F5)); break;
      case 6: F = (F & (FS | FZ | FP)) | FC | (A & (F3 | F5)); break;
      case 7: F = (F & (FS | FZ | FP)) | ((F & FC) ? FH : FC) | (A & (F3 | F5)); break;
      }
      T += 4; return;
    }
  case 1:
    if (op == 0x76) { halted = 1; rPC.w--; T += 4; return; }
    if (y == 6) { u16 a = memaddr(); wr(a, getr_plain(z)); T += 7; }
    else if (z == 6) { u16 a = memaddr(); setr_plain(y, rd(a)); T += 7; }
    else { setr(y, getr(z)); T += 4; }
    return;
  case 2:
    if (z == 6) { u16 a = memaddr(); alu(y, rd(a)); T += 7; } else { alu(y, getr(z)); T += 4; }
    return;
  case 3:
    switch (z) {
    case 0: if (cond(y)) { rPC.w = pop(); rWZ.w = rPC.w; T += 11; } else T += 5; return;
    case 1:
      if (!q) { rp2(p)->w = pop(); T += 10; return; }
      switch (p) {
      case 0: rPC.w = pop(); rWZ.w = rPC.w; T += 10; return;
      case 1: { pair t; t = rBC; rBC = BC_; BC_ = t; t = rDE; rDE = DE_; DE_ = t; t = rHL; rHL = HL_; HL_ = t; T += 4; return; }
      case 2: rPC.w = XY->w; T += 4; return;
      case 3: rSP.w = XY->w; T += 6; return;
      }
    case 2: { u16 a = fetch16(); rWZ.w = a; if (cond(y)) rPC.w = a; T += 10; return; }
    case 3:
      switch (y) {
      case 0: rPC.w = fetch16(); rWZ.w = rPC.w; T += 10; return;
      case 2: { u8 n = fetch(); rWZ.b.l = n + 1; rWZ.b.h = A; port_out((A << 8) | n, A); T += 11; return; }
      case 3: { u8 n = fetch(); u16 pt = (A << 8) | n; rWZ.w = pt + 1; A = port_in(pt); T += 11; return; }
      case 4: { u16 v = rd16(rSP.w); wr16(rSP.w, XY->w); XY->w = v; rWZ.w = v; T += 19; return; }
      case 5: { pair t = rDE; rDE = rHL; rHL = t; T += 4; return; }
      case 6: IFF1 = IFF2 = 0; T += 4; return;
      case 7: IFF1 = IFF2 = 1; ei_delay = 1; T += 4; return;
      }
      return;
    case 4: { u16 a = fetch16(); rWZ.w = a; if (cond(y)) { push(rPC.w); rPC.w = a; T += 17; } else T += 10; return; }
    case 5:
      if (!q) { push(rp2(p)->w); T += 11; return; }
      { u16 a = fetch16(); rWZ.w = a; push(rPC.w); rPC.w = a; T += 17; return; }
    case 6: alu(y, fetch()); T += 7; return;
    case 7:
      if (cpm) { /* CP/M BDOS shim never needs RSTs; fall through */ }
      push(rPC.w); rPC.w = y * 8; rWZ.w = rPC.w; T += 11; return;
    }
  }
}

static void interrupt(void){
  if (halted) { halted = 0; rPC.w++; }
  IFF1 = IFF2 = 0; incR();
  push(rPC.w);
  if (IM == 2) { u16 v = (I << 8) | 0xFF; rPC.w = rd16(v); T += 19; }
  else { rPC.w = 0x38; T += 13; }
}
static void nmi(void){
  if (halted) { halted = 0; rPC.w++; }
  IFF1 = 0; incR(); push(rPC.w); rPC.w = 0x66; T += 11;
}

/* ---------- Python interface ---------- */
static void tables(void){
  for (int i = 0; i < 256; i++) {
    int p = 1; for (int b = 0; b < 8; b++) if (i & (1 << b)) p ^= 1;
    par[i] = p; sz53[i] = (i & (FS | F3 | F5)) | (i ? 0 : FZ); sz53p[i] = sz53[i] | (p ? FP : 0);
  }
}
void z_init(void){
  tables(); memset(mem, 0, sizeof mem);
  rAF.w = rBC.w = rDE.w = rHL.w = rIX.w = rIY.w = 0xFFFF; rSP.w = 0xFFFF; rPC.w = 0;
  AF_.w = BC_.w = DE_.w = HL_.w = 0xFFFF; rWZ.w = 0; I = R = R7 = 0;
  IFF1 = IFF2 = IM = halted = ei_delay = 0; T = 0; TT = 0;
  for (int i = 0; i < 8; i++) keyrows[i] = 0x1F;
  kempston = 0; border = 7; beeps = beepstate = micstate = 0; ear_on = 0; ear_level = 0; mic_rec = 0;
  rom_protect = 1; contention = 1; cpm = 0;
}
u8 *z_mem(void){ return mem; }
void z_setpc(int v){ rPC.w = v; halted = 0; }
int z_getpc(void){ return rPC.w; }
void z_setsp(int v){ rSP.w = v; }
int z_getsp(void){ return rSP.w; }
/* regs: AF BC DE HL IX IY SP PC AF' BC' DE' HL' I R IFF1 IFF2 IM */
void z_getregs(int *o){
  o[0]=rAF.w; o[1]=rBC.w; o[2]=rDE.w; o[3]=rHL.w; o[4]=rIX.w; o[5]=rIY.w; o[6]=rSP.w; o[7]=rPC.w;
  o[8]=AF_.w; o[9]=BC_.w; o[10]=DE_.w; o[11]=HL_.w; o[12]=I; o[13]=(R&0x7F)|R7; o[14]=IFF1; o[15]=IFF2; o[16]=IM;
}
void z_setregs(int *o){
  rAF.w=o[0]; rBC.w=o[1]; rDE.w=o[2]; rHL.w=o[3]; rIX.w=o[4]; rIY.w=o[5]; rSP.w=o[6]; rPC.w=o[7];
  AF_.w=o[8]; BC_.w=o[9]; DE_.w=o[10]; HL_.w=o[11]; I=o[12]; R=o[13]&0x7F; R7=o[13]&0x80; IFF1=o[14]; IFF2=o[15]; IM=o[16]; halted=0;
}
void z_key(int row, int bit, int down){ if (down) keyrows[row] &= ~(1 << bit); else keyrows[row] |= (1 << bit); }
void z_kempston(int v){ kempston = v; }
int z_border(void){ return border; }
int z_beeps(void){ int b = beeps; beeps = 0; return b; }
long z_halt_t(void){ return halt_t; }
long long z_tstates(void){ return TT + T; }
void z_options(int protect, int cont){ rom_protect = protect; contention = cont; }
void z_nmi(void){ nmi(); }

static int int_pending;
static void step(void){
  if (int_pending && T < 32 && IFF1 && !ei_delay) { interrupt(); int_pending = 0; return; }
  ei_delay = 0;
  if (halted) {
    if (halt_t < 0) halt_t = T;
    long lim = (int_pending && T < 32) ? 32 : FRAME;
    long n = (lim - T + 3) / 4; if (n < 1) n = 1; T += n * 4; R = (R + n) & 0x7F; return;
  }
  exec();
}
/* Run one 50 Hz frame (INT asserted for the first 32 T). */
int z_frame(void){
  halt_t = -1; int_pending = 1;
  while (T < FRAME) step();
  T -= FRAME; TT += FRAME; ear_update();
  return 0;
}
/* Run until PC == stop or n T-states elapse.  Returns 1 if stopped. */
int z_run_until(int stop, long long n){
  long long end = TT + T + n;
  while (TT + T < end) {
    if (T >= FRAME) { T -= FRAME; TT += FRAME; int_pending = 1; halt_t = -1; }
    if (rPC.w == stop && !halted) return 1;
    step();
  }
  return 0;
}
/* As z_run_until, with two stop addresses: returns 1 or 2 for the one hit. */
int z_run_until2(int s1, int s2, long long n){
  long long end = TT + T + n;
  while (TT + T < end) {
    if (T >= FRAME) { T -= FRAME; TT += FRAME; int_pending = 1; halt_t = -1; }
    if (!halted) { if (rPC.w == s1) return 1; if (rPC.w == s2) return 2; }
    step();
  }
  return 0;
}
/* Single instruction step (no interrupts). Returns T-states used. */
int z_step(void){ long t = T; exec(); ei_delay = 0; return (int)(T - t); }

/* CP/M harness for zexdoc/zexall: load .com at $100, BDOS 2/9 at $0005. */
int z_cpm_run(long long maxinst){
  cpm = 1; rom_protect = 0; contention = 0;
  mem[0] = 0x76; mem[5] = 0xC9; rSP.w = 0xF000; rPC.w = 0x100; halted = 0; IFF1 = IFF2 = 0;
  for (long long i = 0; i < maxinst; i++) {
    if (rPC.w == 5) {
      if (C == 2) { putchar(E); fflush(stdout); }
      else if (C == 9) { for (u16 a = rDE.w; mem[a] != '$'; a++) putchar(mem[a]); fflush(stdout); }
    }
    if (rPC.w == 0) return 0;
    exec(); if (T > 1000000000) T = 0;
  }
  return 1;
}
