# Project Guidelines

## Code Style
- Follow [.editorconfig](../.editorconfig): default 4-space indent, but use 2 spaces for TypeScript, shell, JSON, and YAML.
- Keep existing naming and module patterns in each area. In Deno TypeScript, prefer named exports and keep types explicit.
- Avoid broad refactors during task work. Keep edits scoped to the user request.

## Architecture
This repository has four main areas:
- `deno/`: Deno workspace with `base/` (shared utilities), `mail/` (mail pipeline + HTTP app), and `tools/` (CLI for service and VM management).
- `services/`: Definitions for programs running on a personal server. These services may depend on binaries/tools built from `deno/`.
  - `services/docker/`: each subdirectory defines one Docker image used by a service.
  - `services/config.template` and `services/templates/`: template and non-template config files (including `docker-compose.yaml`).
- `store/`: personal storage for convenient tools/scripts/configs/other assets. Usually independent from the main deno/services/www workflow unless a task explicitly targets `store/` files.
- `www/`: Hugo static site (content, layouts, assets, env-specific config).

## Build and Test
- Deno workspace tasks (run from `deno/`):
  - `deno task compile:mail`
  - `deno task compile:tools`
- Mail app (run from `deno/mail/`):
  - `deno task run`
- Tests:
  - `deno test deno/mail`
  - or targeted: `deno test deno/mail/mail.test.ts` and `deno test deno/mail/db.test.ts`
- Service config/template generation:
  - `bash services/manage gen-tmpl` (dry-run)
  - `bash services/manage gen-tmpl --no-dry-run` (writes to `services/generated/`)

## Conventions
- Treat templating in `services/templates/` as simple variable replacement (for example `@@CRUPEST_VAR@@` -> value); do not introduce extra template logic or alternate delimiters.
- Templated config loading is order-sensitive: referenced variables must be defined earlier in the config files.
- Prefer not to couple `store/` changes to other subsystems unless the task explicitly requires integration.

## Pitfalls
- `services/manage` requires `deno` and `bash`; on Windows, run from an environment that provides bash (for example Git Bash or WSL).
- The mail-server integration relies on Dovecot tools/paths in container context. Avoid host-path assumptions when changing mail delivery code.
- This repo does not define a single global lint task; verify changes with focused tests and relevant commands for the touched subsystem.