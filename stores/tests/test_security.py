from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from users.models.user_mod import User
from shared.enums.enums import UserRoleEnum
from stores.models.store_mod import Store


class StoreTenantSecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Vendor A
        self.vendor_a = User.objects.create_user(
            email="vendor_a@test.com",
            password="Password123!",
            role=UserRoleEnum.VENDOR
        )
        self.store_a = Store.objects.create(
            vendor=self.vendor_a,
            name="Vendor A Store",
            address="Street A"
        )

        # Vendor B
        self.vendor_b = User.objects.create_user(
            email="vendor_b@test.com",
            password="Password123!",
            role=UserRoleEnum.VENDOR
        )
        self.store_b = Store.objects.create(
            vendor=self.vendor_b,
            name="Vendor B Store",
            address="Street B"
        )

        # Customer
        self.customer = User.objects.create_user(
            email="customer@test.com",
            password="Password123!",
            role=UserRoleEnum.CUSTOMER
        )

    def test_vendor_a_cannot_see_vendor_b_store_in_list(self):
        self.client.force_authenticate(user=self.vendor_a)
        response = self.client.get('/stores/')
        self.assertEqual(response.status_code, 200)
        store_names = [s['name'] for s in response.data['data']]
        self.assertIn("Vendor A Store", store_names)
        self.assertNotIn("Vendor B Store", store_names)

    def test_vendor_a_cannot_mutate_vendor_b_store(self):
        self.client.force_authenticate(user=self.vendor_a)
        response = self.client.patch(
            f'/stores/{self.store_b.id}/',
            {'name': 'Hacked Store Name'}
        )
        # Should return 404 Not Found (filtered out of queryset)
        self.assertEqual(response.status_code, 404)
        self.store_b.refresh_from_db()
        self.assertEqual(self.store_b.name, "Vendor B Store")

    def test_customer_cannot_create_store(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.post('/stores/', {
            'name': 'Unauthorized Store',
            'address': 'Nowhere'
        })
        self.assertEqual(response.status_code, 403)

    def test_public_discovery_returns_active_stores_only(self):
        inactive_store = Store.objects.create(
            vendor=self.vendor_a,
            name="Closed Store",
            is_active=False
        )
        response = self.client.get('/stores/public/')
        self.assertEqual(response.status_code, 200)
        names = [s['name'] for s in response.data['data']]
        self.assertIn("Vendor A Store", names)
        self.assertIn("Vendor B Store", names)
        self.assertNotIn("Closed Store", names)
