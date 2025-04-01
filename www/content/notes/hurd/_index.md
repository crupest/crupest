---
title: "Hurd"
date: 2025-03-03T15:34:41+08:00
lastmod: 2025-03-03T23:28:46+08:00
layout: single
---

{{< mono >}}

[TODOS](/notes/hurd/todos)

{{< /mono >}}

## links

{{< mono >}}

| name | link |
| --- | --- |
| kernel-list-archive | <https://lists.gnu.org/archive/html/bug-hurd/> |
| debian-list-archive | <https://lists.debian.org/debian-hurd/> |
| irc-archive | <https://logs.guix.gnu.org/hurd/> |
| kernel-home | <https://www.gnu.org/software/hurd/index.html> |
| debian-home | <https://www.debian.org/ports/hurd/> |

{{< /mono >}}

refs:

{{< mono >}}

| name | link |
| --- | --- |
| c | <https://en.cppreference.com/w/c> |
| posix latest | <https://pubs.opengroup.org/onlinepubs/9799919799/> |
| posix 2013 | <https://pubs.opengroup.org/onlinepubs/9699919799.2013edition/> |
| posix 2008 | <https://pubs.opengroup.org/onlinepubs/9699919799.2008edition/> |
| glibc | <https://sourceware.org/glibc/manual/2.41/html_mono/libc.html> |

{{< /mono >}}

## *_MAX patch

TODO: Move to separate page.

```c
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
```

## git repos

{{< link-group >}}
hurd
cru: <https://crupest.life/git/cru-hurd/hurd.git>
upstream: <https://git.savannah.gnu.org/git/hurd/hurd.git>
debian: <https://salsa.debian.org/hurd-team/hurd>
{{< /link-group >}}

{{< link-group >}}
gnumach
cru: <https://crupest.life/git/cru-hurd/gnumach.git>
upstream: <https://git.savannah.gnu.org/git/hurd/gnumach.git>
debian: <https://salsa.debian.org/hurd-team/gnumach>
{{< /link-group >}}

{{< link-group >}}
mig
cru: <https://crupest.life/git/cru-hurd/mig.git>
upstream: <https://git.savannah.gnu.org/git/hurd/mig.git>
debian: <https://salsa.debian.org/hurd-team/mig>
{{< /link-group >}}

{{< link-group >}}
glibc
cru: <https://crupest.life/git/cru-hurd/glibc.git>
upstream: <git://sourceware.org/git/glibc.git>
debian: <https://salsa.debian.org/glibc-team/glibc>
mirror: <https://mirrors.tuna.tsinghua.edu.cn/git/glibc.git>
{{< /link-group >}}

{{< link-group >}}
web
cru: <https://crupest.life/git/cru-hurd/web.git>
upstream: <https://git.savannah.gnu.org/git/hurd/web.git>
{{< /link-group >}}

## cheatsheet

Start qemu

```sh
qemu-system-x86_64 -enable-kvm -m 4G -net nic -net user,hostfwd=tcp::3222-:22 -vga vmware -drive cache=writeback,file=[...]
```

Configure/Setup network

```sh
settrans -fgap /servers/socket/2 /hurd/pfinet -i /dev/eth0 -a 10.0.2.15 -g 10.0.2.2 -m 255.255.255.0
fsysopts /servers/socket/2 /hurd/pfinet -i /dev/eth0 -a 10.0.2.15 -g 10.0.2.2 -m 255.255.255.0
fsysopts /server/socket/2 -a 10.0.2.15 -g 10.0.2.2 -m 255.255.255.0
```

Setup apt

```sh
apt-get --allow-unauthenticated --allow-insecure-repositories update
apt-get --allow-unauthenticated upgrade
```

## mailing lists / irc

{{< mono >}}

| name | address |
| --- | --- |
| hurd | <bug-hurd@gnu.org> |
| debian | <debian-hurd@lists.debian.org> |
| irc | librechat #hurd |

{{< /mono >}}
