/* audio.h - samples on the PicoCalc's PWM audio pins (core 0) */
#include <stdint.h>
#define AUDIO_RATE 31250                  /* samples a second */
#define AUDIO_FRAME 625                   /* samples a 20 ms frame */
void audio_init(void);
void audio_push(const uint8_t *buf, int n);   /* queue n samples (0-255) */
