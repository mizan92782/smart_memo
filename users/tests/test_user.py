"""
users/tests/test_user.py — Tests for User Model and Repository
"""
from django.test import TestCase
from users.models.user_mod import User
from users.repositories.user_repository import UserRepository


class UserModelTests(TestCase):
    def test_create_user(self):
        user = UserRepository.create_user(email="test@example.com", password="password123")
        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.check_password("password123"))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
