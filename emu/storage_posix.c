/* storage_posix.c - the storage device's files in a host directory, for the
 * rig: z_storage_dir(path) chooses it (default build/picocalc/sd). */
#include <dirent.h>
#include <stdio.h>
#include <string.h>
#include "storage.h"

static char dir[512] = "build/picocalc/sd";
void z_storage_dir(const char *path){ snprintf(dir, sizeof dir, "%s", path); }

struct st_file { FILE *f; };
static struct st_file files[2];

st_file *st_open(const char *name, int write){
  char p[600];
  snprintf(p, sizeof p, "%s/%s", dir, name);
  for (int i = 0; i < 2; i++)
    if (!files[i].f) {
      files[i].f = fopen(p, write ? "wb" : "rb");
      return files[i].f ? &files[i] : NULL;
    }
  return NULL;
}
int st_read(st_file *f, void *buf, int n){ return (int)fread(buf, 1, n, f->f); }
int st_write(st_file *f, const void *buf, int n){ return (int)fwrite(buf, 1, n, f->f); }
void st_rewind(st_file *f){ rewind(f->f); }
void st_close(st_file *f){ fclose(f->f); f->f = NULL; }

int st_list(char names[][ST_NAME], int max){
  DIR *d = opendir(dir);
  if (!d) return -1;
  int n = 0;
  for (struct dirent *e; n < max && (e = readdir(d)); )
    if (e->d_name[0] != '.' && strlen(e->d_name) < ST_NAME) strcpy(names[n++], e->d_name);
  closedir(d);
  return n;
}
