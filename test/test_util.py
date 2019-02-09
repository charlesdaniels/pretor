import unittest
import sys
import tempfile
import shutil
import os
import pathlib
import contextlib
import io

from pretor import util



class TestUtil(unittest.TestCase):

    def test_compare_versions(this):

        this.assertTrue(util.compare_versions("0.0.1", "0.0.1"))
        this.assertTrue(util.compare_versions("0.0.2", "0.0.1"))
        this.assertTrue(util.compare_versions("1.0.0", "1.0.0"))
        this.assertFalse(util.compare_versions("1.0.0", "1.0.1"))
        this.assertTrue(util.compare_versions("2.0.0", "1.0.1"))

