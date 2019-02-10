#!/bin/sh

FAILED=0
RUN=0

cd "$(dirname "$0")"

echo "pretor-psf is: $(which pretor-psf)" 1>&2

for f in ./smoketests/*.sh ; do
	if ! sh "$f" ; then
		FAILED="$(expr "$FAILED" + 1)"
	fi
	RUN="$(expr "$RUN" + 1)"
done

echo "$FAILED smoketests failed of $RUN run"
exit $FAILED
