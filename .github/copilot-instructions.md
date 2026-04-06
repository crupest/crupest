# Project Guidelines

## Code Style
- Follow [.editorconfig](../.editorconfig): default 4-space indent, but use 2 spaces for TypeScript, shell, JSON, and YAML.
- Keep existing naming and module patterns in each area. In Deno TypeScript, prefer named exports and keep types explicit.
- Avoid broad refactors during task work. Keep edits scoped to the user request.

## Architecture
This repository has three main areas:
- `deno/`: deno workspace.
  - `base/`, `base-contrib/`: shared code and utilities.
  - `gateway/`: reverse proxy.
  - `mail/`: mail service.
  - `tools/`: CLI for service and other tools.
  - `www/`: static site generator/build pipeline.
- `services/`: definitions for programs running on a personal server. These services may depend on binaries/tools built from `deno/`.
  - `services/docker/`: each subdirectory defines one Docker image used by a service.
  - `services/config.mustache` and `services/templates/`: template and non-template config files (including `docker-compose.yaml`).
- `store/`: personal storage for convenient tools/scripts/configs/other assets. Usually independent from the main deno/services workflow unless a task explicitly targets `store/` files.

## Build and Test
- Deno workspace tasks (run from `deno/`):
  - `deno task compile:gateway`
  - `deno task compile:mail`
  - `deno task compile:tools`
  - `deno task generate:www`
- Gateway app (run from `deno/gateway/`):
  - `deno task start`
- Mail app (run from `deno/mail/`):
  - `deno task start`
- Site app (run from `deno/www/`):
  - `deno task dev`
  - `deno task generate`
- Testing, formatting, and linting (run from `deno/`):
  - `deno test` (runs all tests in the workspace)
  - `deno fmt` (formats all code in the workspace)
  - `deno lint` (runs all linters in the workspace)
- Service config/template generation:
  - `bash services/manage gen-tmpl` (dry-run)
  - `bash services/manage gen-tmpl --no-dry-run` (writes to `services/generated/`)

## Conventions
- Templates in `services/templates/` use standard mustache syntax (for example `{{CRUPEST_VAR}}` -> value). HTML escaping is disabled in the Deno rendering code (all values pass through as-is), so `{{` and `{{{` behave identically - always use `{{CRUPEST_VAR}}`. Do not introduce extra template logic or alternate delimiters.
- Templated config loading is order-sensitive: referenced variables must be defined earlier in the config files.
- Prefer not to couple `store/` changes to other subsystems unless the task explicitly requires integration.

## Pitfalls
- `services/manage` requires `deno` and `bash`; on Windows, run from an environment that provides bash (for example Git Bash or WSL).
- This repo does not define a single global lint task; verify changes with focused tests and relevant commands for the touched subsystem.