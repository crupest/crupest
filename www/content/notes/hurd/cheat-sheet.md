---
title: "Hurd Cheat Sheet"
date: 2025-06-12T00:59:16+08:00
lastmod: 2025-06-14T20:34:06+08:00
---

## Mirrors

The mirror has to be `debian-ports`, not `debian`, and many mirror sites do not
provide it. Following is aliyun mirror:

```txt
/etc/apt/sources.list
---
deb https://mirrors.aliyun.com/debian-ports/ unstable main
deb https://mirrors.aliyun.com/debian-ports/ unreleased main
deb-src https://mirrors.aliyun.com/debian/ unstable main
```

The hurd-amd64 deb-src seems to not work.

## Use QEMU Virtual Machine

For i386, use

```sh
qemu-system-x86_64 -enable-kvm -m 4G \
  -net nic -net user,hostfwd=tcp::3222-:22 \
  -vga vmware -drive cache=writeback,file=[...]
```

For x86_64, use

```sh
qemu-system-x86_64 -enable-kvm -m 8G -machine q35 \
  -net nic -net user,hostfwd=tcp::3223-:22 \
  -vga vmware -drive cache=writeback,file=[...]
```

GRUB in the image seems to use hard-coded path of `/dev/*` block file as the
root partition in the kernel command line rather than GUID, so if the hard disk
bus is changed in QEMU and the path is changed accordingly, the system can't
boot on.

QEMU cli arguments `-machine q35` enables AHCI and SATA, and is **required for
official x86_64 image to boot**. As for i386, I haven't checked now.

There is [a Deno script](https://github.com/crupest/crupest/blob/dev/deno/tools/manage-vm.ts)
written by me to help define and build QEMU cli arguments of VMs.

## Inside Hurd

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
