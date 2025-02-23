#! /usr/bin/env bash

set -e

cd /app/src/
ls -l .
[[ ! -d public ]] || rm -rf public
hugo
