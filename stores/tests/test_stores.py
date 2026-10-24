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
