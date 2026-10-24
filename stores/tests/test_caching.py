from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework import status
from shared.caching.cache_service import CacheService
from stores.models.store_mod import Store
from categories.models.category_mod import Category
from products.models.product_mod import Product

User = get_user_model()


class CachingTenantIsolationTests(TestCase):
    """
    Test tenant isolation, key generation, and O(1) versioned invalidation
    as defined in .agents/skills/caching/SKILL.md.
    """

    def setUp(self):
        cache.clear()
        self.client = APIClient()

        # Vendor 1 and Store 1
        self.vendor1 = User.objects.create_user(
            email="vendor1@example.com",
            password="VendorPass123!",
            role="vendor"
        )
        self.store1 = Store.objects.create(
            vendor=self.vendor1,
            name="Alpha Supermarket",
            latitude=23.8103,
            longitude=90.4125,
            is_active=True
        )

        # Vendor 2 and Store 2
        self.vendor2 = User.objects.create_user(
            email="vendor2@example.com",
            password="VendorPass123!",
            role="vendor"
        )
        self.store2 = Store.objects.create(
            vendor=self.vendor2,
            name="Beta Grocery",
            latitude=23.7925,
            longitude=90.4078,
            is_active=True
        )

    def tearDown(self):
        cache.clear()

    def test_tenant_keys_are_isolated(self):
        """Keys for different stores must never collide."""
        key1 = CacheService.build_cache_key(self.store1.id, "catalog", "search")
        key2 = CacheService.build_cache_key(self.store2.id, "catalog", "search")
        self.assertNotEqual(key1, key2)
        self.assertIn(f"store:{self.store1.id}", key1)
        self.assertIn(f"store:{self.store2.id}", key2)

    def test_version_bump_invalidates_keys_o1(self):
        """Bumping tenant version must change generated cache keys in O(1) time."""
        initial_key = CacheService.build_cache_key(self.store1.id, "catalog", "category_list")
        CacheService.set(initial_key, ["Dairy", "Bakery"])

        self.assertEqual(CacheService.get(initial_key), ["Dairy", "Bakery"])

        # Invalidate catalog for Store 1
        new_version = CacheService.invalidate_catalog(self.store1.id)
        self.assertGreater(new_version, 1)

        new_key = CacheService.build_cache_key(self.store1.id, "catalog", "category_list")
        self.assertNotEqual(initial_key, new_key)
        # New key has no data, effectively invalidating old cache without KEY scans
        self.assertIsNone(CacheService.get(new_key))

        # Store 2 version must remain unaffected
        store2_ver = CacheService.get_tenant_version(self.store2.id, "catalog")
        self.assertEqual(store2_ver, 1)

    def test_store_public_detail_caching_and_invalidation(self):
        """Public detail is cached on GET and invalidated on profile update."""
        url = f"/stores/{self.store1.id}/public-detail/"
        res1 = self.client.get(url)
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertEqual(res1.data['data']['store']['name'], "Alpha Supermarket")

        # Verify key exists in cache
        cache_key = CacheService.build_cache_key(self.store1.id, "store", "public_detail")
        cached = CacheService.get(cache_key)
        self.assertIsNotNone(cached)
        self.assertEqual(cached['name'], "Alpha Supermarket")

        # Vendor 1 updates store name
        self.client.force_authenticate(user=self.vendor1)
        update_res = self.client.patch(
            f"/stores/{self.store1.id}/",
            {"name": "Alpha Supermarket Premium"}
        )
        self.assertEqual(update_res.status_code, status.HTTP_200_OK)

        # Cache key should now resolve to new version, yielding updated DB state
        self.client.force_authenticate(user=None)
        res2 = self.client.get(url)
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(res2.data['data']['store']['name'], "Alpha Supermarket Premium")

    def test_catalog_invalidation_on_product_create(self):
        """Creating a product invalidates catalog cache for that store."""
        category = Category.objects.create(name="Beverages", store=self.store1)

        # Populate catalog cache
        catalog_url = f"/products/api/catalog/?store_id={self.store1.id}"
        res1 = self.client.get(catalog_url)
        self.assertEqual(res1.status_code, status.HTTP_200_OK)

        initial_ver = CacheService.get_tenant_version(self.store1.id, "catalog")

        # Create new product
        self.client.force_authenticate(user=self.vendor1)
        create_res = self.client.post("/products/api/", {
            "name": "Sparkling Water",
            "price": "2.50",
            "store": self.store1.id,
            "category": category.id
        })
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED)

        # Version must have incremented
        new_ver = CacheService.get_tenant_version(self.store1.id, "catalog")
        self.assertGreater(new_ver, initial_ver)
