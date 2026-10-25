from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from shared.enums.enums import UserRoleEnum
from stores.models.store_mod import Store
from products.models.product_mod import Product

User = get_user_model()


class ProductListStoreScopeTests(APITestCase):
    """A store page must only list that store's products — a memo rejects
    anything from another store, so cross-store listings are unbuyable."""

    def setUp(self):
        self.vendor_a = User.objects.create_user(
            email="vendor_scope_a@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.vendor_b = User.objects.create_user(
            email="vendor_scope_b@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.store_a = Store.objects.create(
            name="Scope Mart A", vendor=self.vendor_a, address="Road 1", is_active=True
        )
        self.store_b = Store.objects.create(
            name="Scope Mart B", vendor=self.vendor_b, address="Road 2", is_active=True
        )
        self.prod_a = Product.objects.create(
            store=self.store_a, name="Store A Rice", price=Decimal('100.00'), stock=Decimal('10.000')
        )
        self.prod_b = Product.objects.create(
            store=self.store_b, name="Store B Lentils", price=Decimal('120.00'), stock=Decimal('10.000')
        )

    def _names(self, res):
        payload = res.data.get('data', res.data)
        results = payload.get('results', payload) if isinstance(payload, dict) else payload
        return {p['name'] for p in results}

    def test_store_id_filter_excludes_other_stores(self):
        res = self.client.get(f'/products/?store_id={self.store_a.id}')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        names = self._names(res)
        self.assertIn('Store A Rice', names)
        self.assertNotIn('Store B Lentils', names)

    def test_without_store_id_all_active_products_are_listed(self):
        res = self.client.get('/products/')
        names = self._names(res)
        self.assertIn('Store A Rice', names)
        self.assertIn('Store B Lentils', names)

    def test_vendor_cannot_widen_scope_to_another_vendors_store(self):
        self.client.force_authenticate(user=self.vendor_a)
        res = self.client.get(f'/products/?store_id={self.store_b.id}')
        self.assertEqual(self._names(res), set())
