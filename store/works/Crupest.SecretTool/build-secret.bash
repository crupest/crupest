#! /usr/bin/env bash

set -e

function print_argument_error_message_and_exit() {
    argument_error_message="You must specify exactly one argument, the build target (win-x64 | linux-x64 | osx-x64)."
    echo "$argument_error_message"
    exit 1
}



if [[ $# != 1 ]]; then
    print_argument_error_message_and_exit
fi

case "$1" in
    win-x64 | linux-x64 | osx-x64)
        echo "Build target: $1"
    ;;
    *)
        print_argument_error_message_and_exit
    ;;
esac

secret_dir=$(realpath "$(dirname "$0")")

echo "Secret dir: ${secret_dir}"

echo "Check dotnet..."
dotnet --version

echo "Enter \"secret\" dir..."
pushd "$secret_dir"

echo "Begin to build..."
dotnet publish Crupest.SecretTool -c Release -o "$secret_dir/publish" --sc -r "$1"

popd

echo "Finish!"
