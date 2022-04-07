#!/bin/bash

set -e

echo "pyenv: $(pyenv --version)"
echo "npm: $(npm --version)"
echo "pip: $(pip --version)"
echo "pip3: $(pip3 --version)"
echo "python: $(python --version)"
echo "python3: $(python3 --version)"

which poetry || pip3 install poetry
echo "poetry: $(poetry --version)"

# install dependencies
poetry install
npm ci
