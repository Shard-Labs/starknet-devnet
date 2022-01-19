#!/bin/bash

set -e

CAIRO_LANG_VERSION=$(./scripts/get_version.sh cairo-lang)
pip3 install poetry "cairo-lang==$CAIRO_LANG_VERSION"
