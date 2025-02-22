# shellcheck disable=SC2046
export $(xargs < "${script_dir:?}/base-config") 

CRUPEST_PROJECT_DIR="$(realpath "$script_dir/..")"
export CRUPEST_PROJECT_DIR
