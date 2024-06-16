#! /usr/bin/env bash

if [ -t 0 ]; then
    exec bash -l
else
    /bootstrap/start/code-server.bash
fi
