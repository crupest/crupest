---
title: "Use systemd-nspawn to create a development \"VM\""
date: 2025-03-04T23:22:23+08:00
lastmod: 2025-03-04T23:22:23+08:00
---

There are many times when I want to develop something with toolchains that
can only run on Linux distributions other than the one I'm using. Instead of
wasting time to fight against the bad-designed non-portable toolchains, I
usually create isolated environments for development.

There are many technologies to create isolated environments today ranging from
heavy-weight ones to light-weight ones, like tier 1/2 hypervisor, docker,
chroot. However, they all have different pains for maintaining isolated
development environments. With my experience on different tools, the one I
prefer is `systemd-nspawn`. The information of it will be described in the rest
text.

<!--more-->

## Pains of Technologies

Full VMs:
- Easy to bootstrap as being widely used.
- Very slow on bad-performant hardware like laptops.
- Snapshots are too heavy.
- Hard to interact with the host environment, especially in filesystem.

Docker:
- Need some knowledge on Docker.
- Much better on performance.
- Easy to manage with "snapshots" concepts (Docker image).
- Lacks some flexibility. Described below.

The ports and mounts can only be set when creating containers and re-creating is
required to change them. That means, when you forget to mount your persistent
data, you have to use tricky ways to export it. This design is very suitable to
create reusable applications but not a development environment.

Vanilla chroot:
- No built-in functions for maintaining the environment.
- Hard to make a full working VM environment.

However, there are a lot of tools to help make a full-function environment with
chroot. Debian has a good tool called schroot. If I remember correctly, it is
used as the official tool for automatic package building by Debian. It also has
a way to make snapshots, which then can be used as a clean environment to test
reproducible build of packages.

## systemd-nspawn

`systemd-nspawn` is actually a one-shot command of running something in an isolated
environment. It is part of systemd and well supported by its maintainers.
Systemd provide full supports of managing a full environment for it to
help manage virtual environments for it. So it's basically a better schroot. The
main advantages of it are:

- Light-weight as vanilla chroot but with a more mature support of isolation. Every
  isolation features can be disabled individually.
- Host filesystems can be directly bound in it. Works just like `mount --bind`.
  Readonly binding is also supported.
- Network and filesystem settings can be changed anytime even after creation.
- Snapshots can be made in various ways of archiving, like the simplest one `tar`.
- Can be managed just like a service of systemd. It can be automatically started
  by systemd when host system starts, which means the PID 1 process of it will
  be run and startup works will be done in advance.

Following is a step-by-step guide of creating one.

### Prepare and Create
