#!/bin/sh

# run flake8 linter

set -e
set -u

RATCHET=300

cd "$(dirname "$0")/.."

if [ "$(flake8 pretor | wc -l)" -gt "$RATCHET" ] ; then
	echo "too many linter errors, exceeded $RATCHET"
	exit 1
else
	exit 0
fi

