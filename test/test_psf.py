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
from pretor import exceptions

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

    def test_grading_revisions(this):
        thePSF = psf.PSF()
        thePSF.load_from_dir(this.test_dir, "submission")

        this.assertFalse(thePSF.is_graded())

        thePSF.create_revision("graded_0", "submission")

        # should fail because graded_0 has no grade attached
        with this.assertRaises(exceptions.StateError):
            thePSF.create_grade_revision()

        this.assertTrue("graded_0" in thePSF.revisions)
        this.assertFalse("graded_1" in thePSF.revisions)

    def test_load_from_dir(this):
        thePSF = psf.PSF()
        thePSF.load_from_dir(this.test_dir, "AAAA")

        this.assertTrue("AAAA" in thePSF.revisions)

        rev = thePSF.revisions["AAAA"]
        this.assertEqual(rev.get_file("foo").get_data().decode("utf-8"), this.test_str)

    def test_validate_metadata(this):

        metadata = {}
        with this.assertRaises(exceptions.StateError):
            psf.validate_metadata(metadata, [], False)

        # should not throw
        psf.validate_metadata(metadata, [], True)

        # validate assignment
        metadata = {"course": "A", "semester": "B", "assignment": "C", "section": "D"}
        with this.assertRaises(exceptions.StateError):
            psf.validate_metadata(metadata, ["invalid"], False)

        # should not throw
        psf.validate_metadata(metadata, [], True)
