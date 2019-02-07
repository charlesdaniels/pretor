import unittest

from pretor import psf

class TestPSF(unittest.TestCase):
 
    def setUp(self):
        pass
 
    def test_numbers_3_4(self):
        self.assertEqual( 3 * 4, 12)
 
    def test_strings_a_3(self):
        self.assertEqual( 3 * 'a', 'aaa')
