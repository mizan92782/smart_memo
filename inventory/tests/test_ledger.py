from decimal import Decimal
from django.test import TestCase
from users.models.user_mod import User
from stores.models.store_mod import Store
from products.models.product_mod import Product
from inventory.models.inventory_mod import StockBalance, StockLedgerEntry, StockMovementType
from inventory.services.inventory_service import InventoryService
from shared.enums.enums import UserRoleEnum


class InventoryLedgerTests(TestCase):
    def setUp(self):
        self.vendor = User.objects.create_user(
            email="inv_vendor@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.store = Store.objects.create(vendor=self.vendor, name="Super Grocer")
        self.product = Product.objects.create(
            store=self.store, name="Rice 5kg", price=350.00, stock=0
        )

    def test_receive_stock_updates_balance_and_writes_ledger(self):
        balance = InventoryService.receive_stock(
            store=self.store,
            product=self.product,
            quantity=Decimal('50.000'),
            reference_id="PO-1001",
            actor=self.vendor,
            notes="Initial stock intake"
        )
        self.assertEqual(balance.on_hand, Decimal('50.000'))
        self.assertEqual(balance.available, Decimal('50.000'))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, Decimal('50.000'))

        entry = StockLedgerEntry.objects.filter(product=self.product).first()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.movement_type, StockMovementType.PURCHASE_RECEIVE)
        self.assertEqual(entry.quantity, Decimal('50.000'))
        self.assertEqual(entry.balance_after, Decimal('50.000'))

    def test_stock_reservation_and_fulfillment_lifecycle(self):
        # 1. Receive 20 units
        InventoryService.receive_stock(self.store, self.product, Decimal('20.000'))

        # 2. Reserve 5 units for an order
        bal = InventoryService.reserve_stock(self.store, self.product, Decimal('5.000'), reference_id="ORD-1")
        self.assertEqual(bal.on_hand, Decimal('20.000'))
        self.assertEqual(bal.reserved, Decimal('5.000'))
        self.assertEqual(bal.available, Decimal('15.000'))

        # 3. Fulfill the order
        bal = InventoryService.fulfill_stock(self.store, self.product, Decimal('5.000'), reference_id="ORD-1")
        self.assertEqual(bal.on_hand, Decimal('15.000'))
        self.assertEqual(bal.reserved, Decimal('0.000'))
        self.assertEqual(bal.available, Decimal('15.000'))

    def test_order_cancellation_releases_reserved_stock(self):
        InventoryService.receive_stock(self.store, self.product, Decimal('10.000'))
        InventoryService.reserve_stock(self.store, self.product, Decimal('4.000'))

        # Cancel & restore
        bal = InventoryService.release_reserved_stock(self.store, self.product, Decimal('4.000'))
        self.assertEqual(bal.reserved, Decimal('0.000'))
        self.assertEqual(bal.available, Decimal('10.000'))
