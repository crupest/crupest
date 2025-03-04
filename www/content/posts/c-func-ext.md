---
title: "Libc/POSIX Function \"Extensions\""
date: 2025-03-04T13:40:33+08:00
lastmod: 2025-03-04T13:40:33+08:00
categories: coding
tags:
  - c
  - posix
---

Recently, I've been working on porting libraries to GNU/Hurd. The maintainers of GNU/Hurd
have a strong belief that [`*_MAX` macros on POSIX system interfaces](https://pubs.opengroup.org/onlinepubs/9699919799.2008edition/nframe.html)
are very evil things. This is indeed true as a lot of (old) libraries relying on those macros
to determine the buffer size. In modern programming world, it is definitely a bad
idea to use fixed values for buffer sizes without considering possible overflow, unless
you are certain that size is sufficient.

When you get rid of some old things, you will always meet compatibility problems. In these
case, old source codes using these macros just do not compile now. So here are some

<!--more-->


