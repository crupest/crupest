---
title: "Use systemd-nspawn to Create a Development Sandbox"
date: 2025-03-04T23:22:23+08:00
lastmod: 2025-03-27T17:46:24+08:00
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

*systemd-nspawn* consists of two parts that work together to achieve its VM
functionality:

1. The program `systemd-nspawn`, which runs other programs in an isolated
   environment with user-specified settings. Each running VM is essentially a
   group of processes launched via `systemd-nspawn`.
2. Components for defining and managing VMs, possibly utilizing
   `systemd-nspawn`.

*systemd-nspawn* has a user interface similar to *systemd service*:

- `[name].service` => `[name].nspawn`: Define VMs.
  - Should be placed in `/etc/systemd/nspawn/`, where `machinectl` scans for VM
    definitions.
  - `[name]` serves as the VM's name. Use it to specify the VM when calling
    `machinectl`. Note: You'd better use a valid hostname (avoid illegal
    characters like `.`) to prevent weird errors.
  - The options available roughly mirror `systemd-nspawn`'s CLI arguments, with
    some adjustments to better fit VM semantics.
  - Isolation-related options are usually prefixed with `Private` (e.g.,
    `PrivateUsers=`).
- `systemctl` => `machinectl`: Manage VMs.
  - `enable`/`disable`: Set whether the VM starts automatically at system boot.
  - `start`/`poweroff`/`reboot`/`terminate`/`kill`: Control the VM's running
    state.
  - `login`/`shell`: Do things inside the VM.

I'll demonstrate how to create a Debian-based VM on Arch Linux as an example.
You should adjust the commands based on your own situation.

### Create Root Filesystem

The root filesystem of a distribution can be created using a special tool from
its package manager. For Debian-based distributions, it's `debootstrap`. If your
OS uses a different package manager ecosystem, the target distribution's one and
its keyrings (which might reside somewhere else) have to be installed first.

```bash-session
# pacman -S debootstrap debian-archive-keyring ubuntu-keyring
```

Regular directories work perfectly as root filesystems, but other directory-like
things should work, too, such as `btrfs` subvolume.

```bash-session
# btrfs subvolume create /var/lib/machines/[name]
```

Now, run `debootstrap` to create a minimal filesystem. Update the command with
the target distribution's codename and one of its mirrors you select.

```bash-session
# debootstrap --include=dbus,libpam-systemd [codename] \
    /var/lib/machines/[name] [mirror]
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
4. Only bind a subdirectory under *home*: `[Files] Bind=/home/[user]/[subdir]`
5. Set the hostname: `[Exec] Hostname=[hostname]`

I disable user isolation because it's implemented using the kernel's user
namespace, which adds many inconveniences due to UID/GID mapping.

So, the final `.nspawn` file is like:

```systemd
/etc/systemd/nspawn/[name].nspawn
---
[Exec]
PrivateUsers=no
Hostname=[hostname]

[Files]
Bind=/home/[user]/[subdir]

[Network]
Private=no
```

If `machinectl` can already start the VM, you can log in to customize it
further. Otherwise, you can use `systemd-nspawn` directly to enter the VM and
run commands inside it. `--resolv-conf=bind-host` binds the host's
`/etc/resolv.conf` file to make the network work.

```bash-session
# systemd-nspawn --resolv-conf=bind-host -D /var/lib/machines/[name]
```

Now, inside the VM, you can do whatever you like. In my configuration, a correct
user must be created manually.

```bash-session
# apt install locales sudo nano vim less man bash-completion curl wget \
    build-essential git
# dpkg-reconfigure locales

# useradd -m -G sudo -s /usr/bin/bash [user]
# passwd [user]
```

Some setup may need to be done manually, especially those usually handled by the
distribution's installer.

1. Update `/etc/hostname` with the VM's real hostname.
2. Update `/etc/hosts`.

```plain
/etc/hosts
---
127.0.0.1       localhost [hostname]
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

### Use

The following command starts a new shell session for the specified user inside
the VM, where you can run commands and perform tasks.

```bash-session
# machinectl shell [user]@[name]
```

Another way is to use `login` command to enter the *login console*. From there,
you can log in as a user to start a shell session.

```bash-session
# machinectl login [name]
```

To exit a VM session (especially in the *login console*), press `CTRL+]` three
times quickly in a row.

### Snapshot

The easiest way to backup/snapshot a VM is to create an archive of the VM's
filesystem. You can use any archive tool you prefer, such as the simple `tar`.
If the VM's filesystem is a `btrfs` subvolume, native `btrfs` snapshots can be
used here. Before creating a snapshot, you should power off the VM to avoid
archiving runtime files.

```bash-session
# machinectl poweroff [name]
# btrfs subvolume snapshot /var/lib/machines/[name] \
    /var/lib/machines/btrfs-snapshots/[name]/[snapshot-name]
```

`machinectl` also provides an *image* feature similar to Docker, though I've
never tried it. Feel free to explore it if you're interested!
