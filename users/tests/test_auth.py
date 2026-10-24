from django.test import TestCase
from rest_framework.test import APIClient
from users.models.user_mod import User
from users.repositories.user_repository import UserRepository
from shared.enums.enums import UserRoleEnum


class UserAuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_customer_user(self):
        response = self.client.post('/users/register/', {
            'email': 'customer1@example.com',
            'password': 'StrongPassword123!',
            'full_name': 'Alice Wonderland',
            'role': UserRoleEnum.CUSTOMER
        })
        self.assertEqual(response.status_code, 201)
        user = UserRepository.get_by_email('customer1@example.com')
        self.assertIsNotNone(user)
        self.assertEqual(user.role, UserRoleEnum.CUSTOMER)
        self.assertEqual(user.profile.full_name, 'Alice Wonderland')

    def test_duplicate_email_registration_rejected(self):
        UserRepository.create_user('duplicate@example.com', 'Pass12345!')
        response = self.client.post('/users/register/', {
            'email': 'duplicate@example.com',
            'password': 'AnotherPassword123!'
        })
        self.assertEqual(response.status_code, 400)

    def test_authenticated_user_can_access_me(self):
        user = UserRepository.create_user('me@example.com', 'Pass12345!', role=UserRoleEnum.VENDOR)
        self.client.force_authenticate(user=user)
        response = self.client.get('/users/me/')
        self.assertEqual(response.status_code, 200)
        user_data = response.data['data'].get('user', response.data['data'])
        self.assertEqual(user_data['email'], 'me@example.com')
        self.assertEqual(user_data['role'], UserRoleEnum.VENDOR)

    def test_unauthenticated_cannot_access_me(self):
        response = self.client.get('/users/me/')
        self.assertIn(response.status_code, [401, 403])
