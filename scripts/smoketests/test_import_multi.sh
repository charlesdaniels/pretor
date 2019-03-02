#!/bin/sh

# test that a PSF file can be created and that the metadata can be read
# from it successfully, then modified using pretor-import, multiple times in
# succession to ensure grade revisions propagate correctly

TMP="$(mktemp -d)"

fail () {
	echo "FAIL"
	echo "test $0 failed: $@"
	echo "------ stderr -----"
	cat "$TMP/err"
	echo "------ stdout -----"
	cat "$TMP/out"
	rm -rf "$TMP"
	exit 1
}

printf "$0... "

cd "$TMP"

mkdir submission
echo "this is a test string!" > submission/file.txt

pretor-psf --create \
	--debug \
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

echo "semester,assignment,section,course,group,override" > "$TMP/data.csv"
echo "C,D,B,A,E,0.1" >> "$TMP/data.csv"

echo '[course]' > "$TMP/coursedef.toml"
echo 'name="A"' >> "$TMP/coursedef.toml"
echo '[D]' >> "$TMP/coursedef.toml"
echo 'name="D"' >> "$TMP/coursedef.toml"
echo 'weight=0.1' >> "$TMP/coursedef.toml"
echo 'foo=10' >> "$TMP/coursedef.toml"

pretor-import \
	--debug \
	--coursepath "$TMP/coursedef.toml" \
	--input "$TMP/data.csv" \
	"$dest" >> "$TMP/out" 2>> "$TMP/err"

if ! pretor-psf --input "$dest" --scorecard | grep 'OVERALL SCORE: 10.00%' > /dev/null ; then
	fail "pretor-import did not update score"
fi

echo "C,D,B,A,E,0.2" >> "$TMP/data.csv"
pretor-import \
	--coursepath "$TMP/coursedef.toml" \
	--input "$TMP/data.csv" \
	"$dest" >> "$TMP/out" 2>> "$TMP/err"

if ! pretor-psf --input "$dest" --scorecard | grep 'OVERALL SCORE: 20.00%' > /dev/null ; then
	fail "pretor-import did not revise score on second revision"
fi

echo "C,D,B,A,E,0.3" >> "$TMP/data.csv"
pretor-import \
	--debug \
	--coursepath "$TMP/coursedef.toml" \
	--input "$TMP/data.csv" \
	"$dest" >> "$TMP/out" 2>> "$TMP/err"

if ! pretor-psf --input "$dest" --scorecard | grep 'OVERALL SCORE: 30.00%' > /dev/null ; then
	fail "pretor-import did not revise score on third revision"
fi

rm -rf "$TMP"
echo "PASS"
exit 0
