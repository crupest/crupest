This directory contains the template files to generate the final config files.
The template format is quite simple: they are just files containing `{{VAR}}`s. You can simply use text substitution to do the generation. All variable names begin with `CRUPEST_` to avoid name conflicts.

Run `generate.py` and it will help you configure and generate the final config files.

Here are the variables used in templates:
| Variable | Description |
| -------- | ----------- |
| CRUPEST_DOMAIN | Domain to deploy. |
| CRUPEST_UID | Your uid. Run `id -u` to get it. |
| CRUPEST_GID | Your gid. Run `id -g` to get it. |
| CRUPEST_HALO_DB_PASSWORD | Used as halo's h2 database password. Better not to change it after first run. |
