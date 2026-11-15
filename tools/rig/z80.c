/* z80.c - OpticOS headless rig: the 48K Spectrum shell around the shared
 * Z80 core (emu/z80core.h).  16K write-protected ROM, 50 Hz INT (IM 0/1/2),
 * keyboard matrix, Kempston, border/beeper/MIC out with an edge recorder,
 * EAR in fed from a pulse list (built from TAP files by rig.py), approximate
 * ULA contention.  A CP/M mode (BDOS at 5) runs zexdoc/zexall.  Driven from
 * Python via ctypes.
 */
#include <stdio.h>
#include <stdlib.h>

static int contention = 1, cpm = 0;
static const unsigned char cdelay[8] = {6,5,4,3,2,1,0,0};
#define CONTEND(a) contend(a)
static inline void contend(unsigned short a);
#include "../../emu/z80core.h"

static u8 keyrows[8] = {0x1F,0x1F,0x1F,0x1F,0x1F,0x1F,0x1F,0x1F};
static u8 kempston;
static int border, beepstate, beeps, micstate;

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

static void frame_end(void){ ear_update(); }

void z_init(void){
  core_reset();
  for (int i = 0; i < 8; i++) keyrows[i] = 0x1F;
  kempston = 0; border = 7; beeps = beepstate = micstate = 0; ear_on = 0; ear_level = 0; mic_rec = 0;
  contention = 1; cpm = 0;
}
void z_key(int row, int bit, int down){ if (down) keyrows[row] &= ~(1 << bit); else keyrows[row] |= (1 << bit); }
void z_kempston(int v){ kempston = v; }
int z_border(void){ return border; }
int z_beeps(void){ int b = beeps; beeps = 0; return b; }
void z_options(int protect, int cont){ rom_protect = protect; contention = cont; }

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
