#!/bin/sh

# test that pretor-import fails when the schema is ambiguous

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
RES1=$?

dest1="$TMP/C-A-B-E-D.psf"

if [ ! -f "$dest1" ] ; then fail "pretor-psf did not generate '$dest2'" ; fi

if [ "$RES1" -ne "0" ] ; then fail "pretor-psf exited nonzero" ; fi

pretor-psf --create \
	--source ./submission \
	--destination ./ \
	--course "A" \
	--section "B" \
	--semester "C" \
	--assignment "D" \
	--group "F" \
	--allow_no_toml > "$TMP/err" 2> "$TMP/out"
RES2=$?

dest2="$TMP/C-A-B-F-D.psf"

if [ ! -f "$dest2" ] ; then fail "pretor-psf did not generate '$dest2'" ; fi

if [ "$RES2" -ne "0" ] ; then fail "pretor-psf exited nonzero" ; fi



echo "semester,assignment,section,course,override" > "$TMP/data.csv"
echo "C,D,B,A,0.1" >> "$TMP/data.csv"

echo '[course]' > "$TMP/coursedef.toml"
echo 'name="A"' >> "$TMP/coursedef.toml"
echo '[D]' >> "$TMP/coursedef.toml"
echo 'name="D"' >> "$TMP/coursedef.toml"
echo 'weight=0.1' >> "$TMP/coursedef.toml"
echo 'foo=10' >> "$TMP/coursedef.toml"

pretor-import \
	--coursepath "$TMP/coursedef.toml" \
	--input "$TMP/data.csv" \
	"$dest1" "$dest2" > "$TMP/out" 2> "$TMP/err"

RES3=$?

if [ $RES3 -eq 0 ] ; then
	fail "pretor-import should have exited with an error and did not"
fi

if pretor-psf --input "$dest1" --scorecard > /dev/null 2>&1 ; then
	fail "pretor-import updated score for $dest1 and should not have"
fi

if pretor-psf --input "$dest2" --scorecard > /dev/null 2>&1 ; then
	fail "pretor-import updated score for $dest2 and should not have"
fi

rm -rf "$TMP"
echo "PASS"
exit 0
