/* picocalc.h - the PicoCalc machine's API (emu/picocalc.c), for the firmware.
 * The rig reaches the same functions through ctypes. */
#include <stdint.h>
void z_init(void);                           /* reset; then copy the ROM into z_mem() */
uint8_t *z_mem(void);                        /* the 64K address space */
int z_frame(void);                           /* run one 50 Hz frame */
void z_key(int row, int bit, int down);      /* Spectrum matrix: row 0-7 ($FE..$7F), bit 0-4 */
int z_beeps(void);                           /* beeper edges since the last call */
uint8_t *pc_bits(void);                      /* 320 lines x 40 bytes, bit 7 leftmost */
uint8_t *pc_attrs(void);                     /* 40 rows x 80 cells, Spectrum attributes */
