#!/bin/sh

# test that a pretor.toml which requires a newer version of Pretor causes an
# error

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
echo 'minimum_version ="999999.0.0"' > submission/pretor.toml

pretor-psf --create \
	--source ./submission \
	--destination ./ \
	--course "A" \
	--section "B" \
	--semester "C" \
	--assignment "D" \
	--group "E" > "$TMP/err" 2> "$TMP/out"

RES=$?


dest="$TMP/C-A-B-E-D.psf"

if [ -f "$dest" ] ; then fail "pretor-psf generated '$dest'" ; fi

if [ "$RES" -eq "0" ] ; then fail "pretor-psf did not exit nonzero" ; fi

rm -rf "$TMP"
echo "PASS"
exit 0
