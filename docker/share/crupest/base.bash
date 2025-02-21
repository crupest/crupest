RED="\e[31m"
GREEN="\e[32m"
YELLOW="\e[33m"
NC="\e[39m"

die() {
  echo -e "$RED(ERROR) $*$NC" >&2
  exit 1
}

note() {
  echo -e "$YELLOW(NOTE) $*$NC"
}

success() {
  echo -e "$GREEN(SUCCESS) $*$NC"
}

check_root() {
  if [[ $EUID -ne 0 ]]; then
    die "This script must be run as root"
  fi
}

check_env() {
  local var
  for var in "$@"; do
    [[ -n "${!var}" ]] || die "Environment variable $var is not set."
  done
}

import_env() {
  note "Importing environment variables from $1 for" "${@:2}"
  [[ -f "$1" ]] || die "Environment file $1 does not exist."
  # shellcheck source=/dev/null
  . "$1"
  check_env "${@:2}"
  success "Environment variables imported from $1"
}

clean_env() {
  local var
  note "Cleaning environment variables:" "$@"
  for var in "$@"; do
    unset "$var"
  done
}

DOCKER_SECRETS_PATH="/run/secrets/"

import_docker_secrets() {
  local var secret_file="$DOCKER_SECRETS_PATH$1"
  note "Import Docker secrets $1 for" "${@:2}"
  [[ -f "$secret_file" ]] || die "Docker secrets file $1 does not exist."
  # shellcheck source=/dev/null
  . "$secret_file"
  for var in "${@:2}"; do
    [[ -z "${!var}" ]] && die "Secret variable $var is not set."
  done
  success "Import Docker secrets $1 completed."
}

instantiate_template() {
  local template_file="$1.template"
  note "Instantiate template file $template_file with" "${@:2}"
  [[ -f "$template_file" ]] || die "File $template_file does not exist."
  for var in "${@:2}"; do
    check_env "$var"
    sed "s|@@$var@@|${!var}|g" "$template_file" > "$1"
  done
  success "Template file $template_file instantiated. Resulting file is $1."
}

instantiate_template_recursive() {
  find "$1" -type f -name "*.template" | while read -r template_file; do
    instantiate_template "${template_file%.template}" "${@:2}"
  done
}

check_template_instantiation() {
  find "$1" -type f | grep -v -E "\.template$" | while read -r file; do
    grep "@@" "$file" && die "Template variable not instantiated in $file."
  done
}
