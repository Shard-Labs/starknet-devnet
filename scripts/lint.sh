#!/bin/bash

set -e

poetry run pylint $(git ls-files '*.py')
