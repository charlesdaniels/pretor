#!/bin/sh

# Test that attempting to create a PSF with missing data is an error condition

TMP="$(mktemp -d)"

fail () {
	echo "FAIL"
	echo "test $0 failed: $@"
	rm -rf "$TMP"
	exit 1
}

printf "$0... "

cd "$TMP"

mkdir submission
echo "this is a test string!" > submission/file.txt

pretor-psf --create \
	--source ./submission \
	--destination ./ \
	--allow_no_toml > "$TMP/err" 2> "$TMP/out"

RES=$?


dest="$TMP/C-A-B-E-D.psf"

if [ -f "$dest" ] ; then fail "pretor-psf generated '$dest' and should not have" ; fi

if [ "$RES" -eq "0" ] ; then fail "pretor-psf exited nonzero and should not have" ; fi

rm -rf "$TMP"
echo "PASS"
exit 0
