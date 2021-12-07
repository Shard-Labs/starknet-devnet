#!/bin/bash

# Extracts version from .toml

set -e

if [ -z "$1" ]; then
    echo "$0 <CONFIG_ENTRY>"
    exit 1
else
    ENTRY="$1"
fi

CONFIG_FILE=pyproject.toml

if [ ! -f "$CONFIG_FILE" ]; then
    echo "$0: Config file '$CONFIG_FILE' doesn't exist or not reachable"
    exit 1
fi

sed -rn "s/^$ENTRY = \"(.*)\"$/\1/p" "$CONFIG_FILE"
