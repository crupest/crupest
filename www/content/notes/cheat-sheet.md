---
title: "Cheat Sheet"
date: 2025-04-01T23:09:53+08:00
lastmod: 2025-06-12T01:09:39+08:00
---

{{< mono >}}

goto: [Hurd Cheat Sheet (in a separated page)](/notes/hurd/cheat-sheet)

{{< /mono >}}

## GRUB

Update GRUB after `grub` package is updated. Replace `/boot` with your mount
point of the EFI partition in `--efi-directory=/boot`. Replace `GRUB` with your
bootloader id in `--bootloader-id=GRUB`.

```sh
grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=GRUB
grub-mkconfig -o /boot/grub/grub.cfg
```

## (Private) My Service Infrastructure Management

All commands should be run at the project root path.

### Install Deno

Script from <https://docs.deno.com/runtime/getting_started/installation/>

```sh
curl -fsSL https://deno.land/install.sh | sh
```

### Add Git Server User / Set Password

```sh
docker run -it --rm -v "./data/git/user-info:/user-info" httpd htpasswd /user-info [username]
```

### Certbot

A complete command is `[prefix] [docker (based on challenge kind)] [command] [challenge] [domains] [test] [misc]`

| part | for | segment |
| --- | --- | --- |
| prefix | * | `docker run -it --rm --name certbot -v "./data/certbot/certs:/etc/letsencrypt" -v "./data/certbot/data:/var/lib/letsencrypt"` |
| docker | challenge standalone | `-p "0.0.0.0:80:80"` |
| docker | challenge nginx | `-v "./data/certbot/webroot:/var/www/certbot"` |
| command | create/expand/shrink | `certonly` |
| command | renew | `renew` |
| challenge | standalone | `--standalone` |
| challenge | nginx | `--webroot -w /var/www/certbot` |
| domains | * | `[-d [domain]]...` |
| test | * | `--test-cert --dry-run` |
| misc | agree tos | `--agree-tos` |
| misc | cert name | `--cert-name [name]` |
| misc | email | `--email [email]` |

For example, **test** create/expand/shrink with standalone server:

```sh
docker run -it --rm --name certbot \
  -v "./data/certbot/certs:/etc/letsencrypt" -v "./data/certbot/data:/var/lib/letsencrypt"` \
  -p "0.0.0.0:80:80" \
  certonly \
  --standalone \
  -d crupest.life -d mail.crupest.life \
  --test-cert --dry-run
```

## System Setup

### Debian setup

#### Setup SSL Certificates and Curl

```sh
apt-get update
apt-get install ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
```

### Docker Setup

#### Uninstall Packages Provided by Stock Repo

```bash
for pkg in docker.io docker-doc docker-compose \
    podman-docker containerd runc; do
  apt-get remove $pkg;
done
```

#### Install Certs From Docker

Remember to [setup ssl and curl](#setup-ssl-certificates-and-curl) first.

```sh
curl -fsSL https://download.docker.com/linux/debian/gpg \
  -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
```

#### Add Docker Repos

```bash
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null
```

#### Install Docker Packages

```sh
apt-get update
apt-get install docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin
```

#### Start And Enable Docker

Remember to log out and log back to let user group change take effects.

```sh
systemctl enable docker
systemctl start docker
groupadd -f docker
usermod -aG docker $USER
```
