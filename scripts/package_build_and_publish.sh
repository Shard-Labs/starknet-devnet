#!/bin/bash
set -e

PYPI_VERSION=$(curl -Ls https://pypi.org/pypi/starknet-devnet/json | jq ".releases | keys | .[length-1]" -r)
LOCAL_VERSION=$(./get-version.sh)

poetry build
poetry publish --username "$PYPI_USER" --password "$PYPI_PASS"
