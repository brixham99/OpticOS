/* lcdtest.c - PicoCalc LCD bring-up, in the order ClockworkPi's helloworld
 * uses (133 MHz, keyboard controller on I2C, LCD).  Then for ever: fill the
 * screen red, green, blue, white, one a second, toggling the keyboard
 * backlight each time, so a blinking keyboard with a black screen means the
 * program runs and the LCD doesn't show it. */
#include "pico/stdlib.h"
#include "hardware/i2c.h"
#include "hardware/clocks.h"
#include "lcd.h"

static uint8_t buf[8 * 320 * 2];

static void reg_write(uint8_t reg, uint8_t v){
  uint8_t m[2] = { reg | 0x80, v }, r[2];
  i2c_write_timeout_us(i2c1, 0x1F, m, 2, false, 50000);
  sleep_ms(16);
  i2c_read_timeout_us(i2c1, 0x1F, r, 2, false, 50000);
}

int main(void){
  set_sys_clock_khz(133000, true);
  stdio_init_all();
  i2c_init(i2c1, 10000);
  gpio_set_function(6, GPIO_FUNC_I2C);
  gpio_set_function(7, GPIO_FUNC_I2C);
  gpio_pull_up(6);
  gpio_pull_up(7);
  reg_write(0x05, 192);                 /* LCD backlight */
  lcd_init();
  static const uint8_t col[4][3] = { {255,0,0}, {0,255,0}, {0,0,255}, {255,255,255} };
  for (int n = 0;; n++) {
    const uint8_t *c = col[n & 3];
    uint16_t p = lcd_rgb(c[0], c[1], c[2]);
    for (int i = 0; i < 8 * 320; i++) { buf[2*i] = p >> 8; buf[2*i+1] = p; }
    for (int y = 0; y < 320; y += 8) lcd_lines(y, 8, buf);
    reg_write(0x0A, (n & 1) ? 96 : 0);  /* keyboard backlight */
    sleep_ms(1000);
  }
}
