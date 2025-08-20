import unittest
from ..services.api import api_call

class TestServices(unittest.TestCase):
    def test_api_call(self):
        # This is a simple test, in a real scenario we would mock the dependencies
        self.assertIn("Hello", api_call())
