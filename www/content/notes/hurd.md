---
title: "Hurd"
date: 2025-03-03T15:34:41+08:00
lastmod: 2025-03-03T23:28:46+08:00
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

## cheatsheet

### Use QEMU Virtual Machine

For i386, use

```bash-session
# qemu-system-x86_64 -enable-kvm -m 4G \
>   -net nic -net user,hostfwd=tcp::3222-:22 \
>   -vga vmware -drive cache=writeback,file=[...]
```

For x86_64, use

```bash-session
# qemu-system-x86_64 -enable-kvm -m 8G -machine q35 \
>   -net nic -net user,hostfwd=tcp::3223-:22 \
>   -vga vmware -drive cache=writeback,file=[...]
```

GRUB in the image seems to use hard-coded path of `/dev/*` block file as the
root partition in the kernel command line rather than GUID, so if the hard disk
bus is changed in QEMU and the path is changed accordingly, the system can't
boot on.

QEMU cli arguments `-machine q35` enables AHCI and SATA, and is **required for
official x86_64 image to boot**. As for i386, I haven't checked now.

### Inside Hurd

Configure/Setup network

```sh
settrans -fgap /servers/socket/2 /hurd/pfinet \
  -i /dev/eth0 -a 10.0.2.15 -g 10.0.2.2 -m 255.255.255.0
fsysopts /servers/socket/2 /hurd/pfinet \
  -i /dev/eth0 -a 10.0.2.15 -g 10.0.2.2 -m 255.255.255.0
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
