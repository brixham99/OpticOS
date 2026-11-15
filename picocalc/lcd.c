/* lcd.c - the PicoCalc's ST7796SP panel.  Pins follow ClockworkPi's
 * reference code (PicoCalc repo, Code/picocalc_helloworld/lcdspi); the init
 * sequence and pixel format follow PicoMite's ST7796SP driver (SPI-LCD.c),
 * which works on the PicoCalc where the reference's ILI9488 init does not. */
#include "pico/stdlib.h"
#include "hardware/spi.h"
#include "lcd.h"

#define LCD_SPI spi1
#define PIN_SCK 10
#define PIN_TX  11
#define PIN_RX  12
#define PIN_CS  13
#define PIN_DC  14
#define PIN_RST 15
#define LCD_INIT_BAUD 10000000      /* commands: well inside the ST7796's write timing */
#define LCD_BAUD 20000000           /* pixels: 18.75 MHz from 150 MHz (lcdtest's 22 MHz works) */

/* CS and DC changes with set-up and hold time either side: running from RAM
 * at 150 MHz, CS can otherwise rise a few ns after the last clock edge, and
 * the panel drops that byte */
static inline void pin(uint p, int v){ busy_wait_us_32(1); gpio_put(p, v); busy_wait_us_32(1); }

/* as the reference code: CS framed around the command byte and around each
 * data byte */
static void cmd(uint8_t c, const uint8_t *d, int n){
  pin(PIN_DC, 0); pin(PIN_CS, 0);
  spi_write_blocking(LCD_SPI, &c, 1);
  pin(PIN_CS, 1);
  pin(PIN_DC, 1);
  for (int i = 0; i < n; i++) {
    pin(PIN_CS, 0); spi_write_blocking(LCD_SPI, &d[i], 1); pin(PIN_CS, 1);
  }
}
#define CMD(c, ...) do { static const uint8_t d_[] = { __VA_ARGS__ }; cmd(c, d_, sizeof d_); } while (0)

void lcd_init(void){
  static const uint8_t pins[] = { PIN_SCK, PIN_TX, PIN_RX, PIN_CS, PIN_DC, PIN_RST };
  for (int i = 0; i < 6; i++) { gpio_init(pins[i]); if (pins[i] != PIN_RX) gpio_set_dir(pins[i], GPIO_OUT); }
  spi_init(LCD_SPI, LCD_INIT_BAUD);
  gpio_set_function(PIN_SCK, GPIO_FUNC_SPI);
  gpio_set_function(PIN_TX, GPIO_FUNC_SPI);
  gpio_set_function(PIN_RX, GPIO_FUNC_SPI);
  gpio_set_input_hysteresis_enabled(PIN_RX, true);
  gpio_put(PIN_CS, 1);
  gpio_put(PIN_RST, 1);
  gpio_put(PIN_RST, 1); sleep_ms(10);
  gpio_put(PIN_RST, 0); sleep_ms(10);
  gpio_put(PIN_RST, 1); sleep_ms(200);
  /* ST7796SP, as PicoMite initialises it for the PicoCalc */
  CMD(0xC5, 0x1C);            /* VCOM */
  CMD(0x3A, 0x55);            /* 16-bit pixels (RGB565) */
  cmd(0xB0, 0, 0); sleep_ms(150);  /* interface mode: command only, no parameter, as PicoMite */
  CMD(0xB4, 0x01);            /* inversion control */
  cmd(0x21, 0, 0);            /* inversion on */
  CMD(0xB6, 0x80,0x02,0x3B);
  CMD(0xB7, 0xC6);
  CMD(0xF0, 0xC3);            /* command set unlock */
  CMD(0xF0, 0x96);
  CMD(0x36, 0x48);            /* MADCTL: MX, BGR (portrait) */
  CMD(0x33, 0x00,0x00,0x01,0x40,0x00,0xA0);   /* scroll area for 320 lines */
  cmd(0x11, 0, 0); sleep_ms(150);
  CMD(0x3A, 0x55);            /* pixel format and orientation again: a lost byte */
  CMD(0x36, 0x48);            /* here leaves the panel in 18-bit mode */
  cmd(0x29, 0, 0); sleep_ms(150);
  spi_set_baudrate(LCD_SPI, LCD_BAUD);
}

/* the window and the pixels in one CS frame, as PicoMite's DefineRegionSPI */
void lcd_lines(int y, int h, const uint8_t *buf){
  uint8_t ca[4] = { 0, 0, 319 >> 8, 319 & 255 };
  uint8_t pa[4] = { y >> 8, y & 255, (y + h - 1) >> 8, (y + h - 1) & 255 };
  uint8_t c;
  pin(PIN_CS, 0);
  pin(PIN_DC, 0); c = 0x2A; spi_write_blocking(LCD_SPI, &c, 1);
  pin(PIN_DC, 1); spi_write_blocking(LCD_SPI, ca, 4);
  pin(PIN_DC, 0); c = 0x2B; spi_write_blocking(LCD_SPI, &c, 1);
  pin(PIN_DC, 1); spi_write_blocking(LCD_SPI, pa, 4);
  pin(PIN_DC, 0); c = 0x2C; spi_write_blocking(LCD_SPI, &c, 1);
  pin(PIN_DC, 1); spi_write_blocking(LCD_SPI, buf, h * 320 * 2);
  pin(PIN_CS, 1);
}
