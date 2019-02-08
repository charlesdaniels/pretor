#!/bin/sh

set -e
set -u

# Setup a temp directory as a virtualenv for testing

if [ ! -x "$(which virtualenv)" ] ; then
	echo "virtualenv is not installed" 1>&2
	exit 1
fi

if [ ! -x "$(which python3)" ] ; then
	echo "python3 is not installed" 1>&2
	exit 1
fi

VENVDIR="$(mktemp -d)"

echo "creating virtualenv... " 1>&2
virtualenv --python="$(which python3)" "$VENVDIR" 2>&1 > /dev/null

echo "$VENVDIR"
