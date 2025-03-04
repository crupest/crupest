---
title: "Use systemd-nspawn to Create a Development Sandbox"
date: 2025-03-04T23:22:23+08:00
lastmod: 2025-03-04T23:22:23+08:00
---

I often need to develop something for or run non-portable toolchains on Linux
distributions other than the one I'm using. To handle these cases, I usually
create and use a "VM" of that distribution. The tool I prefer for that purpose
is called `systemd-nspawn`, and I'll show the power and share the usage of it
here.

<!--more-->

## Why `systemd-nspawn`

Traditional VMs are slow and nearly unusable on my laptop. The methods of
syncing files are ugly and upsetting. Due to the network isolation, additional
configurations such as port forwarding are usually required, unlike working
directly on the host.

Docker is fast. However, since it is primarily designed for building and
deploying apps, it is still too heavyweight for our needs. Specifically, the
flexibility of isolation configuration is quite limited, which can lead to many
inconveniences. **The biggest headache for me is that ports and mounts of a
container cannot be changed after its creation.** This forces you to deal with
exporting persistent data for missing mounts.

The isolation function of `systemd-nspawn` is much more flexible. Nearly every
part can be switched on/off and configured in detail, independently and
dynamically. You can create a VM as lightweight as you like. File sharing works
just like bind mounts. By disabling the network isolation, the VM shares the
network stack with the host. Is is part of `systemd` and tightly integrated with
it.

Debian has a great tool called `schroot`, which offers similar functionality. It
is also the official tool for automatic package building. By providing
sufficient supplementary functions, it turns vanilla `chroot` into a
full-featured isolated environment. Unfortunately, it seems to be a
Debian-specific tool.

## How `systemd-nspawn` Works

From now on, we focus on `systemd-nspawn`. I'll just use VM for `systemd-nspawn`
VM.

The full function of `systemd-nspawn` to create and maintain a VM actually
**consists of two parts**. It's very easy to get stuck at some point due to
mistakenly mixing them.

### Part 1: Run a Command with Configurable Isolation

`systemd-nspawn` itself is a command-line program that runs programs with
isolation settings specified via command-line arguments. When you invoke
`systemd-nspawn`, it will handle the complex setup of the isolated environment
and run the given program within it. It supports nearly all state-of-the-art
isolation features.

**Note:** The setup of isolation environment is **one-shot**, meaning the
settings are not persisted. You must specify them again via command-line
arguments in each new invocation. That's why I describe it as **stateless**.

`systemd-nspawn` is used to start programs and make the VM alive/power-on. When
all processes exit, the VM becomes dead/power-off.

### Part 2: Persist State and Manage Like Services

To turn `systemd-nspawn` into a real VM, a tool is required to manage its state.
Generally, the state should at least includes filesystems and settings of
isolation. With this information, you can restart the dead VM with
`systemd-nspawn`.

Though you can create your own tools based on these ideas, `systemd-nspawn`
already takes care of inventing the wheel for you. It comes with a full-featured
toolset to perform these tasks.

## The Full Story of Using systemd-nspawn

It works much like `systemd` services.

`xxx.service` => `xxx.nspawn`\
`systemctl` => `machinectl`

Each `.nspawn` file defines a VM and saves its information and configuration. It
follows the format of standard `systemd` unit files. `machinectl` is the
command-line tool to manage VMs along with the `.nspawn` files. It also provides
other useful functions like exporting and importing VMs.

### Conventions

There are some conventions in `systemd-nspawn` tools that greatly simplify
configuration. `machinectl` uses them to locate VMs. Some of the most important
ones are:

- `[id].nspawn` files should be placed in `/etc/systemd/nspawn/`.
- `[id]` in the file name serves as the *ID* of the VM.
- The root directory of the VM with `[id]` is located at
  `/var/lib/machines/[id]`.

In this article, I'll demonstrate how to create a VM running *Ubuntu 20.04*
using `systemd-nspawn` (because I'm going to use that). We'll achieve this in
two steps: setting up a fresh filesystem and creating a `.nspawn` file for it.

 These items roughly correspond to
the command-line arguments of `systemd-nspawn`, though some have different
defaults or meanings to better align with the semantics of VM. All adjustments
are reasonable and shouldn't cause much confusion. For the full list of items,
refer to the `systemd` manual. In my story, only fewer than 10 of them are used,
and they are already sufficient for our purpose.

### Filesystem

If you've always installed Linux distributions with their GUI installers without
understanding the key principles and steps behind it, I'd strongly suggest
learning them (this applies to any GUI software). Doing so will help you gain a
deeper understanding of how an OS works. Of course, you don't need to memorize
the exact commands executed by the installer. :)

One essential step is creating and populating the basic filesystem using the
distribution's **package manager**. For example, in Debian, a program called
`debootstrap`, part of the `dpkg` ecosystem, is responsible for that task. Most
people may not be familiar with it, because it’s not typically needed for
everyday tasks.

If you are not using a Debian-based distribution, `dpkg` and `debootstrap` are
likely available as regular packages, and you can install them directly with
your package manager. Though it might seem a little wired, these tools are
normal programs, after all. Their functions other than package management still
work. In fact, those functions are essential to perform Debian-related tasks on
the distributions not based on it. This principle also applies to other
ecosystems, such as `rpm` in Red Hat-based distributions.

Note that you may need to install keyrings of Debian/Ubuntu. Without them,
`dpkg` and `apt` might refuse to install packages due to integrity and
authentication checks.

For Arch Linux, just run:

```sh
# pacman -S debootstrap debian-archive-keyring ubuntu-keyring

```

By convention, the root filesystem of VM defined by `[id].nspawn` should be
located at `/var/lib/machines/[id]`. It can be a regular directory or a symbolic
link. Using a regular directory is the simplest approach and works perfectly,
while equivalents of it should also work. Note that modifying files here usually
requires the privilege permissions.

If you happen to use `btrfs` filesystem (I do), it's a great opportunity here to
taste its subvolume and snapshot function. Here is the command to create a
subvolume. Change the path as you like.

```bash
# sudo btrfs subvolume create /var/lib/machines/ubuntu20.4

```

Now it's time to populate the content with `debootstrap`. Before we do that, I
want to mention some details related. All Debian-variated distributions
including Ubuntu use the ecosystem of `dpkg`, so `debootstrap` work for all of
them. Just specify the corresponding apt sources and codename. The apt sources
can be a mirror. Old versions of Debian are not in the official pool of it, so
you need an archive mirror.

