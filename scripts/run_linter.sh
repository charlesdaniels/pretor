#!/bin/sh

# run flake8 linter

set -e
set -u

cd "$(dirname "$0")/.."

black --check ./pretor
