from django.test import TestCase
from rest_framework.test import APIClient
from users.models.user_mod import User
from stores.models.store_mod import Store
from categories.models.category_mod import Category
from products.models.product_mod import Product
from shared.enums.enums import UserRoleEnum


class ProductTenantSecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Vendor A & Store A & Product A
        self.vendor_a = User.objects.create_user(
            email="vendor_prod_a@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.store_a = Store.objects.create(vendor=self.vendor_a, name="Store Prod A")
        self.cat_a = Category.objects.create(store=self.store_a, name="Dairy")
        self.prod_a = Product.objects.create(
            store=self.store_a,
            category=self.cat_a,
            name="Milk",
            price=80.00,
            stock=15
        )

        # Vendor B & Store B & Product B
        self.vendor_b = User.objects.create_user(
            email="vendor_prod_b@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.store_b = Store.objects.create(vendor=self.vendor_b, name="Store Prod B")
        self.prod_b = Product.objects.create(
            store=self.store_b,
            name="Cheese",
            price=250.00,
            stock=10
        )

        # Customer
        self.customer = User.objects.create_user(
            email="cust_prod@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )

    def test_vendor_a_cannot_modify_vendor_b_product(self):
        self.client.force_authenticate(user=self.vendor_a)
        response = self.client.patch(f'/products/api/{self.prod_b.id}/', {
            'price': 10.00
        })
        self.assertEqual(response.status_code, 404)
        self.prod_b.refresh_from_db()
        self.assertEqual(float(self.prod_b.price), 250.00)

    def test_customer_cannot_create_product(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.post('/products/api/', {
            'name': 'Unauthorized Product',
            'price': 50.00,
            'store': self.store_a.id
        })
        self.assertEqual(response.status_code, 403)

    def test_public_catalog_search(self):
        response = self.client.get('/products/api/catalog/?search=Milk')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Milk")
