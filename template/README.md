This directory contains the template files used to generate the final config files. They should not be used directly usually. Run `../tool/setup.py` to perform any generation and necessary setup.

The template format is quite simple: they are just files containing `$VAR`s or `${VAR}`s. All variable names begin with `CRUPEST_` to avoid name conflicts.

Here are the variables used in templates:
| Variable | Description |
| -------- | ----------- |
| `CRUPEST_DOMAIN` | Domain to deploy. |
| `CRUPEST_EMAIL` | Email address used in some cases like ssl cert. |
| `CRUPEST_USER` | Your username. Run `id -un` to get it. |
| `CRUPEST_GROUP` | Your group. Run `id -gn` to get it. |
| `CRUPEST_UID` | Your uid. Run `id -u` to get it. |
| `CRUPEST_GID` | Your gid. Run `id -g` to get it. |
| `CRUPEST_HALO_DB_PASSWORD` | Used as halo's h2 database password. Better not to change it after first run. |
| `CRUPEST_IN_CHINA` | Set to `true` if you are in China. |

Note:

1. `CRUPEST_{USER,GROUP,UID,GID}` are used to sync your account to some containers like `code-server` to avoid permission problems. You don't bother to manually set them as the python script will do it for you. However if you change them, you need to manually update it in config and regenerate something. But I don't really think you should change them.

2. `CRUPEST_IN_CHINA` is used to set the mirror for some containers both in themselves or in the process of building them. It is default to `false`. If you are in China, you can set it to `true` to speed up the process.
