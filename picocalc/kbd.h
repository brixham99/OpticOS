/* kbd.h - the PicoCalc keyboard (I2C) shown to the ROM as the Spectrum matrix */
void kbd_init(void);
/* call often from core 1; never blocks for long */
void kbd_poll(void);
/* the keyboard backlight, used as the firmware's status light */
void kbd_light(int on);
