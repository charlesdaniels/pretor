#!/bin/sh

# test that a PSF file can be created and that the metadata can be read
# from it successfully

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
echo 'assignment = "D"' >> submission/pretor.toml
echo 'minimum_version = "0.0.1"' >> submission/pretor.toml

pretor-psf --debug --create \
	--source ./submission \
	--destination ./ \
	--group "E" > "$TMP/err" 2> "$TMP/out"

RES=$?

dest="$TMP/C-A-B-E-D.psf"

if [ ! -f "$dest" ] ; then fail "pretor-psf did not generate '$dest'" ; fi

if [ "$RES" -ne "0" ] ; then fail "pretor-psf exited nonzero" ; fi

check_meta () {
	val="$(pretor-psf --input "$dest" --metadata | grep "^$1" | cut -d' ' -f 2- | xargs)"
	if [ "$val" != "$2" ] ; then
		fail "metadata field '$1' not expected value '$2': $val"
	fi
}

check_meta "semester" "C"
check_meta "assignment" "D"
check_meta "section" "B"
check_meta "course" "A"
check_meta "group" "E"

rm -rf "$TMP"
echo "PASS"
exit 0
