/* audio.c - samples on the PicoCalc's speakers.
 *
 * audio_push() queues samples (0-255) at 31.25 kHz; main.c makes them from
 * the Spectrum beeper each frame.  A hardware timer alarm, re-armed every
 * 32 us from its last target (so the rate never drifts), interrupts 31,250
 * times a second and sets the next sample as the duty of a 520 kHz PWM
 * carrier on the audio pins.  Playing starts with 2 frames
 * (40 ms) in hand and stops (holding the last level) if the samples run
 * out.  The queue and the interrupt are both on core 0, beside the
 * emulator, so they share no state across cores.
 *
 * ClockworkPi's two examples disagree on the left channel (GPIO 26 in
 * picocalc_helloworld, 28 in pico_multi_booter); the right is GPIO 27.
 * All three are driven. */
#include "pico/stdlib.h"
#include "hardware/pwm.h"
#include "hardware/timer.h"
#include "audio.h"

#define RING 4096                     /* samples, a power of two */
#define START (2 * AUDIO_FRAME)
#define TICK_US (1000000 / AUDIO_RATE)   /* 32 */
static const uint PINS[] = { 26, 27, 28 };

static uint8_t ring[RING];
static volatile uint32_t head, tail;  /* written by audio_push / the interrupt */
static int playing, alarm;
static absolute_time_t next;
volatile uint32_t audio_irqs;          /* interrupts taken (for soundtest) */
uint32_t audio_queued(void){ return head - tail; }

static void sample_irq(uint num){
  next = delayed_by_us(next, TICK_US);
  if (hardware_alarm_set_target(num, next)) {      /* already past (a late tick): from now */
    next = delayed_by_us(get_absolute_time(), TICK_US);
    hardware_alarm_set_target(num, next);
  }
  audio_irqs++;
  if (!playing) {
    if (head - tail < START) return;
    playing = 1;
  }
  if (head == tail) { playing = 0; return; }
  uint8_t v = ring[tail & (RING - 1)];
  tail++;
  for (int i = 0; i < 3; i++) pwm_set_gpio_level(PINS[i], v);
}

void audio_init(void){
  pwm_config c = pwm_get_default_config();
  pwm_config_set_wrap(&c, 255);       /* the carrier: clk_sys / 256 */
  for (int i = 0; i < 3; i++) {
    gpio_set_function(PINS[i], GPIO_FUNC_PWM);
    pwm_init(pwm_gpio_to_slice_num(PINS[i]), &c, true);
    pwm_set_gpio_level(PINS[i], 0);
  }
  if (alarm) return;                  /* (the tick is already running) */
  alarm = hardware_alarm_claim_unused(true) + 1;
  hardware_alarm_set_callback(alarm - 1, sample_irq);
  next = delayed_by_us(get_absolute_time(), TICK_US);
  hardware_alarm_set_target(alarm - 1, next);
}

/* queue n samples (0-255) to play; dropped if there is no room */
void audio_push(const uint8_t *buf, int n){
  if (RING - (head - tail) < (uint32_t)n) return;
  uint32_t h = head;
  for (int i = 0; i < n; i++) ring[(h + i) & (RING - 1)] = buf[i];
  head = h + n;                       /* (the interrupt runs on this core) */
}
