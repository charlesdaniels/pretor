#!/bin/sh

# test that a PSF file with a pretor.toml that specifies a list of allowed
# assignment, but where the --assignment is not valid.

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
echo 'course = "A"' >> submission/pretor.toml
echo 'section = "B"' >> submission/pretor.toml
echo 'semester = "C"' >> submission/pretor.toml
echo 'minimum_version = "0.0.1"' >> submission/pretor.toml
echo 'valid_assignment_names = ["foo", "bar"]' >> submission/pretor.toml

pretor-psf --create \
	--source ./submission \
	--destination ./ \
	--assignment "baz" \
	--group "E" > "$TMP/err" 2> "$TMP/out"

RES=$?

dest="$TMP/C-A-B-E-D.psf"

if [ -f "$dest" ] ; then fail "pretor-psf generated '$dest and should not have'" ; fi

if [ "$RES" -eq "0" ] ; then fail "pretor-psf exited 0 and should have" ; fi

rm -rf "$TMP"
echo "PASS"
exit 0
