from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from users.models.user_mod import User
from stores.models.store_mod import Store
from products.models.product_mod import Product
from inventory.models.inventory_mod import StockBalance, StockLedgerEntry, StockMovementType
from purchases.models.purchase_mod import Supplier, Purchase, PurchaseStatus


class PurchaseLifecycleTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.vendor = User.objects.create_user(
            email="vendor_po@example.com",
            password="Password123!",
            role="vendor"
        )
        self.client.force_authenticate(user=self.vendor)

        self.store = Store.objects.create(
            name="Alpha Fresh Grocery",
            vendor=self.vendor,
            latitude=23.8103,
            longitude=90.4125
        )

        self.product = Product.objects.create(
            store=self.store,
            name="Organic Apples",
            sku="APL-001",
            price=Decimal("150.00"),
            stock=Decimal("10.000")
        )

        # Set initial stock balance
        StockBalance.objects.create(
            store=self.store,
            product=self.product,
            on_hand=Decimal("10.000"),
            reserved=Decimal("0.000")
        )

    def test_supplier_creation(self):
        """Vendor can create a supplier scoped to their store."""
        payload = {
            "store": self.store.id,
            "name": "Green Orchards Ltd",
            "contact_person": "John Doe",
            "email": "orchard@example.com",
            "phone": "+1234567890",
            "address": "123 Orchard Lane"
        }
        res = self.client.post("/purchases/suppliers/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Supplier.objects.filter(name="Green Orchards Ltd", store=self.store).exists())

    def test_purchase_draft_does_not_affect_stock(self):
        """Creating and submitting a purchase order does not prematurely update stock."""
        supplier = Supplier.objects.create(store=self.store, name="Dairy Supply Co")
        payload = {
            "store_id": self.store.id,
            "supplier_id": supplier.id,
            "reference": "INV-2026-001",
            "additional_charges": "25.00",
            "items": [
                {
                    "product_id": self.product.id,
                    "quantity": "20.000",
                    "unit_cost": "90.00"
                }
            ]
        }
        res = self.client.post("/purchases/orders/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        purchase_id = res.data["data"]["id"]

        # Stock balance must remain untouched at 10.000
        balance = StockBalance.objects.get(product=self.product)
        self.assertEqual(balance.on_hand, Decimal("10.000"))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, Decimal("10.000"))

        # Submit purchase
        sub_res = self.client.post(f"/purchases/orders/{purchase_id}/submit/")
        self.assertEqual(sub_res.status_code, status.HTTP_200_OK)

        # Still untouched
        balance.refresh_from_db()
        self.assertEqual(balance.on_hand, Decimal("10.000"))

    def test_purchase_receiving_updates_inventory_and_logs_ledger(self):
        """Confirming goods receipt atomically updates stock and creates audit ledger entry."""
        supplier = Supplier.objects.create(store=self.store, name="Produce Co")
        payload = {
            "store_id": self.store.id,
            "supplier_id": supplier.id,
            "items": [
                {
                    "product_id": self.product.id,
                    "quantity": "50.000",
                    "unit_cost": "100.00"
                }
            ]
        }
        res = self.client.post("/purchases/orders/", payload, format="json")
        purchase_id = res.data["data"]["id"]

        # Receive goods
        rec_res = self.client.post(f"/purchases/orders/{purchase_id}/receive/")
        self.assertEqual(rec_res.status_code, status.HTTP_200_OK)

        # Inventory balance should now be 10 + 50 = 60
        balance = StockBalance.objects.get(product=self.product)
        self.assertEqual(balance.on_hand, Decimal("60.000"))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, Decimal("60.000"))

        # Verify ledger audit entry
        ledger = StockLedgerEntry.objects.filter(
            product=self.product,
            movement_type=StockMovementType.PURCHASE_RECEIVE
        ).first()
        self.assertIsNotNone(ledger)
        self.assertEqual(ledger.quantity, Decimal("50.000"))
        self.assertEqual(ledger.balance_after, Decimal("60.000"))

    def test_duplicate_receive_rejected(self):
        """Receiving an already received purchase must fail idempotently without double-crediting."""
        supplier = Supplier.objects.create(store=self.store, name="Produce Co")
        payload = {
            "store_id": self.store.id,
            "supplier_id": supplier.id,
            "items": [
                {"product_id": self.product.id, "quantity": "15.000", "unit_cost": "100.00"}
            ]
        }
        res = self.client.post("/purchases/orders/", payload, format="json")
        purchase_id = res.data["data"]["id"]

        # First receive
        rec1 = self.client.post(f"/purchases/orders/{purchase_id}/receive/")
        self.assertEqual(rec1.status_code, status.HTTP_200_OK)

        # Second receive attempt must be rejected
        rec2 = self.client.post(f"/purchases/orders/{purchase_id}/receive/")
        self.assertEqual(rec2.status_code, status.HTTP_400_BAD_REQUEST)

        # Stock balance must NOT have double-counted
        balance = StockBalance.objects.get(product=self.product)
        self.assertEqual(balance.on_hand, Decimal("25.000"))
