#!/bin/bash

set -e

echo "pyenv: $(pyenv --version)"
echo "npm: $(npm --version)"
echo "node: $(node --version)"
echo "pip: $(pip --version)"
echo "pip3: $(pip3 --version)"
echo "python: $(python --version)"
echo "python3: $(python3 --version)"

echo "pyenv available versions:"
pyenv install --list

PY_VERSION=3.8.12
pyenv install "$PY_VERSION"
pyenv versions
pyenv global "$PY_VERSION"

CAIRO_LANG_VERSION=$(./scripts/get_version.sh cairo-lang)
pip3 install poetry "cairo-lang==$CAIRO_LANG_VERSION"

poetry env use $(which python)
