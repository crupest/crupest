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
    git clone "https://crupest.life/git/hurd/$repo.git"
    pushd $repo
    git remote add upstream "https://git.savannah.gnu.org/git/hurd/$repo.git"
    popd
  fi
done
```

<div class="mono link-group">
  <div class="link-group-title">hurd</div>
  <div class="link-group-list">
    <div class="link-group-item">cru: <a href="https://crupest.life/git/hurd/hurd.git">https://crupest.life/git/hurd/hurd.git</a></div>
    <div class="link-group-item">upstream: <a href="https://git.savannah.gnu.org/git/hurd/hurd.git">https://git.savannah.gnu.org/git/hurd/hurd.git</a></div>
    <div class="link-group-item">debian: <a href="https://salsa.debian.org/hurd-team/hurd">https://salsa.debian.org/hurd-team/hurd</a></div>
  </div>
</div>

<div class="mono link-group">
  <div class="link-group-title">gnumach</div>
  <div class="link-group-list">
    <div class="link-group-item">cru: <a href="https://crupest.life/git/hurd/gnumach.git">https://crupest.life/git/hurd/gnumach.git</a></div>
    <div class="link-group-item">upstream: <a href="https://git.savannah.gnu.org/git/hurd/gnumach.git">https://git.savannah.gnu.org/git/hurd/gnumach.git</a></div>
    <div class="link-group-item">debian: <a href="https://salsa.debian.org/hurd-team/gnumach">https://salsa.debian.org/hurd-team/gnumach</a></div>
  </div>
</div>

<div class="mono link-group">
  <div class="link-group-title">mig</div>
  <div class="link-group-list">
    <div class="link-group-item">cru: <a href="https://crupest.life/git/hurd/mig.git">https://crupest.life/git/hurd/mig.git</a></div>
    <div class="link-group-item">upstream: <a href="https://git.savannah.gnu.org/git/hurd/mig.git">https://git.savannah.gnu.org/git/hurd/mig.git</a></div>
    <div class="link-group-item">debian: <a href="https://salsa.debian.org/hurd-team/mig">https://salsa.debian.org/hurd-team/mig</a></div>
  </div>
</div>

<div class="mono link-group">
  <div class="link-group-title">glibc</div>
  <div class="link-group-list">
    <div class="link-group-item">cru: <a href="https://crupest.life/git/hurd/glibc.git">https://crupest.life/git/hurd/glibc.git</a></div>
    <div class="link-group-item">upstream: <a href="git://sourceware.org/git/glibc.git">git://sourceware.org/git/glibc.git</a></div>
    <div class="link-group-item">debian: <a href="https://salsa.debian.org/glibc-team/glibc">https://salsa.debian.org/glibc-team/glibc</a></div>
    <div class="link-group-item">mirror: <a href="https://mirrors.tuna.tsinghua.edu.cn/git/glibc.git">https://mirrors.tuna.tsinghua.edu.cn/git/glibc.git</a></div>
  </div>
</div>

<div class="mono link-group">
  <div class="link-group-title">web</div>
  <div class="link-group-list">
    <div class="link-group-item">cru: <a href="https://crupest.life/git/hurd/web.git">https://crupest.life/git/hurd/web.git</a></div>
    <div class="link-group-item">upstream: <a href="https://git.savannah.gnu.org/git/hurd/web.git">https://git.savannah.gnu.org/git/hurd/web.git</a></div>
  </div>
</div>
