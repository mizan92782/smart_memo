from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from users.models.user_mod import User
from stores.models.store_mod import Store


class ReportSecurityTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Vendor A and Store A
        self.vendor_a = User.objects.create_user(
            email="vendor_a_rep@example.com",
            password="Password123!",
            role="vendor"
        )
        self.store_a = Store.objects.create(
            name="Store A Analytics",
            vendor=self.vendor_a,
            latitude=23.8103,
            longitude=90.4125
        )

        # Vendor B and Store B
        self.vendor_b = User.objects.create_user(
            email="vendor_b_rep@example.com",
            password="Password123!",
            role="vendor"
        )
        self.store_b = Store.objects.create(
            name="Store B Analytics",
            vendor=self.vendor_b,
            latitude=23.8103,
            longitude=90.4125
        )

        # Customer user
        self.customer = User.objects.create_user(
            email="customer_rep@example.com",
            password="Password123!",
            role="customer"
        )

    def test_customer_cannot_access_reports(self):
        """Customers must receive 403 Forbidden when requesting vendor reports."""
        self.client.force_authenticate(user=self.customer)

        res = self.client.get(f"/reports/sales/?store_id={self.store_a.id}")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        res_inv = self.client.get(f"/reports/inventory/?store_id={self.store_a.id}")
        self.assertEqual(res_inv.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_access_denied(self):
        """Anonymous requests must be rejected with 401 or 403."""
        res = self.client.get(f"/reports/sales/?store_id={self.store_a.id}")
        self.assertIn(res.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_vendor_b_cannot_view_vendor_a_reports(self):
        """Vendor B attempting to request Store A's reports receives 403 Forbidden."""
        self.client.force_authenticate(user=self.vendor_b)

        # Sales
        res_sales = self.client.get(f"/reports/sales/?store_id={self.store_a.id}")
        self.assertEqual(res_sales.status_code, status.HTTP_403_FORBIDDEN)

        # Inventory
        res_inv = self.client.get(f"/reports/inventory/?store_id={self.store_a.id}")
        self.assertEqual(res_inv.status_code, status.HTTP_403_FORBIDDEN)

        # Purchases
        res_po = self.client.get(f"/reports/purchases/?store_id={self.store_a.id}")
        self.assertEqual(res_po.status_code, status.HTTP_403_FORBIDDEN)
