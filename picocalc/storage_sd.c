/* storage_sd.c - the storage device's files (emu/storage.h) in /OpticOS on
 * the PicoCalc's SD card, through FatFs (carlk3's no-OS-FatFS library,
 * configured in hw_config.c).  The card is mounted on first use, and again
 * after a failure, so a card put in later (or swapped) is found. */
#include <stdio.h>
#include <string.h>
#include "ff.h"
#include "storage.h"

#define DIR_PATH "/OpticOS"
static FATFS fs;
static int mounted;
struct st_file { FIL f; int used; };
static struct st_file files[2];

static int mount(void){
  if (mounted) return 1;
  if (f_mount(&fs, "", 1) != FR_OK) return 0;
  FRESULT fr = f_mkdir(DIR_PATH);
  if (fr != FR_OK && fr != FR_EXIST) { f_unmount(""); return 0; }
  return mounted = 1;
}
/* after an error that means the card went away: mount afresh next time */
static void check(FRESULT fr){
  if (fr == FR_NOT_READY || fr == FR_DISK_ERR || fr == FR_INVALID_OBJECT || fr == FR_NOT_ENABLED) {
    f_unmount(""); mounted = 0;
  }
}

st_file *st_open(const char *name, int write){
  char p[64];
  snprintf(p, sizeof p, DIR_PATH "/%s", name);
  for (int tries = 0; tries < 2; tries++) {
    if (!mount()) return NULL;
    for (int i = 0; i < 2; i++)
      if (!files[i].used) {
        FRESULT fr = f_open(&files[i].f, p, write ? FA_WRITE | FA_CREATE_ALWAYS : FA_READ);
        if (fr == FR_OK) { files[i].used = 1; return &files[i]; }
        check(fr);
        if (mounted) return NULL;             /* not a card problem: no such file */
        break;
      }
  }
  return NULL;
}
int st_read(st_file *f, void *buf, int n){
  UINT br = 0;
  FRESULT fr = f_read(&f->f, buf, n, &br);
  check(fr);
  return fr == FR_OK ? (int)br : 0;
}
int st_write(st_file *f, const void *buf, int n){
  UINT bw = 0;
  FRESULT fr = f_write(&f->f, buf, n, &bw);
  check(fr);
  return fr == FR_OK ? (int)bw : 0;
}
void st_rewind(st_file *f){ check(f_lseek(&f->f, 0)); }
void st_close(st_file *f){ check(f_close(&f->f)); f->used = 0; }

int st_list(char names[][ST_NAME], int max){
  for (int tries = 0; tries < 2; tries++) {
    if (!mount()) return -1;
    DIR d; FILINFO fi;
    FRESULT fr = f_opendir(&d, DIR_PATH);
    if (fr != FR_OK) { check(fr); continue; }
    int n = 0;
    while (n < max && f_readdir(&d, &fi) == FR_OK && fi.fname[0])
      if (!(fi.fattrib & (AM_DIR | AM_HID | AM_SYS)) && strlen(fi.fname) < ST_NAME) strcpy(names[n++], fi.fname);
    f_closedir(&d);
    return n;
  }
  return -1;
}
