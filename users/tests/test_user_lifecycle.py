from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from users.models.user_mod import User
from users.repositories.user_repository import UserRepository
from shared.enums.enums import UserRoleEnum


class UserLifecycleTests(TestCase):
    """
    Automated test suite verifying the complete Authentication Lifecycle &
    User Profile Management per .agents/skills/authentication-authorization/SKILL.md.
    """

    def setUp(self):
        self.client = APIClient()
        self.raw_password = 'SecurePassword123!'
        self.user = UserRepository.create_user(
            email='testuser@example.com',
            password=self.raw_password,
            role=UserRoleEnum.CUSTOMER
        )
        self.user.refresh_from_db()
        self.user.profile.full_name = 'Original Name'
        self.user.profile.phone_number = '+1000000000'
        self.user.profile.address = '100 Default Way'
        self.user.profile.save()


    def test_login_successful_with_valid_credentials(self):
        """POST /users/login/ returns 200, user role, and auth token."""
        response = self.client.post('/users/login/', {
            'email': 'testuser@example.com',
            'password': self.raw_password,
        })
        self.assertEqual(response.status_code, 200)
        data = response.data['data']
        self.assertIn('token', data)
        self.assertEqual(data['user']['email'], 'testuser@example.com')
        self.assertEqual(data['user']['role'], UserRoleEnum.CUSTOMER)
        self.assertTrue(Token.objects.filter(key=data['token']).exists())

    def test_login_fails_with_invalid_password(self):
        """POST /users/login/ returns 400 when password is incorrect."""
        response = self.client.post('/users/login/', {
            'email': 'testuser@example.com',
            'password': 'WrongPassword123!',
        })
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data.get('success', True))

    def test_login_fails_with_nonexistent_email(self):
        """POST /users/login/ returns 400 when email does not exist."""
        response = self.client.post('/users/login/', {
            'email': 'doesnotexist@example.com',
            'password': self.raw_password,
        })
        self.assertEqual(response.status_code, 400)

    def test_login_blocked_for_inactive_user(self):
        """POST /users/login/ returns 403 when user is disabled."""
        self.user.is_active = False
        self.user.save()

        response = self.client.post('/users/login/', {
            'email': 'testuser@example.com',
            'password': self.raw_password,
        })
        self.assertEqual(response.status_code, 403)

    def test_token_authentication_allows_access_to_protected_endpoint(self):
        """Authorization: Token <key> enables access to authenticated endpoints."""
        token = UserRepository.get_or_create_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = self.client.get('/users/me/')
        self.assertEqual(response.status_code, 200)
        user_data = response.data['data'].get('user', response.data['data'])
        self.assertEqual(user_data['email'], 'testuser@example.com')

    def test_logout_invalidates_token(self):
        """POST /users/logout/ revokes auth token; subsequent calls fail."""
        token = UserRepository.get_or_create_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        logout_resp = self.client.post('/users/logout/')
        self.assertEqual(logout_resp.status_code, 200)

        # Token should be removed from database
        self.assertFalse(Token.objects.filter(key=token.key).exists())

        # Subsequent call with revoked token must fail with 401
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        followup_resp = self.client.get('/users/me/')
        self.assertEqual(followup_resp.status_code, 401)

    def test_change_password_success_and_rotates_token(self):
        """POST /users/change-password/ updates hash and rotates token."""
        token = UserRepository.get_or_create_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        new_password = 'BrandNewPassword999!'

        response = self.client.post('/users/change-password/', {
            'old_password': self.raw_password,
            'new_password': new_password,
        })
        self.assertEqual(response.status_code, 200)
        new_token_key = response.data['data']['token']

        # Old token is invalidated
        self.assertFalse(Token.objects.filter(key=token.key).exists())
        # New token is active
        self.assertTrue(Token.objects.filter(key=new_token_key).exists())

        # Clear credentials header so login endpoint tests unauthenticated credential flow
        self.client.credentials()

        # Old password cannot login, new password can login
        login_old = self.client.post('/users/login/', {
            'email': 'testuser@example.com',
            'password': self.raw_password,
        })
        self.assertEqual(login_old.status_code, 400)

        login_new = self.client.post('/users/login/', {
            'email': 'testuser@example.com',
            'password': new_password,
        })
        self.assertEqual(login_new.status_code, 200)


    def test_change_password_fails_with_wrong_old_password(self):
        """POST /users/change-password/ rejected when old password doesn't match."""
        token = UserRepository.get_or_create_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = self.client.post('/users/change-password/', {
            'old_password': 'IncorrectOldPassword123!',
            'new_password': 'BrandNewPassword999!',
        })
        self.assertEqual(response.status_code, 400)

    def test_change_password_fails_if_new_password_too_short(self):
        """POST /users/change-password/ rejected if new password has < 8 chars."""
        token = UserRepository.get_or_create_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = self.client.post('/users/change-password/', {
            'old_password': self.raw_password,
            'new_password': 'short',
        })
        self.assertEqual(response.status_code, 400)

    def test_get_profile_returns_own_profile(self):
        """GET /users/profile/ returns profile for authenticated user."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/users/profile/')
        self.assertEqual(response.status_code, 200)
        profile_data = response.data['data'].get('profile', response.data['data'])
        self.assertEqual(profile_data['full_name'], 'Original Name')
        self.assertEqual(profile_data['phone_number'], '+1000000000')
        self.assertEqual(profile_data['address'], '100 Default Way')

    def test_patch_profile_updates_fields_safely(self):
        """PATCH /users/profile/ safely updates mutable profile fields."""
        self.client.force_authenticate(user=self.user)
        response = self.client.patch('/users/profile/', {
            'full_name': 'Updated Full Name',
            'phone_number': '+8801700000000',
            'address': '200 Updated Boulevard',
        })
        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.full_name, 'Updated Full Name')
        self.assertEqual(self.user.profile.phone_number, '+8801700000000')
        self.assertEqual(self.user.profile.address, '200 Updated Boulevard')

    def test_profile_isolation_cannot_affect_other_user(self):
        """Updating user A's profile leaves user B's profile unaffected."""
        other_user = UserRepository.create_user(
            email='other@example.com',
            password='OtherPassword123!',
            role=UserRoleEnum.VENDOR
        )
        other_user.refresh_from_db()
        other_user.profile.full_name = 'Other User Name'
        other_user.profile.phone_number = '+9999999999'
        other_user.profile.save()


        # Authenticate as self.user and update
        self.client.force_authenticate(user=self.user)
        self.client.patch('/users/profile/', {
            'full_name': 'Tampered Name',
        })

        other_user.profile.refresh_from_db()
        self.assertEqual(other_user.profile.full_name, 'Other User Name')
        self.assertEqual(other_user.profile.phone_number, '+9999999999')

    def test_unauthenticated_requests_to_protected_endpoints_fail(self):
        """Unauthenticated requests to protected endpoints return 401 or 403."""
        endpoints = [
            ('post', '/users/logout/'),
            ('post', '/users/change-password/'),
            ('get', '/users/profile/'),
            ('patch', '/users/profile/'),
        ]
        for method, url in endpoints:
            req_func = getattr(self.client, method)
            response = req_func(url)
            self.assertIn(
                response.status_code,
                [401, 403],
                f"Expected 401/403 for unauthenticated {method.upper()} {url}, got {response.status_code}"
            )
