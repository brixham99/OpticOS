/* main.c - OpticOS on the PicoCalc.
 *
 * Core 0 runs the PicoCalc machine (emu/picocalc.c: the Z80 with the
 * OpticOS ROM and its display, keyboard and storage devices), one 50 Hz
 * frame every 20 ms, and plays the beeper (audio.c).  Core 1 owns the rest
 * of the hardware: it polls the keyboard into the key matrix and copies
 * changed character rows of the machine's display to the LCD.  The two share only the bitmap, attributes and key matrix, where a
 * torn read costs at most one stale row until the next pass.
 *
 * On the serial console (the PicoCalc's USB-C port: UART0, 115200 baud),
 * core 0 reports how long a frame takes to emulate. */
#include <stdio.h>
#include <string.h>
#include "pico/stdlib.h"
#include "pico/multicore.h"
#include "hardware/clocks.h"
#include "picocalc.h"
#include "lcd.h"
#include "kbd.h"
#include "audio.h"
#include "font8x8.h"

extern const unsigned char opticos_rom[16384];
int z_getpc(void);

/* bring-up diagnostics: a colour-bar test pattern at start, then a status
 * line on the bottom row (frames, Z80 PC, frame time), and the keyboard
 * backlight blinks once a second while the Z80 runs */
#define DIAG 0
static volatile uint32_t frames_run, frame_us;

#define W 320
#define COLS 40
#define ROWS 40
#define FRAME_US 20000

/* ---- core 1: keyboard and screen */
static uint8_t shadow_bits[W * W / 8], shadow_attrs[ROWS * COLS];
static uint8_t line_buf[8 * W * 2];
static uint8_t row_flash[ROWS];
static uint32_t core1_stack[16384 / 4];        /* snprintf needs more than the 2K default */

static uint16_t PAL[16];
static const uint8_t PAL_RGB[16][3] = {
  {0,0,0}, {0,0,215}, {215,0,0}, {215,0,215}, {0,215,0}, {0,215,215}, {215,215,0}, {215,215,215},
  {0,0,0}, {0,0,255}, {255,0,0}, {255,0,255}, {0,255,0}, {0,255,255}, {255,255,0}, {255,255,255},
};

static void draw_row(int r, int flash_on){
  const uint8_t *a = &shadow_attrs[r * COLS];
  uint8_t *o = line_buf;
  int fl = 0;
  for (int y = 0; y < 8; y++) {
    const uint8_t *b = &shadow_bits[(r * 8 + y) * (W / 8)];
    for (int c = 0; c < COLS; c++) {
      uint8_t at = a[c], br = (at & 0x40) >> 3;
      uint16_t ink = PAL[(at & 7) | br], paper = PAL[((at >> 3) & 7) | br];
      if (at & 0x80) { fl = 1; if (flash_on) { uint16_t t = ink; ink = paper; paper = t; } }
      uint8_t px = b[c];
      for (int m = 0x80; m; m >>= 1) {
        uint16_t p = (px & m) ? ink : paper;
        *o++ = p >> 8; *o++ = p;
      }
    }
  }
  row_flash[r] = fl;
  lcd_lines(r * 8, 8, line_buf);
}

static void test_pattern(void){
  for (int r = 0; r < ROWS; r++) {
    uint8_t *o = line_buf;
    for (int i = 0; i < 8 * W; i++) { uint16_t p = PAL[8 + (i % W) / 40]; *o++ = p >> 8; *o++ = p; }
    lcd_lines(r * 8, 8, line_buf);
  }
}

/* text in the display's 8x8 font, white on blue, on character row r */
static void status_line(int r, const char *s){
  uint8_t *o = line_buf;
  for (int y = 0; y < 8; y++)
    for (int c = 0; c < COLS; c++) {
      int ch = *s && c < (int)strlen(s) ? s[c] : ' ';
      if (ch < 32 || ch > 127) ch = '?';
      uint8_t f = font8x8[ch - 32][y];
      for (int m = 0x80; m; m >>= 1) {
        uint16_t p = (f & m) ? PAL[15] : PAL[9];
        *o++ = p >> 8; *o++ = p;
      }
    }
  lcd_lines(r * 8, 8, line_buf);
}

static void core1_main(void){
  for (int i = 0; i < 16; i++) PAL[i] = lcd_rgb(PAL_RGB[i][0], PAL_RGB[i][1], PAL_RGB[i][2]);
  printf("opticos: core 1 up, keyboard and backlight\n");
  kbd_init();
  printf("opticos: LCD init\n");
  lcd_init();
  printf("opticos: LCD init done, test pattern\n");
#if DIAG
  test_pattern();
  sleep_ms(2000);
#endif
  const uint8_t *bits = pc_bits(), *attrs = pc_attrs();
  int flash_was = -1;
  for (;;) {
    int flash_on = (time_us_64() / 320000) & 1;    /* FLASH: 16 frames each way */
    int flash_changed = flash_on != flash_was;
    for (int r = 0; r < ROWS; r++) {
      kbd_poll();
      const uint8_t *lb = &bits[r * 8 * (W / 8)], *la = &attrs[r * COLS];
      uint8_t *sb = &shadow_bits[r * 8 * (W / 8)], *sa = &shadow_attrs[r * COLS];
      if (flash_was < 0 || memcmp(lb, sb, 8 * W / 8) || memcmp(la, sa, COLS)
          || (flash_changed && row_flash[r])) {
        memcpy(sb, lb, 8 * W / 8); memcpy(sa, la, COLS);
        draw_row(r, flash_on);
      }
    }
    flash_was = flash_on;
#if DIAG
    char st[COLS + 1];
    snprintf(st, sizeof st, "%lu PC %04X %lu us", (unsigned long)frames_run,
             z_getpc(), (unsigned long)frame_us);
    status_line(ROWS - 1, st);
    kbd_light((frames_run / 25) & 1);
    memset(&shadow_attrs[(ROWS - 1) * COLS], 0xFF, COLS);    /* redraw the row when DIAG is off */
#endif
  }
}

/* ---- core 0: the machine */
/* the beeper's edges in the frame just run -> its 625 samples (pc_render:
 * the level averaged over each), queued to play */
#define AMP 128                                  /* a high level, of 255 */
static uint32_t edge_t[4096];
static uint8_t edge_v[4096], samples[AUDIO_FRAME];
static void beeper(void){
  static uint32_t prev;                          /* T-states at the end of the last frame */
  static int level;
  uint32_t now = pc_tstates();
  int n = pc_edges(edge_t, edge_v, 4096);
  pc_render(prev, now - prev, AUDIO_FRAME, edge_t, edge_v, n, &level, samples, AMP);
  prev = now;
  audio_push(samples, AUDIO_FRAME);
}

int main(void){
  /* Interrupts on: we can be started (by a boot loader before us) with them
   * masked (PRIMASK = 1), which the SDK's start-up code doesn't undo, and
   * then no interrupt is ever taken: no sound, no USB. */
  __asm volatile ("cpsie i" ::: "memory");
  set_sys_clock_khz(133000, true);             /* as lcdtest and ClockworkPi's reference */
  stdio_init_all();
  printf("opticos: core 0 up\n");
  z_init();
  memcpy(z_mem(), opticos_rom, sizeof opticos_rom);
  audio_init();                                /* before the first frame: the chime */
  multicore_launch_core1_with_stack(core1_main, core1_stack, sizeof core1_stack);

  uint64_t next = time_us_64(), busy = 0, worst = 0;
  int frames = 0, late = 0;
  for (;;) {
    uint64_t t0 = time_us_64();
    z_frame();
    beeper();                                    /* this frame's sound, 20 ms behind */
    uint64_t t = time_us_64() - t0;
    busy += t; if (t > worst) worst = t;
    frames_run++; frame_us = t;
    next += FRAME_US;
    uint64_t now = time_us_64();
    if (now < next) sleep_until(from_us_since_boot(next));
    else if (now > next + 5 * FRAME_US) { next = now; late++; }   /* fell behind: resync */
    if (++frames == 250) {
      printf("opticos: frame %llu us avg, %llu us worst (budget %d), %d resyncs\n",
             busy / frames, worst, FRAME_US, late);
      frames = 0; busy = worst = 0; late = 0;
    }
  }
}
