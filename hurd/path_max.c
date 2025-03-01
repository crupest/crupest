#include <errno.h>
#include <stdlib.h>
#include <unistd.h>

static inline char *xreadlink(const char *restrict path) {
  char *buffer;
  size_t allocated = 128;
  ssize_t len;

  while (1) {
    buffer = (char *)malloc(allocated);
    if (!buffer) {
      return NULL;
    }
    len = readlink(path, buffer, allocated);
    if (len < (ssize_t)allocated) {
      return buffer;
    }
    free(buffer);
    if (len >= (ssize_t)allocated) {
      allocated *= 2;
      continue;
    }
    return NULL;
  }
}

static inline char *xgethostname() {
  long max_host_name;
  char *buffer;

  max_host_name = sysconf(_SC_HOST_NAME_MAX);
  buffer = malloc(max_host_name + 1);

  if (gethostname(buffer, max_host_name + 1)) {
    free(buffer);
    return NULL;
  }

  buffer[max_host_name] = '\0';
  return buffer;
}

static inline char *xgetcwd() {
  char *buffer;
  size_t allocated = 128;

  while (1) {
    buffer = (char *)malloc(allocated);
    if (!buffer) {
      return NULL;
    }
    getcwd(buffer, allocated);
    if (buffer)
      return buffer;
    free(buffer);
    if (errno == ERANGE) {
      allocated *= 2;
      continue;
    }
    return NULL;
  }
}
