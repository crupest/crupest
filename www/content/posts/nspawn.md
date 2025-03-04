---
title: "Use systemd-nspawn to Create a Development Sandbox"
date: 2025-03-04T23:22:23+08:00
lastmod: 2025-03-04T23:22:23+08:00
---

I often need to develop something targeted to or run non-portable toolchains on
Linux distributions other than the one I'm using. To handle these cases, I
usually create and use a "VM" of that distribution. The tool I prefer for that
purpose is called `systemd-nspawn`, and I'll show the power and share the usage
of it here.

<!--more-->

## Why `systemd-nspawn`

I've long been using traditional VMs and Docker for this purpose. While both
work fine, regardless of the performance, they suffer from being overly
isolated. Two typical headaches for me are host network sharing in traditional
VMs and the immutability of Docker container ports and mounts.

`systemd-nspawn` is much more flexible on isolation. Everything can be toggled
and configured independently, dynamically, and in detail. You can create VMs as
lightweight as you like. Filesystem sharing works like bind mounts, and network
isolation can be disabled entirely. You'll find they remove the two headaches
above from your brain. It is part of `systemd` and has the same happy user
experience.

Debian has a similar powerful tool called `schroot`. It is the official tool for
automatic package building. Unfortunately, it seems to be a tool specific to
Debian.

From now on, I'll focus on `systemd-nspawn`. To keep things simple, I'll just
use *VM* to refer to *`systemd-nspawn` VM*.

## How `systemd-nspawn` Works

`systemd-nspawn` actually **consists of 2 parts** to work like a VM. Be careful
not to mix them up!

**Part 1: A command-line program with the same name, `systemd-nspawn`, for
setting up isolated environments and running programs within them.** It supports
most state-of-the-art isolation features and provides precise control over them.
The isolation settings are passed through command-line arguments. Note that the
isolation environments are **one-shot** and not saved, so you must specify the
settings again in every single call. In short, it is **stateless**.

**Part 2: Tools for managing VMs, and performing basic maintenance.** They use
special format files to let users define VMs. These files store the identities,
isolation settings, and other information of VMs. The tools can use this data to
calculate the proper command-line arguments for `systemd-nspawn`. By correctly
creating/killing processes, they turn the **stateless** `systemd-nspawn` into
live **stateful** VMs. They also provides a simplified version of *Docker
images*, but I've never tried it myself.

## The Full Story of Using systemd-nspawn

Done with the theory, it's time to really use `systemd-nspawn`. I'll create a
*Ubuntu 20.04* VM on Arch Linux as an example. You should adjust the commands
based on your own situation.

Since it's part of `systemd`, it has a similar interface to other components:
`xxx.service` => `xxx.nspawn`, `systemctl` => `machinectl`.

### Rules

Each `.nspawn` file defines one VM. It is a `systemd` unit file with specific
sections and options. The options roughly match the command-line arguments of
`systemd-nspawn`, but some have adjusted defaults or meanings to make them more
like VMs. `machinectl` scans `/etc/systemd/nspawn/` for `.nspawn` files, so you
should put them there.

The VM defined in file `[xxx].nspawn` has the name `[xxx]`, and you can use this
name to specify the VM in `machinectl`. By default, the VM uses
`/var/lib/machines/[xxx]` as its root directory .

### Create Root Filesystem

The root filesystem of a distribution can be created using a special tool from
its **package manager**. For Debian-based distributions, the tool is called
`debootstrap`. If the package manager used by the target distribution is
different from yours, you'll need to install it first. Note that the keyrings of
that distribution may not be part of its package manager and must be installed
separately.

```bash-session
# pacman -S debootstrap debian-archive-keyring ubuntu-keyring
```

A regular directory works well as the root filesystem, but other directory-like
things should work, too. For example, if you use `btrfs` filesystem (like I do),
it's a great place to experience its subvolume and snapshot features.

```bash-session
# btrfs subvolume create /var/lib/machines/ubuntu204

```

After preparing the directory for the root filesystem, we can create the
contents with `debootstrap`. You'll first need to find the codename and a mirror
of the distribution, and then update the commands with them.

```bash-session
# debootstrap --include=dbus,libpam-systemd focal \
    /var/lib/machines/ubuntu204 https://mirrors.ustc.edu.cn/ubuntu/
```

From here, the OS can be seen as installed and ready to use. You can now
customize it as you like.

### Configure and Customize

I'll present my configuration and customization here, and briefly explain the
reasoning behind them. You can absolutely change them with your own ideas,
especially when you find any mistakes in them.

1. Disable user isolation and netword isolation entirely.
2. Create a user with the same username, group name, UID and GIDs.
3. Only bind a subdirectory under the home directory.

Except for host/VM interoperability, you can customize a VM just like a Docker
image/container.

Besides my approach, there are many other ways to get a happy-to-use filesystem
sharing experience. You only need to consider two things: **binds** and
**permissions** (effectively user mapping). Binds are just path mappings and
easy to set up. For permissions, if the VM and the host use the same user/group
and UID/GID, it will just work. However, if the user mapping feature is enabled
(implemented by the kernel's user namespace), advanced configurations are
usually required to make it work.

`systemd-nspawn` also provides a magical option to *bind the user completely* by
configuring every related thing all at once, However, I don't use this option
due to its hidden complexity. If you use this option, you should not create the
user manually in the VM, or you may get an error. For details, check the manual.

In my configuration, an identical user is required for `machinectl` to boot the
VM. Before the VM can be fully started, we have to use `systemd-nspawn` directly
to run it and complete the setup. During the process, you are free to do any
other customizations, like installing the packages you need.

```bash-session
# systemd-nspawn --resolv-conf=bind-host -D /var/lib/machines/ubuntu204

# apt install locales sudo nano vim less man bash-completion curl wget \
    build-essential git
# dpkg-reconfigure locales
# useradd -m -G sudo -s /usr/bin/bash crupest
# passwd crupest
```

Then create this file.

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
systemd](https://github.com/systemd/systemd/issues/22234), you have setup the
backport source.

```plain
/etc/apt/sources.list
---
deb https://mirrors.ustc.edu.cn/ubuntu focal main
deb https://mirrors.ustc.edu.cn/ubuntu/ focal-updates main
deb https://mirrors.ustc.edu.cn/ubuntu/ focal-backports main
deb https://mirrors.ustc.edu.cn/ubuntu/ focal-security main
```

