/* soundtest.c - PicoCalc speaker bring-up.  Repeats, 6 seconds a round:
 *   A  1 s: 440 Hz made by the PWM hardware alone on GPIO 26 and 27
 *   B  1 s: silence
 *   C  1 s: 550 Hz: audio.c's 520 kHz carrier, its duty switched by hand
 *   D  1 s: silence
 *   E  1 s: 660 Hz through audio.c's sample interrupt
 *   F  1 s: silence
 * The serial console (USB-C, 115200) reports each phase, with the count of
 * sample interrupts and the samples queued. */
#include <stdio.h>
#include "pico/stdlib.h"
#include "hardware/clocks.h"
#include "hardware/pwm.h"
#include "hardware/structs/timer.h"
#include "hardware/structs/scb.h"
#include "hardware/structs/nvic.h"
#include "audio.h"

extern volatile uint32_t audio_irqs;
uint32_t audio_queued(void);
static void report(const char *what){
  uint32_t primask;
  __asm volatile ("mrs %0, primask" : "=r" (primask));
  printf("soundtest: %s  irqs %lu  queued %lu  clk_sys %lu\n", what, (unsigned long)audio_irqs,
         (unsigned long)audio_queued(), (unsigned long)clock_get_hz(clk_sys));
  printf("  primask %lu  vtor %08lx  iser0 %08lx  timer armed %lx inte %lx intr %lx  pwm inte %lx intr %lx\n",
         (unsigned long)primask, (unsigned long)scb_hw->vtor, (unsigned long)nvic_hw->iser[0],
         (unsigned long)timer0_hw->armed, (unsigned long)timer0_hw->inte, (unsigned long)timer0_hw->intr,
         (unsigned long)pwm_hw->inte, (unsigned long)pwm_hw->intr);
}
static void tone(int hz){              /* GPIO 26/27 (slice 5): a square wave at hz, or off */
  uint slice = pwm_gpio_to_slice_num(26);
  gpio_set_function(26, GPIO_FUNC_PWM);
  gpio_set_function(27, GPIO_FUNC_PWM);
  if (!hz) { pwm_set_enabled(slice, false); return; }
  pwm_config c = pwm_get_default_config();
  pwm_config_set_clkdiv(&c, 64.0f);
  uint32_t top = clock_get_hz(clk_sys) / 64 / hz - 1;
  pwm_config_set_wrap(&c, top);
  pwm_init(slice, &c, true);
  pwm_set_both_levels(slice, top / 2, top / 2);
}

int main(void){
  /* Interrupts on: we can be started (by a boot loader before us) with them
   * masked (PRIMASK = 1), which the SDK's start-up code doesn't undo, and
   * then no interrupt is ever taken: no sound, no USB. */
  __asm volatile ("cpsie i" ::: "memory");
  set_sys_clock_khz(133000, true);
  stdio_init_all();
  static uint8_t buf[AUDIO_FRAME];
  sleep_ms(500);
  report("start");
  for (;;) {
    report("A 440 Hz, PWM hardware");
    tone(440); sleep_ms(1000);
    tone(0); sleep_ms(1000);
    audio_init();                       /* (the pins back on the 520 kHz carrier) */
    report("C 550 Hz, carrier by hand");
    absolute_time_t end = make_timeout_time_ms(1000);
    for (int v = 0; absolute_time_diff_us(get_absolute_time(), end) > 0; v ^= 128) {
      pwm_set_gpio_level(26, v); pwm_set_gpio_level(27, v); pwm_set_gpio_level(28, v);
      sleep_us(909);                    /* half of 550 Hz */
    }
    pwm_set_gpio_level(26, 0); pwm_set_gpio_level(27, 0); pwm_set_gpio_level(28, 0);
    sleep_ms(1000);
    report("E 660 Hz, sample interrupt");
    for (int f = 0; f < 50; f++) {      /* 1 s of 660 Hz: 1320 half-periods a second */
      for (int i = 0; i < AUDIO_FRAME; i++) buf[i] = ((f * AUDIO_FRAME + i) * 1320 / AUDIO_RATE) & 1 ? 128 : 0;
      audio_push(buf, AUDIO_FRAME);
      sleep_ms(20);
    }
    report("E done");
    sleep_ms(1040);
  }
}
