from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework import status

from shared.enums.enums import UserRoleEnum
from stores.models.store_mod import Store
from products.models.product_mod import Product
from inventory.models.inventory_mod import StockBalance, StockLedgerEntry, StockMovementType
from inventory.models.reconciliation_mod import StockReconciliation, ReconciliationStatus
from inventory.services.inventory_service import InventoryService
from audit.models.audit_mod import AuditLog, AuditAction

User = get_user_model()


class StockReconciliationTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

        # Vendors & Customers
        self.vendor_a = User.objects.create_user(
            email='vendor_a_rec@example.com',
            password='Password123!',
            role=UserRoleEnum.VENDOR
        )
        self.vendor_b = User.objects.create_user(
            email='vendor_b_rec@example.com',
            password='Password123!',
            role=UserRoleEnum.VENDOR
        )
        self.customer = User.objects.create_user(
            email='customer_rec@example.com',
            password='Password123!',
            role=UserRoleEnum.CUSTOMER
        )

        # Stores
        self.store_a = Store.objects.create(
            name="Vendor A Superstore",
            vendor=self.vendor_a,
            latitude=23.8103,
            longitude=90.4125,
            is_active=True,
            is_verified=True
        )
        self.store_b = Store.objects.create(
            name="Vendor B Superstore",
            vendor=self.vendor_b,
            latitude=23.7500,
            longitude=90.3900,
            is_active=True,
            is_verified=True
        )

        # Products for Store A
        self.prod_a1 = Product.objects.create(
            store=self.store_a,
            name="Basmati Rice 5kg",
            price=Decimal("500.00"),
            stock=Decimal("50.000"),
            is_active=True
        )
        InventoryService.receive_stock(self.store_a, self.prod_a1, Decimal("50.000"))

        self.prod_a2 = Product.objects.create(
            store=self.store_a,
            name="Cooking Oil 1L",
            price=Decimal("180.00"),
            stock=Decimal("30.000"),
            is_active=True
        )
        InventoryService.receive_stock(self.store_a, self.prod_a2, Decimal("30.000"))

    def tearDown(self):
        cache.clear()

    def test_create_reconciliation_draft_computes_discrepancy_and_variance(self):
        self.client.force_authenticate(user=self.vendor_a)
        payload = {
            "store_id": self.store_a.id,
            "notes": "End of month physical inventory count",
            "items": [
                {
                    "product_id": self.prod_a1.id,
                    "physical_stock": "45.000",
                    "notes": "5 bags damaged in transit"
                },
                {
                    "product_id": self.prod_a2.id,
                    "physical_stock": "35.000",
                    "notes": "5 extra bottles found on top shelf"
                }
            ]
        }
        resp = self.client.post("/inventory/reconciliations/", payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.data["data"]

        self.assertEqual(data["status"], ReconciliationStatus.DRAFT)
        self.assertEqual(data["total_items_counted"], 2)
        # Net discrepancy: -5 + 5 = 0.000
        self.assertEqual(Decimal(str(data["total_discrepancy_qty"])), Decimal("0.000"))
        # Net variance value: (-5 * 500) + (5 * 180) = -2500 + 900 = -1600.00
        self.assertEqual(Decimal(str(data["total_discrepancy_value"])), Decimal("-1600.00"))

        items = data["items"]
        self.assertEqual(len(items), 2)
        item1 = next(i for i in items if i["product"] == self.prod_a1.id)
        self.assertEqual(Decimal(str(item1["system_stock"])), Decimal("50.000"))
        self.assertEqual(Decimal(str(item1["physical_stock"])), Decimal("45.000"))
        self.assertEqual(Decimal(str(item1["discrepancy"])), Decimal("-5.000"))
        self.assertEqual(Decimal(str(item1["variance_value"])), Decimal("-2500.00"))

    def test_apply_reconciliation_updates_stock_balances_and_ledger(self):
        self.client.force_authenticate(user=self.vendor_a)
        # Create draft
        resp = self.client.post("/inventory/reconciliations/", {
            "store_id": self.store_a.id,
            "items": [
                {"product_id": self.prod_a1.id, "physical_stock": "42.000"},
                {"product_id": self.prod_a2.id, "physical_stock": "33.000"}
            ]
        }, format='json')
        rec_id = resp.data["data"]["id"]

        # Apply reconciliation
        resp_apply = self.client.post(f"/inventory/reconciliations/{rec_id}/apply/")
        self.assertEqual(resp_apply.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_apply.data["data"]["status"], ReconciliationStatus.APPLIED)

        # Verify balances
        bal1 = StockBalance.objects.get(store=self.store_a, product=self.prod_a1)
        bal2 = StockBalance.objects.get(store=self.store_a, product=self.prod_a2)
        self.assertEqual(bal1.on_hand, Decimal("42.000"))
        self.assertEqual(bal2.on_hand, Decimal("33.000"))

        # Verify product read model synchronized
        self.prod_a1.refresh_from_db()
        self.prod_a2.refresh_from_db()
        self.assertEqual(self.prod_a1.stock, Decimal("42.000"))
        self.assertEqual(self.prod_a2.stock, Decimal("33.000"))

        # Verify StockLedgerEntries recorded
        rec = StockReconciliation.objects.get(id=rec_id)
        entries = StockLedgerEntry.objects.filter(reference_id=rec.reconciliation_number)
        self.assertEqual(entries.count(), 2)
        for entry in entries:
            self.assertEqual(entry.movement_type, StockMovementType.RECONCILIATION)
            self.assertEqual(entry.actor, self.vendor_a)

    def test_apply_reconciliation_generates_audit_log(self):
        self.client.force_authenticate(user=self.vendor_a)
        resp = self.client.post("/inventory/reconciliations/", {
            "store_id": self.store_a.id,
            "items": [{"product_id": self.prod_a1.id, "physical_stock": "48.000"}]
        }, format='json')
        rec_id = resp.data["data"]["id"]

        self.client.post(f"/inventory/reconciliations/{rec_id}/apply/")
        log = AuditLog.objects.filter(
            action=AuditAction.INVENTORY_RECONCILED,
            target_model="StockReconciliation",
            target_id=str(rec_id)
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.store, self.store_a)
        self.assertEqual(log.actor, self.vendor_a)

    def test_cannot_apply_already_applied_reconciliation(self):
        self.client.force_authenticate(user=self.vendor_a)
        resp = self.client.post("/inventory/reconciliations/", {
            "store_id": self.store_a.id,
            "items": [{"product_id": self.prod_a1.id, "physical_stock": "40.000"}]
        }, format='json')
        rec_id = resp.data["data"]["id"]

        # First apply succeeds
        resp1 = self.client.post(f"/inventory/reconciliations/{rec_id}/apply/")
        self.assertEqual(resp1.status_code, status.HTTP_200_OK)

        # Second apply fails
        resp2 = self.client.post(f"/inventory/reconciliations/{rec_id}/apply/")
        self.assertEqual(resp2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Only draft can be applied", resp2.data["message"])

    def test_cancel_draft_reconciliation_preserves_stock(self):
        self.client.force_authenticate(user=self.vendor_a)
        resp = self.client.post("/inventory/reconciliations/", {
            "store_id": self.store_a.id,
            "items": [{"product_id": self.prod_a1.id, "physical_stock": "10.000"}]
        }, format='json')
        rec_id = resp.data["data"]["id"]

        resp_cancel = self.client.post(f"/inventory/reconciliations/{rec_id}/cancel/")
        self.assertEqual(resp_cancel.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_cancel.data["data"]["status"], ReconciliationStatus.CANCELLED)

        # Verify stock remains unchanged at 50
        bal = StockBalance.objects.get(store=self.store_a, product=self.prod_a1)
        self.assertEqual(bal.on_hand, Decimal("50.000"))

    def test_reconciliation_cannot_reduce_stock_below_active_reservations(self):
        # Reserve 40 units for an active order
        InventoryService.reserve_stock(
            store=self.store_a,
            product=self.prod_a1,
            quantity=Decimal("40.000"),
            reference_id="ORD-TEST-RES"
        )
        bal = StockBalance.objects.get(store=self.store_a, product=self.prod_a1)
        self.assertEqual(bal.on_hand, Decimal("50.000"))
        self.assertEqual(bal.reserved, Decimal("40.000"))

        # Physical count reports only 30 units (lower than the 40 reserved)
        self.client.force_authenticate(user=self.vendor_a)
        resp = self.client.post("/inventory/reconciliations/", {
            "store_id": self.store_a.id,
            "items": [{"product_id": self.prod_a1.id, "physical_stock": "30.000"}]
        }, format='json')
        rec_id = resp.data["data"]["id"]

        # Applying must fail to protect active order reservations
        resp_apply = self.client.post(f"/inventory/reconciliations/{rec_id}/apply/")
        self.assertEqual(resp_apply.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("below reserved orders", resp_apply.data["message"])

        # Balances remain intact
        bal.refresh_from_db()
        self.assertEqual(bal.on_hand, Decimal("50.000"))

    def test_vendor_tenant_isolation_on_reconciliations(self):
        # Vendor A creates a reconciliation for Store A
        self.client.force_authenticate(user=self.vendor_a)
        resp = self.client.post("/inventory/reconciliations/", {
            "store_id": self.store_a.id,
            "items": [{"product_id": self.prod_a1.id, "physical_stock": "45.000"}]
        }, format='json')
        rec_a_id = resp.data["data"]["id"]

        # Vendor B tries to view Vendor A's reconciliation -> 404
        self.client.force_authenticate(user=self.vendor_b)
        resp_b_view = self.client.get(f"/inventory/reconciliations/{rec_a_id}/")
        self.assertEqual(resp_b_view.status_code, status.HTTP_404_NOT_FOUND)

        # Vendor B tries to apply Vendor A's reconciliation -> 404
        resp_b_apply = self.client.post(f"/inventory/reconciliations/{rec_a_id}/apply/")
        self.assertEqual(resp_b_apply.status_code, status.HTTP_404_NOT_FOUND)

        # Vendor B tries to create reconciliation for Store A -> 403 Forbidden
        resp_b_create = self.client.post("/inventory/reconciliations/", {
            "store_id": self.store_a.id,
            "items": [{"product_id": self.prod_a1.id, "physical_stock": "10.000"}]
        }, format='json')
        self.assertEqual(resp_b_create.status_code, status.HTTP_403_FORBIDDEN)

    def test_customer_access_blocked_from_reconciliations(self):
        self.client.force_authenticate(user=self.customer)
        resp = self.client.get("/inventory/reconciliations/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        resp_create = self.client.post("/inventory/reconciliations/", {
            "store_id": self.store_a.id,
            "items": []
        })
        self.assertEqual(resp_create.status_code, status.HTTP_403_FORBIDDEN)
