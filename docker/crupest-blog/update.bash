#! /usr/bin/env bash

set -e

echo -e "\e[0;103m\e[K\e[1mBegin to build blog...\e[0m"
echo "Begin time: $(date +%Y-%m-%dT%H:%M:%SZ)"

# check /blog directory exists
if [[ ! -d /blog ]]; then
    echo "Directory /blog not found, clone blog repository..."
    git clone https://github.com/crupest/blog.git /blog
    cd /blog
    git submodule update --init --recursive
else
    echo "Directory /blog founded, update blog repository..."
    cd /blog
    git fetch -p
    git reset --hard origin/master
    git submodule update --init --recursive
fi

# Now hugo it
echo "Run hugo to generate blog..."
hugo

echo "Finish time: $(date +%Y-%m-%dT%H:%M:%SZ)"
echo -e "\e[0;102m\e[K\e[1mFinish build!\e[0m"

