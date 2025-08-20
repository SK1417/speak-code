import unittest
from ..utils import greet, Calculator

class TestUtils(unittest.TestCase):
    def test_greet(self):
        self.assertEqual(greet("World"), "Hello, World!")

    def test_calculator_add(self):
        calc = Calculator()
        self.assertEqual(calc.add(1, 2), 3)
