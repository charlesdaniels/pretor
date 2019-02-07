#!/bin/sh

# Run unit tests in a virtualenv

set -e
set -u

cd "$(dirname "$0")"

VENVDIR="$(./prep_env.sh)"

. "$VENVDIR/bin/activate"

cd ..

python3 setup.py install

cd test

if ! python3 -m unittest discover ; then
	rm -rf "$VENVDIR"
	exit 1
else
	rm -rf "$VENVDIR"
	exit 0
fi
