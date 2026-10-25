from django.test import TestCase
from rest_framework.test import APIClient
from users.models.user_mod import User
from stores.models.store_mod import Store
from categories.models.category_mod import Category
from shared.enums.enums import UserRoleEnum


class CategoryTenantSecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Vendor A & Store A
        self.vendor_a = User.objects.create_user(
            email="vendor_cat_a@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.store_a = Store.objects.create(vendor=self.vendor_a, name="Store Cat A")
        self.cat_a = Category.objects.create(store=self.store_a, name="Beverages")

        # Vendor B & Store B
        self.vendor_b = User.objects.create_user(
            email="vendor_cat_b@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.store_b = Store.objects.create(vendor=self.vendor_b, name="Store Cat B")
        self.cat_b = Category.objects.create(store=self.store_b, name="Snacks")

        # Customer
        self.customer = User.objects.create_user(
            email="cust_cat@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )

    def test_vendor_a_cannot_delete_vendor_b_category(self):
        self.client.force_authenticate(user=self.vendor_a)
        response = self.client.delete(f'/categories/api/{self.cat_b.id}/')
        self.assertIn(response.status_code, [403, 404])
        self.cat_b.refresh_from_db()
        self.assertFalse(self.cat_b.is_deleted)

    def test_vendor_cannot_create_category_for_another_store(self):
        self.client.force_authenticate(user=self.vendor_a)
        response = self.client.post('/categories/api/', {
            'name': 'Hacked Cat',
            'store_id': self.store_b.id
        })
        self.assertEqual(response.status_code, 403)

    def test_customer_cannot_create_category(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.post('/categories/api/', {
            'name': 'Customer Cat',
            'store_id': self.store_a.id
        })
        self.assertEqual(response.status_code, 403)

    def test_vendor_cannot_assign_another_store_category_to_product(self):
        """Vendor A cannot assign Vendor B's category to a product in Store A."""
        self.client.force_authenticate(user=self.vendor_a)
        response = self.client.post('/products/', {
            'store': self.store_a.id,
            'name': 'Cross Tenant Product',
            'price': '10.00',
            'stock': 10,
            'category': self.cat_b.id,
        })
        self.assertEqual(response.status_code, 400)

