#!/bin/bash

# Extracts version from .toml

if [ -n "$1" ]; then
    CONFIG_FILE="$1"
else
    CONFIG_FILE=pyproject.toml
fi

if [ ! -f "$CONFIG_FILE" ]; then
    echo "$0: Config file '$CONFIG_FILE' doesn't exist or not reachable"
    exit 1
fi

sed -rn "s/^.*version = \"(.*)\"$/\1/p" "$CONFIG_FILE"
