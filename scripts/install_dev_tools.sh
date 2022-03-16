#!/bin/bash

set -e

echo "pyenv: $(pyenv --version)"
echo "npm: $(npm --version)"
echo "node: $(node --version)"
echo "pip: $(pip --version)"
echo "pip3: $(pip3 --version)"
echo "python: $(python --version)"
echo "python3: $(python3 --version)"

pyenv install 3.8.12
echo "pyenv versions"
pyenv versions
pyenv global 3.8.12

CAIRO_LANG_VERSION=$(./scripts/get_version.sh cairo-lang)
pip3 install poetry "cairo-lang==$CAIRO_LANG_VERSION"

poetry env use $(which python)
