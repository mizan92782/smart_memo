"""
products/tests/test_views.py — Tests for Product Views
"""
from django.test import TestCase
from django.urls import reverse
from categories.models.category_mod import Category
from products.models.product_mod import Product


class ProductViewTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Groceries")
        self.product = Product.objects.create(
            name="Apple",
            category=self.category,
            price=120.00,
            stock=10
        )

    def test_product_list_view(self):
        url = reverse('product-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Apple")

    def test_category_products_view(self):
        url = reverse('category_products', kwargs={'pk': self.category.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Apple")

    def test_product_images_management_and_tenant_isolation(self):
        from users.models.user_mod import User
        from shared.enums.enums import UserRoleEnum
        from stores.models.store_mod import Store
        from rest_framework.test import APIClient

        vendor1 = User.objects.create_user(email="v1@shop.com", password="Password123!", role=UserRoleEnum.VENDOR)
        vendor2 = User.objects.create_user(email="v2@shop.com", password="Password123!", role=UserRoleEnum.VENDOR)

        store1 = Store.objects.create(vendor=vendor1, name="V1 Mart", address="Main St")
        store2 = Store.objects.create(vendor=vendor2, name="V2 Mart", address="Second St")

        prod = Product.objects.create(store=store1, name="Organic Honey", price=250.00, stock=20)

        client1 = APIClient()
        client1.force_authenticate(user=vendor1)

        client2 = APIClient()
        client2.force_authenticate(user=vendor2)

        # 1. Vendor 1 adds image 1
        res1 = client1.post(f"/products/{prod.id}/images/", {
            "image_url": "https://example.com/honey1.jpg",
            "is_primary": True,
            "alt_text": "Honey Jar Front"
        })
        self.assertEqual(res1.status_code, 201)
        img1_id = res1.json()["data"]["id"]
        self.assertTrue(res1.json()["data"]["is_primary"])

        # 2. Vendor 1 adds image 2 (also sets is_primary -> unsets image 1)
        res2 = client1.post(f"/products/{prod.id}/images/", {
            "image_url": "https://example.com/honey2.jpg",
            "is_primary": True,
            "alt_text": "Honey Nutrition Label"
        })
        self.assertEqual(res2.status_code, 201)
        img2_id = res2.json()["data"]["id"]

        # 3. Retrieve product images
        res_list = self.client.get(f"/products/{prod.id}/images/")
        self.assertEqual(res_list.status_code, 200)
        images = res_list.json()["data"]
        self.assertEqual(len(images), 2)

        # Check primary image is img2 and img1 is not primary
        from products.models.product_image_mod import ProductImage
        img1 = ProductImage.objects.get(id=img1_id)
        img2 = ProductImage.objects.get(id=img2_id)
        self.assertFalse(img1.is_primary)
        self.assertTrue(img2.is_primary)

        # 4. Check product serialized primary_image_url
        prod.refresh_from_db()
        self.assertEqual(prod.primary_image_url, "https://example.com/honey2.jpg")

        # 5. Tenant isolation: Vendor 2 cannot delete or update Vendor 1's product images
        forbidden_del = client2.delete(f"/products/{prod.id}/images/{img1_id}/")
        self.assertIn(forbidden_del.status_code, [403, 404])

        # 6. Vendor 1 can delete image
        ok_del = client1.delete(f"/products/{prod.id}/images/{img1_id}/")
        self.assertEqual(ok_del.status_code, 200)
        self.assertEqual(prod.images.count(), 1)
