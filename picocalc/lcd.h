/* lcd.h - the PicoCalc's 320x320 ST7796SP panel on SPI1, 16-bit colour */
#include <stdint.h>
void lcd_init(void);
/* pixel lines y..y+h-1, full width, from buf: 2 bytes per pixel, RGB565 high byte first */
void lcd_lines(int y, int h, const uint8_t *buf);
static inline uint16_t lcd_rgb(int r, int g, int b){ return (r & 0xF8) << 8 | (g & 0xFC) << 3 | b >> 3; }
