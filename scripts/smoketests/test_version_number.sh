#!/bin/sh

# check that the version number in the manual matches that of the software

printf "$0... "

fail () {
	echo "FAIL"
	echo "test $0 failed: $@"
	rm -rf "$TMP"
	exit 1
}

cd "$(dirname "$0")/../.."

MAN_VERS="$(grep newcommand < manual/pretor.sty | grep pretorvers  | cut -d '{' -f3 | cut -d ' ' -f 2 | cut -d '}' -f 1)"
PROG_VERS="$(pretor-psf --version)"

if [ "$MAN_VERS" != "$PROG_VERS" ] ; then
	fail "manual version $MAN_VERS does not match program version $PROG_VERS"
fi

echo "PASS"
exit 0
