#!/bin/bash

set -e

TOML_VERSION=$(./scripts/get_version.sh version)
echo "toml version: $TOML_VERSION"
PY_VERSION=$(poetry run python -c "from starknet_devnet import __version__ as v; print(v)")
echo "py version: $PY_VERSION"

if [ "$TOML_VERSION" != "$PY_VERSION" ]; then
    echo "Inconsistent versioning across project"
    exit 1
fi
