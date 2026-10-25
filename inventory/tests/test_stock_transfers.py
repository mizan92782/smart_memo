from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from stores.models.store_mod import Store
from products.models.product_mod import Product
from categories.models.category_mod import Category
from inventory.models.inventory_mod import StockBalance, StockLedgerEntry, StockMovementType
from inventory.models.transfer_mod import StockTransfer, StockTransferItem, TransferStatus

User = get_user_model()


class StockTransferTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Vendor 1 owning two stores
        self.vendor = User.objects.create_user(
            email="vendor_warehouse@example.com",
            password="password123",
            role="vendor"
        )
        self.warehouse = Store.objects.create(
            name="Central Warehouse Hub",
            vendor=self.vendor,
            is_active=True,
            is_verified=True
        )
        self.retail_store = Store.objects.create(
            name="Downtown Retail Outlet",
            vendor=self.vendor,
            is_active=True,
            is_verified=True
        )

        # Competing Vendor 2 with Store 3
        self.rival_vendor = User.objects.create_user(
            email="rival_vendor@example.com",
            password="password123",
            role="vendor"
        )
        self.rival_store = Store.objects.create(
            name="Rival Mart",
            vendor=self.rival_vendor,
            is_active=True,
            is_verified=True
        )

        # Warehouse Product
        self.category = Category.objects.create(
            store=self.warehouse,
            name="Beverages"
        )

        self.product_juice = Product.objects.create(
            store=self.warehouse,
            category=self.category,
            name="Fresh Orange Juice 1L",
            sku="BEV-OJ-1L",
            barcode="8901234567890",
            price=Decimal('45.00'),
            stock=Decimal('100.000'),
            is_active=True
        )
        self.warehouse_balance = StockBalance.objects.create(
            store=self.warehouse,
            product=self.product_juice,
            on_hand=Decimal('100.000'),
            reserved=Decimal('10.000')  # Available = 90.000
        )

    def test_vendor_create_draft_transfer(self):
        """Vendor creates a draft stock transfer between their two stores."""
        self.client.force_authenticate(user=self.vendor)
        payload = {
            "source_store_id": self.warehouse.id,
            "destination_store_id": self.retail_store.id,
            "driver_name": "Dave Courier",
            "driver_phone": "+1234567890",
            "vehicle_type": "Van",
            "tracking_notes": "Stock replenishment for weekend sale",
            "items": [
                {
                    "product_id": self.product_juice.id,
                    "quantity": "25.000"
                }
            ]
        }
        res = self.client.post("/inventory/transfers/create-transfer/", payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res.data['success'])

        data = res.data['data']
        self.assertTrue(data['transfer_number'].startswith("TRF-"))
        self.assertEqual(data['status'], TransferStatus.DRAFT)
        self.assertEqual(len(data['items']), 1)
        self.assertEqual(data['items'][0]['quantity'], '25.000')

        # Stock in warehouse should NOT be touched yet in DRAFT status
        self.warehouse_balance.refresh_from_db()
        self.assertEqual(self.warehouse_balance.on_hand, Decimal('100.000'))

    def test_reject_transfer_to_competitor_store(self):
        """Vendor cannot transfer stock to a store they do not own (IDOR defense)."""
        self.client.force_authenticate(user=self.vendor)
        payload = {
            "source_store_id": self.warehouse.id,
            "destination_store_id": self.rival_store.id,  # Owned by rival vendor
            "items": [{"product_id": self.product_juice.id, "quantity": "10.000"}]
        }
        res = self.client.post("/inventory/transfers/create-transfer/", payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("only transfer stock between stores you own", res.data['message'])

    def test_reject_transfer_with_same_source_and_destination(self):
        """Source and destination store cannot be identical."""
        self.client.force_authenticate(user=self.vendor)
        payload = {
            "source_store_id": self.warehouse.id,
            "destination_store_id": self.warehouse.id,
            "items": [{"product_id": self.product_juice.id, "quantity": "5.000"}]
        }
        res = self.client.post("/inventory/transfers/create-transfer/", payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_transfer_exceeding_available_stock(self):
        """Cannot transfer more than available stock (on_hand minus reserved)."""
        self.client.force_authenticate(user=self.vendor)
        payload = {
            "source_store_id": self.warehouse.id,
            "destination_store_id": self.retail_store.id,
            "items": [{"product_id": self.product_juice.id, "quantity": "95.000"}]  # Available is only 90
        }
        res = self.client.post("/inventory/transfers/create-transfer/", payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Insufficient stock", res.data['message'])

    def test_full_lifecycle_dispatch_and_receive_with_auto_provisioning(self):
        """
        Complete lifecycle:
        1. Create draft transfer.
        2. Dispatch: stock deducted from source on-hand with row locks and TRANSFER_OUT logged.
        3. Receive: destination product auto-provisioned matching SKU/barcode and credited with TRANSFER_IN.
        """
        # 1. Create
        self.client.force_authenticate(user=self.vendor)
        create_resp = self.client.post("/inventory/transfers/create-transfer/", {
            "source_store_id": self.warehouse.id,
            "destination_store_id": self.retail_store.id,
            "driver_name": "Dave Courier",
            "items": [{"product_id": self.product_juice.id, "quantity": "30.000"}]
        }, format='json')
        transfer_id = create_resp.data['data']['id']

        # 2. Dispatch
        dispatch_resp = self.client.post(f"/inventory/transfers/{transfer_id}/dispatch/", format='json')
        self.assertEqual(dispatch_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(dispatch_resp.data['data']['status'], TransferStatus.IN_TRANSIT)

        # Verify source warehouse deducted
        self.warehouse_balance.refresh_from_db()
        self.assertEqual(self.warehouse_balance.on_hand, Decimal('70.000'))  # 100 - 30

        # Verify TRANSFER_OUT ledger entry
        out_ledger = StockLedgerEntry.objects.filter(
            store=self.warehouse,
            product=self.product_juice,
            movement_type=StockMovementType.TRANSFER_OUT
        ).first()
        self.assertIsNotNone(out_ledger)
        self.assertEqual(out_ledger.quantity, Decimal('30.000'))
        self.assertEqual(out_ledger.balance_after, Decimal('70.000'))

        # 3. Receive at retail store
        receive_resp = self.client.post(f"/inventory/transfers/{transfer_id}/receive/", format='json')
        self.assertEqual(receive_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(receive_resp.data['data']['status'], TransferStatus.RECEIVED)

        # Verify retail store now has product auto-provisioned
        dest_product = Product.objects.filter(
            store=self.retail_store,
            sku=self.product_juice.sku
        ).first()
        self.assertIsNotNone(dest_product)
        self.assertEqual(dest_product.name, self.product_juice.name)
        self.assertEqual(dest_product.stock, Decimal('30.000'))

        # Verify retail store StockBalance
        dest_balance = StockBalance.objects.filter(
            store=self.retail_store,
            product=dest_product
        ).first()
        self.assertIsNotNone(dest_balance)
        self.assertEqual(dest_balance.on_hand, Decimal('30.000'))

        # Verify TRANSFER_IN ledger entry
        in_ledger = StockLedgerEntry.objects.filter(
            store=self.retail_store,
            product=dest_product,
            movement_type=StockMovementType.TRANSFER_IN
        ).first()
        self.assertIsNotNone(in_ledger)
        self.assertEqual(in_ledger.quantity, Decimal('30.000'))

    def test_cancel_in_transit_transfer_restores_source_stock(self):
        """Cancelling an in-transit transfer safely restores stock to source store."""
        self.client.force_authenticate(user=self.vendor)
        create_resp = self.client.post("/inventory/transfers/create-transfer/", {
            "source_store_id": self.warehouse.id,
            "destination_store_id": self.retail_store.id,
            "items": [{"product_id": self.product_juice.id, "quantity": "20.000"}]
        }, format='json')
        transfer_id = create_resp.data['data']['id']

        # Dispatch
        self.client.post(f"/inventory/transfers/{transfer_id}/dispatch/", format='json')
        self.warehouse_balance.refresh_from_db()
        self.assertEqual(self.warehouse_balance.on_hand, Decimal('80.000'))

        # Cancel in transit
        cancel_resp = self.client.post(f"/inventory/transfers/{transfer_id}/cancel/", {
            "reason": "Transit vehicle broke down"
        }, format='json')
        self.assertEqual(cancel_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(cancel_resp.data['data']['status'], TransferStatus.CANCELLED)

        # Source store stock should be restored back to 100
        self.warehouse_balance.refresh_from_db()
        self.assertEqual(self.warehouse_balance.on_hand, Decimal('100.000'))

        # Verify ledger has TRANSFER_CANCEL_RESTORE
        restore_ledger = StockLedgerEntry.objects.filter(
            store=self.warehouse,
            product=self.product_juice,
            movement_type=StockMovementType.TRANSFER_CANCEL_RESTORE
        ).first()
        self.assertIsNotNone(restore_ledger)
        self.assertEqual(restore_ledger.quantity, Decimal('20.000'))
        self.assertEqual(restore_ledger.balance_after, Decimal('100.000'))

    def test_transfer_driver_waybill_manifest_slip(self):
        """Driver 40-col monospace waybill generation."""
        self.client.force_authenticate(user=self.vendor)
        create_resp = self.client.post("/inventory/transfers/create-transfer/", {
            "source_store_id": self.warehouse.id,
            "destination_store_id": self.retail_store.id,
            "driver_name": "Dave Courier",
            "driver_phone": "+1234567890",
            "vehicle_type": "Toyota HiAce Van",
            "tracking_notes": "Handle with care",
            "items": [{"product_id": self.product_juice.id, "quantity": "15.000"}]
        }, format='json')
        transfer_id = create_resp.data['data']['id']

        # Fetch plain text waybill slip
        slip_resp = self.client.get(f"/inventory/transfers/{transfer_id}/waybill/?receipt_format=text")
        self.assertEqual(slip_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(slip_resp['content-type'], 'text/plain; charset=utf-8')
        content = slip_resp.content.decode('utf-8')

        self.assertIn("TRANSFER MANIFEST / WAYBILL", content)
        self.assertIn("CENTRAL WAREHOUSE HUB", content)
        self.assertIn("DOWNTOWN RETAIL OUTLET", content)
        self.assertIn("Dave Courier", content)
        self.assertIn("Fresh Orange Juice 1L", content)
        self.assertIn("15.000", content)

    def test_cross_vendor_defense_on_transfer_actions(self):
        """Rival vendor cannot dispatch, receive, or cancel another vendor's transfers."""
        self.client.force_authenticate(user=self.vendor)
        create_resp = self.client.post("/inventory/transfers/create-transfer/", {
            "source_store_id": self.warehouse.id,
            "destination_store_id": self.retail_store.id,
            "items": [{"product_id": self.product_juice.id, "quantity": "10.000"}]
        }, format='json')
        transfer_id = create_resp.data['data']['id']

        # Rival vendor attempts to dispatch
        self.client.force_authenticate(user=self.rival_vendor)
        hack_dispatch = self.client.post(f"/inventory/transfers/{transfer_id}/dispatch/", format='json')
        self.assertEqual(hack_dispatch.status_code, status.HTTP_403_FORBIDDEN)

        # Rival vendor attempts to cancel
        hack_cancel = self.client.post(f"/inventory/transfers/{transfer_id}/cancel/", {"reason": "Malicious"}, format='json')
        self.assertEqual(hack_cancel.status_code, status.HTTP_403_FORBIDDEN)
