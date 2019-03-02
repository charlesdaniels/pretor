#!/bin/sh

cd "$(dirname "$0")/.."

if ! xenon --max-absolute C --max-modules A --max-average A pretor ; then
	radon cc pretor -a -na
	exit 1
else
	echo "complexity looks OK!"
	exit 0
fi
