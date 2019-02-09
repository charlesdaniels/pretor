#!/bin/sh

FAILED=0

cd "$(dirname "$0")"

for f in ./smoketests/*.sh ; do
	if ! sh "$f" ; then
		FAILED="$(expr "$FAILED" + 1)"
	fi
done

echo "$FAILED smoketests failed"
exit $FAILED
