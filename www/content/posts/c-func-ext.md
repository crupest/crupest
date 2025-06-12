---
title: "Libc/POSIX Function \"Extensions\""
date: 2025-03-04T13:40:33+08:00
lastmod: 2025-03-04T13:40:33+08:00
categories: coding
tags:
  - c
  - posix
---

(I've given up on this, at least for linux pam.)

Recently, I’ve been working on porting some libraries to GNU/Hurd. Many (old)
libraries use [`*_MAX` constants on POSIX system
interfaces](https://pubs.opengroup.org/onlinepubs/9699919799.2008edition/nframe.html)
to calculate buffer sizes. However, the GNU/Hurd maintainers urge against the
blind use of them and refuse to define them in system headers. When old APIs are
gone, compatibility problems come. To make my life easier, I'll put some
reusable code snippets here to help *fix `*_MAX` bugs*.

<!--more-->

```c
#include <stdlib.h>
#include <stdarg.h>
#include <unistd.h>
#include <stdio.h>
#include <errno.h>

static inline char *xreadlink(const char *restrict path) {
  char *buffer;
  size_t allocated = 128;
  ssize_t len;

  while (1) {
    buffer = (char*) malloc(allocated);
    if (!buffer) { return NULL; }
    len = readlink(path, buffer, allocated);
    if (len < (ssize_t) allocated) { return buffer; }
    free(buffer);
    if (len >= (ssize_t) allocated) { allocated *= 2; continue; }
    return NULL;
  }
 }


static inline char *xgethostname(void) {
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

static inline char *xgetcwd(void) {
  char *buffer;
  size_t allocated = 128;

  while (1) {
    buffer = (char*) malloc(allocated);
    if (!buffer) { return NULL; }
    getcwd(buffer, allocated);
    if (buffer) return buffer;
    free(buffer);
    if (errno == ERANGE) { allocated *= 2; continue; }
    return NULL;
  }
}

static inline __attribute__((__format__(__printf__, 2, 3))) int
xsprintf(char **buf_ptr, const char *restrict format, ...) {
  char *buffer;
  int ret;

  va_list args;
  va_start(args, format);

  ret = snprintf(NULL, 0,  format, args);
  if (ret < 0) { goto out; }

  buffer = malloc(ret + 1);
  if (!buffer) { ret = -1; goto out; }

  ret = snprintf(NULL, 0,  format, args);
  if (ret < 0) { free(buffer); goto out; }

  *buf_ptr = buffer;

out:
  va_end(args);
  return ret;
}
```
