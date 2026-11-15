/* hw_config.c - the PicoCalc's SD card for carlk3's no-OS-FatFS library:
 * SPI0 on GPIO 18 (SCK), 19 (MOSI), 16 (MISO), chip select GPIO 17, as in
 * ClockworkPi's reference code (Code/pico_multi_booter/sd_boot/config.h).
 * Card detect (GPIO 22) is not used: a missing card shows as a failed mount. */
#include "hw_config.h"

static spi_t spi = {
  .hw_inst = spi0,
  .sck_gpio = 18,
  .mosi_gpio = 19,
  .miso_gpio = 16,
  .baud_rate = 12 * 1000 * 1000,
};
static sd_spi_if_t spi_if = {
  .spi = &spi,
  .ss_gpio = 17,
};
static sd_card_t sd_card = {
  .type = SD_IF_SPI,
  .spi_if_p = &spi_if,
};

size_t sd_get_num(void){ return 1; }
sd_card_t *sd_get_by_num(size_t num){ return num == 0 ? &sd_card : NULL; }
