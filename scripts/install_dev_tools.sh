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

PY_VERSION=3.8.9

pyenv versions > installed_pyenv_versions.txt
echo "$(grep -q $PY_VERSION installed_pyenv_versions.txt )"
if ! grep -q $PY_VERSION installed_pyenv_versions.txt 
then
    pyenv install "$PY_VERSION"
fi

pyenv global "$PY_VERSION"
echo "Using global python at: $(which python)"

CAIRO_LANG_VERSION=$(./scripts/get_version.sh cairo-lang)
pip3 install poetry "cairo-lang==$CAIRO_LANG_VERSION"

poetry env use $(which python)
