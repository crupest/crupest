---
title: "Hurd Useful Links"
date: 2025-06-14T20:34:06+08:00
lastmod: 2025-06-14T20:34:06+08:00
---

## links

| name                | link                                           |
| ------------------- | ---------------------------------------------- |
| kernel-list-archive | <https://lists.gnu.org/archive/html/bug-hurd/> |
| debian-list-archive | <https://lists.debian.org/debian-hurd/>        |
| irc-archive         | <https://logs.guix.gnu.org/hurd/>              |
| kernel-home         | <https://www.gnu.org/software/hurd/index.html> |
| debian-home         | <https://www.debian.org/ports/hurd/>           |

refs:

| name         | link                                                            |
| ------------ | --------------------------------------------------------------- |
| c            | <https://en.cppreference.com/w/c>                               |
| posix latest | <https://pubs.opengroup.org/onlinepubs/9799919799/>             |
| posix 2013   | <https://pubs.opengroup.org/onlinepubs/9699919799.2013edition/> |
| posix 2008   | <https://pubs.opengroup.org/onlinepubs/9699919799.2008edition/> |
| glibc        | <https://sourceware.org/glibc/manual/2.41/html_mono/libc.html>  |

## mailing lists / irc

| name   | address                        |
| ------ | ------------------------------ |
| hurd   | <bug-hurd@gnu.org>             |
| debian | <debian-hurd@lists.debian.org> |
| irc    | librechat #hurd                |

## *_MAX patch

See [this](posts/c-func-ext.md)

## git repos

Clone all at once:

```sh
# glibc is too big, so not clone here.
for repo in hurd gnumach mig web; do
  if [ ! -d $repo ]; then
    git clone "https://git.savannah.gnu.org/git/hurd/$repo.git"
  fi
done
```

### hurd

| name     | link                                             |
| -------- | ------------------------------------------------ |
| upstream | <https://git.savannah.gnu.org/git/hurd/hurd.git> |
| debian   | <https://salsa.debian.org/hurd-team/hurd>        |

### gnumach

| name     | link                                                |
| -------- | --------------------------------------------------- |
| upstream | <https://git.savannah.gnu.org/git/hurd/gnumach.git> |
| debian   | <https://salsa.debian.org/hurd-team/gnumach>        |

### mig

| name     | link                                            |
| -------- | ----------------------------------------------- |
| upstream | <https://git.savannah.gnu.org/git/hurd/mig.git> |
| debian   | <https://salsa.debian.org/hurd-team/mig>        |

### glibc

| name     | link                                                 |
| -------- | ---------------------------------------------------- |
| upstream | <git://sourceware.org/git/glibc.git>                 |
| debian   | <https://salsa.debian.org/glibc-team/glibc>          |
| mirror   | <https://mirrors.tuna.tsinghua.edu.cn/git/glibc.git> |

### web

| name     | link                                            |
| -------- | ----------------------------------------------- |
| upstream | <https://git.savannah.gnu.org/git/hurd/web.git> |
