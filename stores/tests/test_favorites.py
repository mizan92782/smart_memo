from django.test import TestCase
from rest_framework.test import APIClient
from users.models.user_mod import User
from stores.models.store_mod import Store
from stores.models.favorite_mod import FavoriteStore
from shared.enums.enums import UserRoleEnum


class FavoriteStoreTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Vendor & Stores
        self.vendor = User.objects.create_user(
            email="fav_vendor@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.store1 = Store.objects.create(vendor=self.vendor, name="Favorite Store 1")
        self.store2 = Store.objects.create(vendor=self.vendor, name="Favorite Store 2")

        # Customer A
        self.customer_a = User.objects.create_user(
            email="customer_a@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )

        # Customer B
        self.customer_b = User.objects.create_user(
            email="customer_b@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )

    def test_customer_can_favorite_store_and_idempotency(self):
        self.client.force_authenticate(user=self.customer_a)

        # 1. First favorite call
        res = self.client.post(f'/stores/{self.store1.id}/favorite/')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(FavoriteStore.objects.filter(customer=self.customer_a, store=self.store1).count(), 1)

        # 2. Second favorite call (idempotent: does not duplicate or raise 500)
        res2 = self.client.post(f'/stores/{self.store1.id}/favorite/')
        self.assertEqual(res2.status_code, 201)
        self.assertEqual(FavoriteStore.objects.filter(customer=self.customer_a, store=self.store1).count(), 1)

    def test_customer_can_unfavorite_store(self):
        self.client.force_authenticate(user=self.customer_a)
        self.client.post(f'/stores/{self.store1.id}/favorite/')
        self.assertEqual(FavoriteStore.objects.filter(customer=self.customer_a, store=self.store1).count(), 1)

        # DELETE unfavorite
        res = self.client.delete(f'/stores/{self.store1.id}/favorite/')
        self.assertEqual(res.status_code, 200)
        self.assertFalse(FavoriteStore.objects.filter(customer=self.customer_a, store=self.store1).exists())

    def test_customer_isolation_on_favorites_listing(self):
        # Customer A favorites Store 1
        self.client.force_authenticate(user=self.customer_a)
        self.client.post(f'/stores/{self.store1.id}/favorite/')

        # Customer B favorites Store 2
        self.client.force_authenticate(user=self.customer_b)
        self.client.post(f'/stores/{self.store2.id}/favorite/')

        # Customer B gets favorites -> only Store 2
        res_b = self.client.get('/stores/favorites/')
        self.assertEqual(res_b.status_code, 200)
        fav_store_ids = [item['store']['id'] for item in res_b.data['data']]
        self.assertIn(self.store2.id, fav_store_ids)
        self.assertNotIn(self.store1.id, fav_store_ids)

        # Customer A gets favorites -> only Store 1
        self.client.force_authenticate(user=self.customer_a)
        res_a = self.client.get('/stores/favorites/')
        self.assertEqual(res_a.status_code, 200)
        fav_store_ids_a = [item['store']['id'] for item in res_a.data['data']]
        self.assertIn(self.store1.id, fav_store_ids_a)
        self.assertNotIn(self.store2.id, fav_store_ids_a)

    def test_unauthenticated_user_cannot_access_favorites(self):
        # Listing requires auth
        res_list = self.client.get('/stores/favorites/')
        self.assertIn(res_list.status_code, [401, 403])

        # Favoriting requires auth
        res_post = self.client.post(f'/stores/{self.store1.id}/favorite/')
        self.assertIn(res_post.status_code, [401, 403])

