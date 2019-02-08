import unittest
import sys
import tempfile
import shutil
import os
import pathlib
import contextlib
import io

from pretor import psf

# https://stackoverflow.com/a/17981937
@contextlib.contextmanager
def captured_output():
    new_out, new_err = io.StringIO(), io.StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err

class TestPSF(unittest.TestCase):

    def setUp(this):
        this.test_dir = tempfile.mkdtemp()
        this.test_out_dir = tempfile.mkdtemp()
        this.test_file = os.path.join(this.test_dir, "foo")
        this.test_str = "this is a test string!"
        with open(this.test_file, 'w') as f:
            f.write(this.test_str)

    def tearDown(this):
        shutil.rmtree(this.test_dir)
        shutil.rmtree(this.test_out_dir)
        this.test_dir = None
        this.test_file = None
        this.test_str = None

    def test_psf_cli_create(this):
        argv = [
            "--create",
            "--source", this.test_dir,
            "--destination", this.test_out_dir,
            "--course", "A",
            "--section", "B",
            "--semester", "C",
            "--assignment", "D",
            "--group", "E",
            "--allow_no_toml"
        ]

        try:
            with captured_output() as (out, err):
                psf.psf_cli(argv)
        except SystemExit:
            pass

        outpath = pathlib.Path(this.test_out_dir) / "C-A-B-E-D.psf"
        this.assertTrue(outpath.exists())

        with captured_output() as (out, err):
            psf.psf_cli([
                "--input", str(outpath),
                "--metadata"
            ])

            output = out.getvalue().strip()

        results = {}
        for line in output.split("\n"):
            key = line.split()[0]
            val = ' '.join(line.split()[1:])
            results[key] = val

        this.assertEqual(results["semester"]   , "C")
        this.assertEqual(results["assignment"] , "D")
        this.assertEqual(results["section"]    , "B")
        this.assertEqual(results["group"]      , "E")
        this.assertEqual(results["course"]     , "A")
