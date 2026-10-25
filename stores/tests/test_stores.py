from django.test import TestCase
from users.models.user_mod import User
from shared.enums.enums import UserRoleEnum
from stores.models.store_mod import Store
from stores.repositories.store_repository import StoreRepository
from stores.services.store_service import StoreService


class StoreModelAndServiceTests(TestCase):
    def setUp(self):
        self.vendor = User.objects.create_user(
            email="vendor1@test.com",
            password="Password123!",
            role=UserRoleEnum.VENDOR
        )

    def test_create_store_generates_slug(self):
        store = StoreService.register_store(
            vendor=self.vendor,
            name="Fresh Corner Mart",
            address="123 High St"
        )
        self.assertEqual(store.name, "Fresh Corner Mart")
        self.assertEqual(store.slug, "fresh-corner-mart")
        self.assertEqual(store.vendor, self.vendor)
        self.assertTrue(store.is_active)

    def test_duplicate_name_generates_unique_slug(self):
        store1 = StoreService.register_store(
            vendor=self.vendor,
            name="Quick Stop"
        )
        store2 = StoreService.register_store(
            vendor=self.vendor,
            name="Quick Stop"
        )
        self.assertEqual(store1.slug, "quick-stop")
        self.assertEqual(store2.slug, "quick-stop-1")

    def test_update_store_profile(self):
        store = StoreService.register_store(vendor=self.vendor, name="Old Name")
        updated = StoreService.update_store_profile(store, name="New Name", delivery_fee=25.00)
        self.assertEqual(updated.name, "New Name")
        self.assertEqual(float(updated.delivery_fee), 25.00)

    def test_soft_delete_store(self):
        store = StoreService.register_store(vendor=self.vendor, name="Deletable Store")
        StoreRepository.delete_store(store)
        self.assertTrue(store.is_deleted)
        self.assertIsNone(StoreRepository.get_by_id(store.id))

    def test_store_branding_and_public_url_slug(self):
        store = StoreService.register_store(
            vendor=self.vendor,
            name="Apex Supermarket",
            owner_name="Alice Apex",
            logo_url="https://images.unsplash.com/logo.jpg",
            cover_photo_url="https://images.unsplash.com/cover.jpg",
            phone_number="1234567890",
            secondary_phone="0987654321",
            whatsapp_number="1234567890",
            shop_type="hybrid",
            website_url="https://apexsuper.com"
        )
        self.assertEqual(store.owner_name, "Alice Apex")
        self.assertEqual(store.logo_url, "https://images.unsplash.com/logo.jpg")
        self.assertEqual(store.cover_photo_url, "https://images.unsplash.com/cover.jpg")
        self.assertEqual(store.secondary_phone, "0987654321")
        self.assertEqual(store.whatsapp_number, "1234567890")
        self.assertEqual(store.shop_type, "hybrid")
        self.assertEqual(store.public_url_slug, "apex-supermarket.com")

    def test_public_storefront_endpoint(self):
        store = StoreService.register_store(
            vendor=self.vendor,
            name="Green Valley Organics",
            owner_name="George Green",
            shop_type="online_and_physical"
        )
        # Test resolving by vanity domain slug
        response = self.client.get(f"/stores/public-store/{store.public_url_slug}/")
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertIn("storefront", json_data.get("data", {}))
        self.assertEqual(json_data["data"]["storefront"]["store"]["name"], "Green Valley Organics")
        self.assertEqual(json_data["data"]["storefront"]["store"]["owner_name"], "George Green")
        self.assertEqual(json_data["data"]["storefront"]["public_url"], f"/Eshopping/{store.public_url_slug}/")

        # Test resolving by bare slug
        response_bare = self.client.get(f"/stores/public-store/{store.slug}/")
        self.assertEqual(response_bare.status_code, 200)
