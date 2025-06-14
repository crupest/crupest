---
title: "Hurd Useful Links"
date: 2025-06-14T20:34:06+08:00
lastmod: 2025-06-14T20:34:06+08:00
---

## links

| name | link |
| --- | --- |
| kernel-list-archive | <https://lists.gnu.org/archive/html/bug-hurd/> |
| debian-list-archive | <https://lists.debian.org/debian-hurd/> |
| irc-archive | <https://logs.guix.gnu.org/hurd/> |
| kernel-home | <https://www.gnu.org/software/hurd/index.html> |
| debian-home | <https://www.debian.org/ports/hurd/> |

refs:

| name | link |
| --- | --- |
| c | <https://en.cppreference.com/w/c> |
| posix latest | <https://pubs.opengroup.org/onlinepubs/9799919799/> |
| posix 2013 | <https://pubs.opengroup.org/onlinepubs/9699919799.2013edition/> |
| posix 2008 | <https://pubs.opengroup.org/onlinepubs/9699919799.2008edition/> |
| glibc | <https://sourceware.org/glibc/manual/2.41/html_mono/libc.html> |

## mailing lists / irc

| name | address |
| --- | --- |
| hurd | <bug-hurd@gnu.org> |
| debian | <debian-hurd@lists.debian.org> |
| irc | librechat #hurd |

## *_MAX patch

See [this](posts/c-func-ext.md)

## git repos

Clone all at once:

```sh
# glibc is too big, so not clone here.
for repo in hurd gnumach mig web; do
  if [ ! -d $repo ]; then
    git clone "https://crupest.life/git/hurd/$repo.git"
    pushd $repo
    git remote add upstream "https://git.savannah.gnu.org/git/hurd/$repo.git"
    popd
  fi
done
```

{{< link-group >}}
hurd
cru: <https://crupest.life/git/hurd/hurd.git>
upstream: <https://git.savannah.gnu.org/git/hurd/hurd.git>
debian: <https://salsa.debian.org/hurd-team/hurd>
{{< /link-group >}}

{{< link-group >}}
gnumach
cru: <https://crupest.life/git/hurd/gnumach.git>
upstream: <https://git.savannah.gnu.org/git/hurd/gnumach.git>
debian: <https://salsa.debian.org/hurd-team/gnumach>
{{< /link-group >}}

{{< link-group >}}
mig
cru: <https://crupest.life/git/hurd/mig.git>
upstream: <https://git.savannah.gnu.org/git/hurd/mig.git>
debian: <https://salsa.debian.org/hurd-team/mig>
{{< /link-group >}}

{{< link-group >}}
glibc
cru: <https://crupest.life/git/hurd/glibc.git>
upstream: <git://sourceware.org/git/glibc.git>
debian: <https://salsa.debian.org/glibc-team/glibc>
mirror: <https://mirrors.tuna.tsinghua.edu.cn/git/glibc.git>
{{< /link-group >}}

{{< link-group >}}
web
cru: <https://crupest.life/git/hurd/web.git>
upstream: <https://git.savannah.gnu.org/git/hurd/web.git>
{{< /link-group >}}
