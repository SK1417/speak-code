import unittest
from ..models import User

class TestModels(unittest.TestCase):
    def test_user_creation(self):
        user = User("Test", "test@test.com")
        self.assertEqual(user.name, "Test")
        self.assertEqual(user.email, "test@test.com")
