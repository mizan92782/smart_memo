from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework import status
from shared.enums.enums import UserRoleEnum

User = get_user_model()


class ThrottlingTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='throttle_test@example.com',
            password='TestPassword123!',
            role=UserRoleEnum.CUSTOMER
        )

    def tearDown(self):
        cache.clear()

    def test_login_rate_limiting_triggers_429(self):
        """Verify anonymous login attempt rate limit (5 requests per minute)."""
        for i in range(5):
            resp = self.client.post("/users/login/", {
                "email": "wrong@example.com",
                "password": "WrongPassword123!"
            })
            self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

        # 6th attempt should be throttled
        throttled_resp = self.client.post("/users/login/", {
            "email": "wrong@example.com",
            "password": "WrongPassword123!"
        })
        self.assertEqual(throttled_resp.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertFalse(throttled_resp.data["success"])
        self.assertIn("throttled", throttled_resp.data["message"].lower())
        self.assertIsNotNone(throttled_resp.data.get("data"))
        self.assertIn("available_in_seconds", throttled_resp.data["data"])
        self.assertGreater(throttled_resp.data["data"]["available_in_seconds"], 0)

    def test_signup_rate_limiting_triggers_429(self):
        """Verify signup rate limit (5 requests per minute)."""
        for i in range(5):
            resp = self.client.post("/users/register/", {
                "email": f"signup_{i}@example.com",
                "password": "Password123!",
                "full_name": f"User {i}"
            })
            self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        # 6th attempt should be throttled
        throttled_resp = self.client.post("/users/register/", {
            "email": "signup_overflow@example.com",
            "password": "Password123!",
            "full_name": "Overflow User"
        })
        self.assertEqual(throttled_resp.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertFalse(throttled_resp.data["success"])
        self.assertIn("throttled", throttled_resp.data["message"].lower())

    def test_nearby_discovery_rate_limiting_triggers_429(self):
        """Verify geospatial nearby discovery rate limit (30 requests per minute)."""
        for i in range(30):
            resp = self.client.get("/stores/nearby/")
            self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # 31st attempt should be throttled
        throttled_resp = self.client.get("/stores/nearby/")
        self.assertEqual(throttled_resp.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertFalse(throttled_resp.data["success"])
        self.assertIn("throttled", throttled_resp.data["message"].lower())
