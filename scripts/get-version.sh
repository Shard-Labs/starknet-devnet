#!/bin/bash

# Extracts version from .toml

if [ -n "$1" ]; then
    CONFIG_FILE="$1"
fi

if [ ! -f "$CONFIG_FILE" ]; then
    echo "$0: Valid file must be provided either by env var CONFIG_FILE or as a command-line argument"
    exit 1
fi

sed -rn "s/^.*version = \"(.*)\"$/\1/p" "$1"
