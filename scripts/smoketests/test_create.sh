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

pretor-psf --create \
	--source ./submission \
	--destination ./ \
	--course "A" \
	--section "B" \
	--semester "C" \
	--assignment "D" \
	--group "E" \
	--allow_no_toml > "$TMP/err" 2> "$TMP/out"

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
