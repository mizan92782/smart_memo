from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from users.models.user_mod import User
from stores.models.store_mod import Store
from products.models.product_mod import Product
from purchases.models.purchase_mod import Supplier, Purchase


class PurchaseSecurityTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Vendor A and Store A
        self.vendor_a = User.objects.create_user(
            email="vendor_a_sec@example.com",
            password="Password123!",
            role="vendor"
        )
        self.store_a = Store.objects.create(
            name="Vendor A Store",
            vendor=self.vendor_a,
            latitude=23.8103,
            longitude=90.4125
        )
        self.product_a = Product.objects.create(
            store=self.store_a,
            name="Store A Product",
            sku="SKU-A-1",
            price=Decimal("100.00")
        )
        self.supplier_a = Supplier.objects.create(
            store=self.store_a,
            name="Store A Supplier"
        )
        self.purchase_a = Purchase.objects.create(
            store=self.store_a,
            supplier=self.supplier_a,
            subtotal=Decimal("200.00"),
            total_cost=Decimal("200.00")
        )

        # Vendor B and Store B
        self.vendor_b = User.objects.create_user(
            email="vendor_b_sec@example.com",
            password="Password123!",
            role="vendor"
        )
        self.store_b = Store.objects.create(
            name="Vendor B Store",
            vendor=self.vendor_b,
            latitude=23.8103,
            longitude=90.4125
        )

        # Customer user
        self.customer = User.objects.create_user(
            email="customer_purchases@example.com",
            password="Password123!",
            role="customer"
        )

    def test_customer_cannot_access_purchase_endpoints(self):
        """Customers must receive 403 Forbidden when trying to access vendor purchase endpoints."""
        self.client.force_authenticate(user=self.customer)

        res_sup = self.client.get("/purchases/suppliers/")
        self.assertEqual(res_sup.status_code, status.HTTP_403_FORBIDDEN)

        res_po = self.client.get("/purchases/orders/")
        self.assertEqual(res_po.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_access_denied(self):
        """Anonymous requests must be rejected with 401 or 403."""
        res_sup = self.client.get("/purchases/suppliers/")
        self.assertIn(res_sup.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

        res_po = self.client.get("/purchases/orders/")
        self.assertIn(res_po.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_vendor_b_cannot_view_or_modify_vendor_a_purchase(self):
        """Vendor B querying Vendor A's purchase ID receives 404 Not Found (IDOR prevention)."""
        self.client.force_authenticate(user=self.vendor_b)

        # Retrieve Vendor A's purchase
        res = self.client.get(f"/purchases/orders/{self.purchase_a.id}/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

        # Attempt to receive Vendor A's purchase
        rec_res = self.client.post(f"/purchases/orders/{self.purchase_a.id}/receive/")
        self.assertEqual(rec_res.status_code, status.HTTP_404_NOT_FOUND)

    def test_vendor_b_cannot_create_purchase_with_vendor_a_store_or_supplier(self):
        """Vendor B attempting to specify Store A or Supplier A must be rejected."""
        self.client.force_authenticate(user=self.vendor_b)

        payload = {
            "store_id": self.store_a.id,
            "supplier_id": self.supplier_a.id,
            "items": [{"product_id": self.product_a.id, "quantity": "10.000", "unit_cost": "50.00"}]
        }
        res = self.client.post("/purchases/orders/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
