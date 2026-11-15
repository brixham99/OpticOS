/* picocalc.h - the PicoCalc machine's API (emu/picocalc.c), for the firmware.
 * The rig reaches the same functions through ctypes. */
#include <stdint.h>
void z_init(void);                           /* reset; then copy the ROM into z_mem() */
uint8_t *z_mem(void);                        /* the 64K address space */
int z_frame(void);                           /* run one 50 Hz frame */
void z_key(int row, int bit, int down);      /* Spectrum matrix: row 0-7 ($FE..$7F), bit 0-4 */
int z_beeps(void);                           /* beeper edges since the last call */
/* sound: the beeper's edges since the last call (at most max): T-state of
 * each (since reset, mod 2^32) and the level after it */
int pc_edges(uint32_t *t, uint8_t *v, int max);
int pc_level(void);                          /* the beeper's level now */
uint32_t pc_tstates(void);                   /* T-states since reset, mod 2^32 */
/* n samples (0-amp) of the beeper over len T-states from t0, from its edges;
 * *level is the level at t0 and becomes the level at the end */
void pc_render(uint32_t t0, uint32_t len, int n, const uint32_t *et, const uint8_t *ev, int ne,
               int *level, uint8_t *out, int amp);
uint8_t *pc_bits(void);                      /* 320 lines x 40 bytes, bit 7 leftmost */
uint8_t *pc_attrs(void);                     /* 40 rows x 40 cells, Spectrum attributes */
const uint8_t *pc_font(void);                /* the 8x8 font, codes 32-127, 8 bytes each */
