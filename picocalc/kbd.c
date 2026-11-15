/* kbd.c - the PicoCalc keyboard, read from its controller over I2C (protocol
 * from ClockworkPi's reference code, Code/picocalc_helloworld/i2ckbd), shown
 * to the ROM as the Spectrum key matrix.
 *
 * The controller reports characters with shift already applied ('A', '(').
 * Each character is held on the matrix as the Spectrum keys that type it:
 * 'A' as CAPS SHIFT + A, '(' as SYMBOL SHIFT + 8, the arrows as CAPS SHIFT +
 * 5-8, so the ROM's own scan, auto-repeat, KEY() and BREAK work unchanged.
 * Characters that need the Spectrum's E mode ([ ] { } \ | ~) are typed as a
 * timed sequence instead, without auto-repeat. */
#include <ctype.h>
#include <stdio.h>
#include <string.h>
#include "pico/stdlib.h"
#include "hardware/i2c.h"
#include "kbd.h"
#include "picocalc.h"

#define KBD_I2C  i2c1
#define PIN_SDA  6
#define PIN_SCL  7
#define KBD_ADDR 0x1F
#define KBD_BAUD 10000
#define REG_FIFO 0x09
#define REG_LCD_BL 0x05              /* LCD backlight: 16-240 */
#define REG_KBD_BL 0x0A              /* keyboard backlight: 0, 32-224 */
#define LCD_BL_LEVEL 192
#define FIFO_WAIT_US 16000           /* the reference code's write-to-read delay */
#define MIN_HOLD_US  60000           /* every key is held for at least 3 frames */
#define ST_PRESSED 1
#define ST_RELEASED 3

/* Spectrum matrix rows ($FE..$7F), bits 0-4; '^' is CAPS SHIFT, '#' SYMBOL SHIFT */
static const char *const MROWS[8] = { "^zxcv", "asdfg", "qwert", "12345", "09876", "poiuy", "\nlkjh", " #mnb" };
static const char SYMS[] = ":z`x?c/v<r>t!1@2#3$4%5_0)9(8'7&6\"p;o=l+k-j^h.m,n*b";
static const char EMODE[] = "[y]u{f}g\\d|s~a";

typedef struct { char k[2]; } chord;          /* up to two Spectrum keys, 0 = none */
static struct { uint8_t code; chord c; uint64_t t; int rel; } held[4];
static int nheld;
static struct { chord c; uint32_t us; } script[4];
static int nscript, iscript;
static uint64_t script_t;
static uint8_t applied[8], want[8];
static int fifo_state;
static uint64_t fifo_t;

static void press_key(uint8_t *m, char k){
  if (!k) return;
  for (int r = 0; r < 8; r++) {
    const char *p = strchr(MROWS[r], k);
    if (p && k) { m[r] |= 1 << (p - MROWS[r]); return; }
  }
}
static const char *pair_of(const char *tab, int c){
  for (const char *p = tab; *p; p += 2) if (*p == c) return p;
  return 0;
}

/* the chord for controller key code c; 0 if none */
static int map(uint8_t c, chord *o){
  const char *p;
  o->k[0] = o->k[1] = 0;
  switch (c) {
  case 0x0A: case 0x0D: o->k[0] = '\n'; return 1;
  case 0x08: case 0xD4: o->k[0] = '^'; o->k[1] = '0'; return 1;    /* DELETE */
  case 0xB4: o->k[0] = '^'; o->k[1] = '5'; return 1;               /* left */
  case 0xB6: o->k[0] = '^'; o->k[1] = '6'; return 1;               /* down */
  case 0xB5: o->k[0] = '^'; o->k[1] = '7'; return 1;               /* up */
  case 0xB7: o->k[0] = '^'; o->k[1] = '8'; return 1;               /* right */
  case 0xB1: case 0xD0: o->k[0] = '^'; o->k[1] = ' '; return 1;    /* Esc, Break: BREAK */
  }
  if (c == ' ' || isdigit(c) || islower(c)) { o->k[0] = c; return 1; }
  if (isupper(c)) { o->k[0] = '^'; o->k[1] = tolower(c); return 1; }
  if (c >= 32 && c < 127 && (p = pair_of(SYMS, c))) { o->k[0] = '#'; o->k[1] = p[1]; return 1; }
  return 0;
}

static void event(int st, uint8_t code){
  uint64_t now = time_us_64();
  if (st == ST_PRESSED) {
    const char *e = code < 127 ? pair_of(EMODE, code) : 0;
    if (e) {
      if (nscript) return;
      script[0] = (typeof(script[0])){ { { '^', '#' } }, 60000 };
      script[1] = (typeof(script[0])){ { { 0, 0 } }, 60000 };
      script[2] = (typeof(script[0])){ { { e[1], 0 } }, 60000 };
      script[3] = (typeof(script[0])){ { { 0, 0 } }, 40000 };
      nscript = 4; iscript = 0; script_t = now;
      return;
    }
    chord c;
    if (!map(code, &c) || nheld == 4) return;
    for (int i = 0; i < nheld; i++) if (held[i].code == code) return;
    held[nheld].code = code; held[nheld].c = c; held[nheld].t = now; held[nheld].rel = 0; nheld++;
  } else if (st == ST_RELEASED) {
    /* a release may name the character with a different shift state than its
     * press did: if no held key matches, let go of them all */
    int found = 0;
    for (int i = 0; i < nheld; i++) if (held[i].code == code) { held[i].rel = 1; found = 1; }
    if (!found) for (int i = 0; i < nheld; i++) held[i].rel = 1;
  }
}

static void update_matrix(void){
  uint64_t now = time_us_64();
  for (int i = 0; i < nheld; )
    if (held[i].rel && now >= held[i].t + MIN_HOLD_US) held[i] = held[--nheld]; else i++;
  memset(want, 0, sizeof want);
  if (nscript) {
    while (iscript < nscript && now >= script_t + script[iscript].us) script_t += script[iscript++].us;
    if (iscript == nscript) nscript = 0;
    else { press_key(want, script[iscript].c.k[0]); press_key(want, script[iscript].c.k[1]); }
  }
  if (!nscript)
    for (int i = 0; i < nheld; i++) { press_key(want, held[i].c.k[0]); press_key(want, held[i].c.k[1]); }
  for (int r = 0; r < 8; r++)
    for (int b = 0; b < 5; b++)
      if ((want[r] ^ applied[r]) >> b & 1) z_key(r, b, want[r] >> b & 1);
  memcpy(applied, want, sizeof applied);
}

/* a controller register write (bit 7 set), then the 2-byte reply, as the
 * reference code does */
static int reg_write(uint8_t reg, uint8_t v){
  uint8_t m[2] = { reg | 0x80, v }, r[2];
  if (i2c_write_timeout_us(KBD_I2C, KBD_ADDR, m, 2, false, 50000) != 2) return 0;
  sleep_ms(16);
  return i2c_read_timeout_us(KBD_I2C, KBD_ADDR, r, 2, false, 50000) == 2;
}

void kbd_init(void){
  i2c_init(KBD_I2C, KBD_BAUD);
  gpio_set_function(PIN_SDA, GPIO_FUNC_I2C);
  gpio_set_function(PIN_SCL, GPIO_FUNC_I2C);
  gpio_pull_up(PIN_SDA);
  gpio_pull_up(PIN_SCL);
  int ok = reg_write(REG_LCD_BL, LCD_BL_LEVEL);
  printf("opticos: keyboard controller %s\n", ok ? "answered" : "did not answer");
}

/* the keyboard backlight on or off; applied by kbd_poll between FIFO reads */
static int light_want, light_have;
void kbd_light(int on){ light_want = on; }

void kbd_poll(void){
  uint64_t now = time_us_64();
  if (fifo_state == 0 && light_want != light_have) {
    reg_write(REG_KBD_BL, light_want ? 96 : 0);
    light_have = light_want;
  } else if (fifo_state == 0 && now >= fifo_t) {
    uint8_t reg = REG_FIFO;
    if (i2c_write_timeout_us(KBD_I2C, KBD_ADDR, &reg, 1, false, 20000) == 1) fifo_state = 1;
    fifo_t = time_us_64() + FIFO_WAIT_US;
  } else if (fifo_state == 1 && now >= fifo_t) {
    uint8_t b[2];
    fifo_state = 0;
    if (i2c_read_timeout_us(KBD_I2C, KBD_ADDR, b, 2, false, 20000) == 2 && b[0]) {
      event(b[0], b[1]);
      fifo_t = 0;                      /* more may be queued: ask again now */
    } else fifo_t = time_us_64() + 5000;
  }
  update_matrix();
}
