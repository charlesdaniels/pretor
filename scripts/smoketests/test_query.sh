#!/bin/sh

# test creating several PSFs then querying them

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
	--course "A1" \
	--section "B1" \
	--semester "C1" \
	--assignment "D1" \
	--group "E1" \
	--allow_no_toml > "$TMP/err" 2> "$TMP/out"

pretor-psf --create \
	--source ./submission \
	--destination ./ \
	--course "A2" \
	--section "B2" \
	--semester "C2" \
	--assignment "D2" \
	--group "E2" \
	--allow_no_toml > "$TMP/err" 2> "$TMP/out"

pretor-query --query 'SELECT course FROM psf' > $TMP/result

if ! grep 'A1' < $TMP/result > /dev/null 2>&1 ; then
	fail "missing result"
fi

if ! grep 'A2' < $TMP/result > /dev/null 2>&1 ; then
	fail "missing result"
fi

pretor-query --query 'SELECT course FROM psf WHERE section == "B2"' > $TMP/result

if grep 'A1' < $TMP/result > /dev/null 2>&1 ; then
	fail "extra result"
fi

if ! grep 'A2' < $TMP/result > /dev/null 2>&1 ; then
	fail "missing result"
fi

if [ -e "memory" ] ; then fail "database written to disk, not in memory" ; fi

if [ -e ":memory:" ] ; then fail "database written to disk, not in memory" ; fi

rm -rf "$TMP"
echo "PASS"
exit 0
