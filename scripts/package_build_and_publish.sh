#!/bin/bash
set -e

[ -f .env ] && source .env

PYPI_VERSION=$(curl -Ls https://pypi.org/pypi/starknet-devnet/json | jq ".releases | keys | .[length-1]" -r)
echo "Pypi version: $PYPI_VERSION"

LOCAL_VERSION=$(./scripts/get_version.sh version)
echo "Local version: $LOCAL_VERSION"

# Building is executed regardles of versions
poetry build

if [ "$PYPI_VERSION" = "$LOCAL_VERSION" ]; then
    echo "Latest pypi version is already equal to the local version."
    echo "Publishing skipped"
else
    poetry publish --username "$PYPI_USER" --password "$PYPI_PASS"
fi
