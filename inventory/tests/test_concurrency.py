from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from users.models.user_mod import User
from stores.models.store_mod import Store
from products.models.product_mod import Product
from inventory.services.inventory_service import InventoryService
from shared.enums.enums import UserRoleEnum


class InventoryConcurrencyAndSecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Vendor A
        self.vendor_a = User.objects.create_user(
            email="inv_a@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.store_a = Store.objects.create(vendor=self.vendor_a, name="Store A")
        self.prod_a = Product.objects.create(store=self.store_a, name="Sugar", price=100.00, stock=0)

        # Vendor B
        self.vendor_b = User.objects.create_user(
            email="inv_b@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.store_b = Store.objects.create(vendor=self.vendor_b, name="Store B")
        self.prod_b = Product.objects.create(store=self.store_b, name="Salt", price=50.00, stock=0)

    def test_insufficient_stock_reservation_fails(self):
        InventoryService.receive_stock(self.store_a, self.prod_a, Decimal('5.000'))
        with self.assertRaises(ValueError):
            InventoryService.reserve_stock(self.store_a, self.prod_a, Decimal('10.000'))

    def test_adjustment_cannot_reduce_stock_below_reserved(self):
        InventoryService.receive_stock(self.store_a, self.prod_a, Decimal('10.000'))
        InventoryService.reserve_stock(self.store_a, self.prod_a, Decimal('6.000'))

        # Trying to subtract 8 would leave on_hand=2, but reserved is 6!
        with self.assertRaises(ValueError):
            InventoryService.adjust_stock(self.store_a, self.prod_a, Decimal('-8.000'))

    def test_vendor_a_cannot_adjust_vendor_b_stock(self):
        self.client.force_authenticate(user=self.vendor_a)
        response = self.client.post('/inventory/balances/adjust/', {
            'product_id': self.prod_b.id,
            'quantity': 20.0,
            'reason': 'manual_adjustment'
        })
        self.assertEqual(response.status_code, 403)
