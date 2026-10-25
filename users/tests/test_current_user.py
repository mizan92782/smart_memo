from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from shared.enums.enums import UserRoleEnum

User = get_user_model()


class CurrentUserEndpointTests(APITestCase):
    """
    GET /users/me/ is how the SPA validates a persisted token on boot instead of
    trusting whatever identity it cached in localStorage.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email="me_probe@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )

    def test_returns_identity_for_valid_token(self):
        login = self.client.post(
            '/users/login/',
            {'email': 'me_probe@test.com', 'password': 'Password123!'},
            format='json'
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        token = login.data['data']['token']

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        res = self.client.get('/users/me/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        user = res.data['data']['user']
        self.assertEqual(user['email'], 'me_probe@test.com')
        # Role must be present — the SPA routes on it, and /users/profile/ omits it.
        self.assertEqual(user['role'], UserRoleEnum.VENDOR)
        self.assertEqual(user['id'], self.user.id)
        self.assertIn('profile', user)

    def test_rejects_anonymous_request(self):
        res = self.client.get('/users/me/')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_rejects_revoked_token(self):
        login = self.client.post(
            '/users/login/',
            {'email': 'me_probe@test.com', 'password': 'Password123!'},
            format='json'
        )
        token = login.data['data']['token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        self.client.post('/users/logout/')

        res = self.client.get('/users/me/')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
