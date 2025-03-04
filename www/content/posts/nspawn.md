---
title: "Use systemd-nspawn to Create a Development Sandbox"
date: 2025-03-04T23:22:23+08:00
lastmod: 2025-03-27T01:32:40+08:00
---

*systemd-nspawn* is a great tool for creating development sandboxes. Compared to
other similar technologies, it's lightweight, flexible, and easy to use. In this
blog, I'll present a simple guide to using it.

<!--more-->

## Advantages

I've been using traditional VMs and Docker for creating development
environments. While both work fine, regardless of the performance, they suffer
from being overly isolated. Two big headaches for me are host network sharing in
traditional VMs and the immutability of Docker container ports and mounts.

*systemd-nspawn* is much more flexible. Every feature can be configured
granularly and dynamically. For example, filesystem sharing can be configured to
work like bind mounts, and network isolation can be disabled entirely, which
exactly solves the two headaches mentioned above. Additionally, being part of
*systemd*, it has the same excellent design as other *systemd* components.

Debian has a similar powerful tool called *schroot*. It is the official tool for
automatic package building. Unfortunately, it seems to be a tool specific to
Debian.

## Usage

I'll demonstrate how to create a *Ubuntu 20.04* VM on Arch Linux as an example.
You should adjust the commands based on your own situation.

*systemd-nspawn* consists of two parts that work together to achieve its VM
functionality:
1. The program `systemd-nspawn`, which runs other programs in an isolated
   environment with user-specified settings. Each running VM is essentially a
   group of processes launched via `systemd-nspawn`.
2. Components for defining and managing VMs, possibly utilizing
   `systemd-nspawn`.

*systemd-nspawn* has similar usage to *systemd service*:

- `[name].service` => `[name].nspawn`: VM definitions.
  - Should be placed in `/etc/systemd/nspawn/`, where `machinectl` scans for VM
    definitions.
  - `[name]` serves as the VM's name and should be used to specify the VM when
    calling `machinectl`. Note: You'd better use the VM's hostname as its value
    (avoid illegal characters like `.`) to prevent weird issues caused by the
    inconsistency.
  - The options available roughly mirror `systemd-nspawn`'s CLI arguments, with
    some adjustments to better fit VM semantics.
  - Isolation-related options are usually prefixed with `Private` (e.g.,
    `PrivateUsers=`).
- `systemctl` => `machinectl`: VM management.
  - `enable`/`disable`: Set whether the VM starts automatically at system boot.
  - `start`/`poweroff`/`reboot`/`terminate`/`kill`: Control the VM's running
    state.
  - `login`/`shell`: Do things inside the VM.

### Create Root Filesystem

The root filesystem of a distribution can be created using a special tool from
its **package manager**. For Debian-based distributions, it's `debootstrap`. If
your OS uses a different package manager ecosystem, the target distribution's
one and its keyrings (which might reside somewhere else) need to be installed
first.

```bash-session
# pacman -S debootstrap debian-archive-keyring ubuntu-keyring
```

Regular directories work perfectly as root filesystems, but other directory-like
things should work, too, such as `btrfs` subvolume and snapshot.

```bash-session
# btrfs subvolume create /var/lib/machines/ubuntu204
```

Now, run `debootstrap` to create a minimal filesystem. The following command
should be modified with the target distribution's codename and one of its
mirrors selected by you.

```bash-session
# debootstrap --include=dbus,libpam-systemd focal \
    /var/lib/machines/ubuntu204 https://mirrors.ustc.edu.cn/ubuntu/
```

At this point, the filesystem contains only the distribution's essential
packages, much like a base Docker image (e.g., `debian`), so you can customize
it in a similar way.

### Configure and Customize

I'll present my personal configuration here as a reference. You can create a new
one based on it or from scratch.

1. Disable user isolation: `[Exec] PrivateUsers=no`
2. Disable network isolation: `[Network] Private=no`
3. Create a user with the same username, group name, UID and GIDs: should be
   done inside the VM.
4. Only bind a subdirectory under *home*: `[Files] Bind=/home/crupest/codes`
5. Set the hostname: `Hostname=[xxx]`

I disable user isolation because it's implemented using the kernel's user
namespace, which adds many inconveniences due to UID/GID mapping.

So, the final `.nspawn` file is like:

```systemd
/etc/systemd/nspawn/ubuntu204.nspawn
---
[Exec]
PrivateUsers=no
Hostname=crupest-arch-ubuntu204

[Files]
Bind=/home/crupest/codes

[Network]
Private=no
```

If `machinectl` can already start the VM, you can log in to customize it
further. Otherwise, you can use `systemd-nspawn` directly to enter the VM and
run commands inside it. `--resolv-conf=bind-host` binds the host's
`/etc/resolv.conf` file to make the network work.

```bash-session
# systemd-nspawn --resolv-conf=bind-host -D /var/lib/machines/ubuntu204
```

Now, inside the VM, you can do whatever you like. In my configuration, a correct
user must be created manually.

```bash-session
# apt install locales sudo nano vim less man bash-completion curl wget \
    build-essential git
# dpkg-reconfigure locales

# useradd -m -G sudo -s /usr/bin/bash crupest
# passwd crupest
```

Some setup may need to be done manually, especially those usually handled by the
distribution's installer.

```plain
/etc/hostname
---
crupest-arch-ubuntu204
```

```plain
/etc/hosts
---
127.0.0.1       localhost crupest-arch-ubuntu204
::1             localhost ip6-localhost ip6-loopback
ff02::1         ip6-allnodes
ff02::2         ip6-allrouters
```

**Ubuntu 20.04 specific:** Due to [a bug in
systemd](https://github.com/systemd/systemd/issues/22234), the backport source
has to be added.

```plain
/etc/apt/sources.list
---
deb https://mirrors.ustc.edu.cn/ubuntu focal main
deb https://mirrors.ustc.edu.cn/ubuntu/ focal-updates main
deb https://mirrors.ustc.edu.cn/ubuntu/ focal-backports main
deb https://mirrors.ustc.edu.cn/ubuntu/ focal-security main
```

