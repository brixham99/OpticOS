/* storage.h - the files behind the PicoCalc's storage device (emu/picocalc.c).
 * The rig keeps them in a host directory (storage_posix.c); the firmware
 * keeps them in /OpticOS on the SD card (picocalc/storage_sd.c).  Names are
 * plain file names, no directory. */
#ifndef STORAGE_H
#define STORAGE_H
typedef struct st_file st_file;
st_file *st_open(const char *name, int write);  /* write: create or truncate; NULL on failure */
int st_read(st_file *f, void *buf, int n);       /* bytes read (short at the end) */
int st_write(st_file *f, const void *buf, int n);/* bytes written */
void st_rewind(st_file *f);
void st_close(st_file *f);
/* the names of the files in the directory, at most max of them, each at most
 * ST_NAME-1 characters (longer names are left out); -1 if there is no card */
#define ST_NAME 32
int st_list(char names[][ST_NAME], int max);
#endif
