#!/bin/sh

# Run unit tests in a virtualenv

set -e
set -u

cd "$(dirname "$0")"

cd ..

echo "installing pretor... " 1>&2
python3 setup.py install 2>&1 > /dev/null

cd test
echo "running tests... " 1>&2

if ! python3 -m unittest discover ; then
	echo "tests failed!" 1>&2
	exit 1
else
	echo "tests OK" 1>&2
	exit 0
fi
