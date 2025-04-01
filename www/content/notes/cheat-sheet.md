---
title: "Cheat Sheet"
date: 2025-04-01T23:09:53+08:00
lastmod: 2025-04-01T23:09:53+08:00
---

Update GRUB after `grub` package is updated. Replace `/boot` with your mount
point of the EFI partition in `--efi-directory=/boot`. Replace `GRUB` with your
bootloader id in `--bootloader-id=GRUB`.

```bash-session
grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=GRUB
grub-mkconfig -o /boot/grub/grub.cfg
```
