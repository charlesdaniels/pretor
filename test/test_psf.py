import unittest
import sys
import tempfile
import shutil
import os
import pathlib
import contextlib
import io
import logging

from pretor import psf

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

    def test_load_from_dir(this):
        thePSF = psf.PSF()
        thePSF.load_from_dir(this.test_dir, "AAAA")

        this.assertTrue("AAAA" in thePSF.revisions)

        rev = thePSF.revisions["AAAA"]
        this.assertEqual(rev.get_file("foo").get_data().decode("utf-8"), this.test_str)
