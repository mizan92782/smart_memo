from decimal import Decimal
from datetime import timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from stores.models.store_mod import Store
from products.models.product_mod import Product
from categories.models.category_mod import Category
from inventory.models.inventory_mod import StockBalance, StockLedgerEntry, StockMovementType
from inventory.models.batch_mod import ProductBatch, BatchStatus
from notifications.models.notification_mod import Notification, NotificationType
from audit.models.audit_mod import AuditLog, AuditAction

User = get_user_model()


class ProductBatchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.today = timezone.now().date()

        # Primary Vendor & Store
        self.vendor = User.objects.create_user(
            email="dairy_vendor@example.com",
            password="password123",
            role="vendor"
        )
        self.store = Store.objects.create(
            name="Fresh Dairy Mart",
            vendor=self.vendor,
            is_active=True,
            is_verified=True
        )

        # Competing Vendor & Store (Tenant Isolation verification)
        self.rival_vendor = User.objects.create_user(
            email="rival_grocer@example.com",
            password="password123",
            role="vendor"
        )
        self.rival_store = Store.objects.create(
            name="Rival Grocer",
            vendor=self.rival_vendor,
            is_active=True,
            is_verified=True
        )

        # Customer User
        self.customer = User.objects.create_user(
            email="customer_shopper@example.com",
            password="password123",
            role="customer"
        )

        # Category and Perishable Products
        self.category = Category.objects.create(
            store=self.store,
            name="Dairy & Eggs"
        )
        self.product_milk = Product.objects.create(
            store=self.store,
            category=self.category,
            name="Organic Whole Milk 1L",
            sku="DAIRY-MILK-1L",
            barcode="7890123456789",
            price=Decimal('80.00'),
            stock=Decimal('0.000'),
            is_active=True
        )

        self.rival_category = Category.objects.create(
            store=self.rival_store,
            name="Dairy"
        )
        self.rival_product = Product.objects.create(
            store=self.rival_store,
            category=self.rival_category,
            name="Rival Milk 1L",
            sku="RIVAL-MILK-1L",
            barcode="9990123456789",
            price=Decimal('85.00'),
            stock=Decimal('50.000'),
            is_active=True
        )

    def test_vendor_register_batch_with_stock_intake(self):
        """Vendor registers a new batch with add_to_stock=True, updating batch and stock balances."""
        self.client.force_authenticate(user=self.vendor)

        payload = {
            "product_id": self.product_milk.id,
            "batch_number": "LOT-202610-A1",
            "manufacture_date": str(self.today - timedelta(days=2)),
            "expiry_date": str(self.today + timedelta(days=14)),
            "initial_quantity": "50.000",
            "cost_price": "60.00",
            "add_to_stock": True,
            "notes": "Delivered in refrigerated truck #4."
        }

        res = self.client.post("/inventory/batches/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.data["data"]

        batch_id = data["id"]
        self.assertEqual(data["batch_number"], "LOT-202610-A1")
        self.assertEqual(data["status"], BatchStatus.ACTIVE)
        self.assertEqual(Decimal(data["current_quantity"]), Decimal('50.000'))
        self.assertEqual(Decimal(data["total_valuation"]), Decimal('3000.00'))
        self.assertEqual(data["days_until_expiry"], 14)

        # Verify Store Stock Balance was credited atomically
        balance = StockBalance.objects.get(store=self.store, product=self.product_milk)
        self.assertEqual(balance.on_hand, Decimal('50.000'))

        # Verify Immutable Stock Ledger Entry
        ledger = StockLedgerEntry.objects.filter(
            store=self.store,
            product=self.product_milk,
            movement_type=StockMovementType.PURCHASE_RECEIVE
        ).first()
        self.assertIsNotNone(ledger)
        self.assertEqual(ledger.quantity, Decimal('50.000'))
        self.assertIn("BATCH-LOT-202610-A1", ledger.reference_id)

        # Verify Audit Log
        audit = AuditLog.objects.filter(
            action=AuditAction.BATCH_CREATED,
            target_model="ProductBatch",
            target_id=str(batch_id)
        ).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.details["batch_number"], "LOT-202610-A1")

    def test_register_batch_validation_guards(self):
        """Reject invalid batch registration (past expiry date, non-positive quantity, duplicate batch)."""
        self.client.force_authenticate(user=self.vendor)

        # 1. Past expiry date
        past_payload = {
            "product_id": self.product_milk.id,
            "batch_number": "LOT-EXPIRED-OLD",
            "expiry_date": str(self.today - timedelta(days=5)),
            "initial_quantity": "10.000"
        }
        res = self.client.post("/inventory/batches/", past_payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        # 2. Non-positive quantity
        zero_payload = {
            "product_id": self.product_milk.id,
            "batch_number": "LOT-ZERO-QTY",
            "expiry_date": str(self.today + timedelta(days=10)),
            "initial_quantity": "0.000"
        }
        res = self.client.post("/inventory/batches/", zero_payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        # 3. Duplicate batch number
        ProductBatch.objects.create(
            store=self.store,
            product=self.product_milk,
            batch_number="LOT-DUP-100",
            expiry_date=self.today + timedelta(days=20),
            initial_quantity=Decimal('20.000'),
            current_quantity=Decimal('20.000')
        )

        dup_payload = {
            "product_id": self.product_milk.id,
            "batch_number": "LOT-DUP-100",
            "expiry_date": str(self.today + timedelta(days=25)),
            "initial_quantity": "10.000"
        }
        res = self.client.post("/inventory/batches/", dup_payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_fefo_allocation_earliest_expiry_first(self):
        """FEFO allocation strictly prioritizes the batch expiring soonest."""
        self.client.force_authenticate(user=self.vendor)

        # Batch 1: Expiring in 4 days (10 units)
        batch_earliest = ProductBatch.objects.create(
            store=self.store,
            product=self.product_milk,
            batch_number="LOT-EARLY-EXP",
            expiry_date=self.today + timedelta(days=4),
            initial_quantity=Decimal('10.000'),
            current_quantity=Decimal('10.000'),
            cost_price=Decimal('50.00')
        )
        # Batch 2: Expiring in 18 days (25 units)
        batch_later = ProductBatch.objects.create(
            store=self.store,
            product=self.product_milk,
            batch_number="LOT-LATER-EXP",
            expiry_date=self.today + timedelta(days=18),
            initial_quantity=Decimal('25.000'),
            current_quantity=Decimal('25.000'),
            cost_price=Decimal('52.00')
        )

        # Allocate 6 units
        alloc_payload = {
            "product_id": self.product_milk.id,
            "quantity": "6.000",
            "deduct": True
        }
        res = self.client.post("/inventory/batches/fefo-allocate/", alloc_payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        alloc_data = res.data["data"]

        self.assertEqual(len(alloc_data["allocations"]), 1)
        first_alloc = alloc_data["allocations"][0]
        self.assertEqual(first_alloc["batch_id"], batch_earliest.id)
        self.assertEqual(Decimal(first_alloc["allocated_quantity"]), Decimal('6.000'))

        # Verify batch current quantities in database
        batch_earliest.refresh_from_db()
        batch_later.refresh_from_db()
        self.assertEqual(batch_earliest.current_quantity, Decimal('4.000'))
        self.assertEqual(batch_later.current_quantity, Decimal('25.000'))

    def test_fefo_allocation_multi_batch_split(self):
        """Allocation splits across multiple batches when first batch is insufficient."""
        self.client.force_authenticate(user=self.vendor)

        # Batch 1: Expiring in 2 days (4 units)
        batch1 = ProductBatch.objects.create(
            store=self.store,
            product=self.product_milk,
            batch_number="LOT-SPLIT-1",
            expiry_date=self.today + timedelta(days=2),
            initial_quantity=Decimal('4.000'),
            current_quantity=Decimal('4.000')
        )
        # Batch 2: Expiring in 10 days (20 units)
        batch2 = ProductBatch.objects.create(
            store=self.store,
            product=self.product_milk,
            batch_number="LOT-SPLIT-2",
            expiry_date=self.today + timedelta(days=10),
            initial_quantity=Decimal('20.000'),
            current_quantity=Decimal('20.000')
        )

        # Request 11 units: should consume all 4 from batch1, and 7 from batch2
        res = self.client.post("/inventory/batches/fefo-allocate/", {
            "product_id": self.product_milk.id,
            "quantity": "11.000",
            "deduct": True
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data["data"]

        self.assertEqual(len(data["allocations"]), 2)
        self.assertEqual(data["allocations"][0]["batch_id"], batch1.id)
        self.assertEqual(Decimal(data["allocations"][0]["allocated_quantity"]), Decimal('4.000'))
        self.assertEqual(data["allocations"][1]["batch_id"], batch2.id)
        self.assertEqual(Decimal(data["allocations"][1]["allocated_quantity"]), Decimal('7.000'))

        batch1.refresh_from_db()
        batch2.refresh_from_db()
        self.assertEqual(batch1.current_quantity, Decimal('0.000'))
        self.assertEqual(batch1.status, BatchStatus.DEPLETED)
        self.assertEqual(batch2.current_quantity, Decimal('13.000'))

    def test_fefo_allocation_insufficient_stock_error(self):
        """Allocation fails with 400 Bad Request when requested stock exceeds unexpired batch total."""
        self.client.force_authenticate(user=self.vendor)

        ProductBatch.objects.create(
            store=self.store,
            product=self.product_milk,
            batch_number="LOT-SMALL",
            expiry_date=self.today + timedelta(days=5),
            initial_quantity=Decimal('5.000'),
            current_quantity=Decimal('5.000')
        )

        res = self.client.post("/inventory/batches/fefo-allocate/", {
            "product_id": self.product_milk.id,
            "quantity": "50.000",
            "deduct": True
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Insufficient", res.data["message"])

    def test_batch_spoilage_disposal(self):
        """Vendor writes off spoiled batch stock, decrementing batch and on-hand inventory."""
        self.client.force_authenticate(user=self.vendor)

        # Setup stock balance
        StockBalance.objects.create(
            store=self.store,
            product=self.product_milk,
            on_hand=Decimal('30.000'),
            reserved=Decimal('0.000')
        )

        batch = ProductBatch.objects.create(
            store=self.store,
            product=self.product_milk,
            batch_number="LOT-SPOIL-TEST",
            expiry_date=self.today + timedelta(days=1),
            initial_quantity=Decimal('30.000'),
            current_quantity=Decimal('30.000'),
            cost_price=Decimal('50.00')
        )

        disposal_payload = {
            "quantity": "8.000",
            "reason": "Broken Seal & Curdling",
            "notes": "Damaged during handling."
        }
        res = self.client.post(f"/inventory/batches/{batch.id}/dispose/", disposal_payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        res_data = res.data["data"]

        self.assertEqual(Decimal(res_data["disposed_quantity"]), Decimal('8.000'))
        self.assertEqual(Decimal(res_data["remaining_batch_quantity"]), Decimal('22.000'))
        self.assertEqual(Decimal(res_data["financial_loss"]), Decimal('400.00'))  # 8 * 50.00

        # Verify batch updated
        batch.refresh_from_db()
        self.assertEqual(batch.current_quantity, Decimal('22.000'))

        # Verify Store StockBalance decremented
        balance = StockBalance.objects.get(store=self.store, product=self.product_milk)
        self.assertEqual(balance.on_hand, Decimal('22.000'))

        # Verify StockLedgerEntry logged as BATCH_DISPOSAL
        ledger = StockLedgerEntry.objects.filter(
            store=self.store,
            product=self.product_milk,
            movement_type=StockMovementType.BATCH_DISPOSAL
        ).first()
        self.assertIsNotNone(ledger)
        self.assertEqual(ledger.quantity, Decimal('-8.000'))
        self.assertEqual(ledger.balance_after, Decimal('22.000'))

        # Verify Audit Log entry
        audit = AuditLog.objects.filter(
            action=AuditAction.BATCH_DISPOSED,
            target_id=str(batch.id)
        ).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.details["reason"], "Broken Seal & Curdling")

    def test_batch_disposal_cannot_breach_reservations(self):
        """Disposal write-off is blocked if remaining stock would violate active order reservations."""
        self.client.force_authenticate(user=self.vendor)

        # 20 on hand, but 18 reserved for ongoing active orders!
        StockBalance.objects.create(
            store=self.store,
            product=self.product_milk,
            on_hand=Decimal('20.000'),
            reserved=Decimal('18.000')  # only 2 unreserved
        )

        batch = ProductBatch.objects.create(
            store=self.store,
            product=self.product_milk,
            batch_number="LOT-RESERVE-GUARD",
            expiry_date=self.today + timedelta(days=2),
            initial_quantity=Decimal('20.000'),
            current_quantity=Decimal('20.000')
        )

        # Attempt to dispose 10 units (would leave 10 on hand, violating 18 reserved)
        res = self.client.post(f"/inventory/batches/{batch.id}/dispose/", {
            "quantity": "10.000",
            "reason": "Expired"
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("breach ongoing customer reservations", res.data["message"])

        # Batch and balance remain untouched
        batch.refresh_from_db()
        self.assertEqual(batch.current_quantity, Decimal('20.000'))

    def test_batch_clearance_pricing(self):
        """Vendor applies a clearance discount on a near-expiry batch."""
        self.client.force_authenticate(user=self.vendor)

        batch = ProductBatch.objects.create(
            store=self.store,
            product=self.product_milk,  # Price is 80.00
            batch_number="LOT-CLEARANCE-1",
            expiry_date=self.today + timedelta(days=3),
            initial_quantity=Decimal('15.000'),
            current_quantity=Decimal('15.000'),
            cost_price=Decimal('50.00')
        )

        # Apply 25% clearance discount
        res = self.client.post(f"/inventory/batches/{batch.id}/clearance/", {
            "discount_percent": "25.00"
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data["data"]

        self.assertTrue(data["is_clearance"])
        self.assertEqual(Decimal(data["clearance_discount_percent"]), Decimal('25.00'))
        self.assertEqual(Decimal(data["clearance_unit_price"]), Decimal('60.00'))  # 80.00 * 0.75

        # Check Audit Log
        audit = AuditLog.objects.filter(
            action=AuditAction.BATCH_CLEARANCE,
            target_id=str(batch.id)
        ).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.details["discount_percent"], "25.00")

    def test_near_expiry_alert_vendor_notification(self):
        """Scanning near-expiry batches flags their status and generates high-priority vendor notification."""
        self.client.force_authenticate(user=self.vendor)

        # Batch expiring in 3 days (within 7-day threshold)
        batch = ProductBatch.objects.create(
            store=self.store,
            product=self.product_milk,
            batch_number="LOT-ALERT-NEAR",
            expiry_date=self.today + timedelta(days=3),
            initial_quantity=Decimal('12.000'),
            current_quantity=Decimal('12.000')
        )

        res = self.client.get("/inventory/batches/near-expiry/?days_threshold=7")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        items = res.data["data"]

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["batch_id"], batch.id)
        self.assertEqual(items[0]["status"], BatchStatus.NEAR_EXPIRY)

        batch.refresh_from_db()
        self.assertEqual(batch.status, BatchStatus.NEAR_EXPIRY)

        # Verify Notification generated for store vendor
        notif = Notification.objects.filter(
            recipient=self.vendor,
            store=self.store,
            notification_type=NotificationType.BATCH_EXPIRY_ALERT
        ).first()
        self.assertIsNotNone(notif)
        self.assertIn("Perishable Stock Expiry Alert", notif.title)

    def test_tenant_isolation_and_idor_prevention(self):
        """Vendor B cannot view, allocate, or dispose Vendor A's batches; Customer is rejected (403)."""
        # Create Batch in Vendor A's store
        batch_a = ProductBatch.objects.create(
            store=self.store,
            product=self.product_milk,
            batch_number="LOT-STORE-A",
            expiry_date=self.today + timedelta(days=10),
            initial_quantity=Decimal('20.000'),
            current_quantity=Decimal('20.000')
        )

        # 1. Customer attempt -> 403 Forbidden
        self.client.force_authenticate(user=self.customer)
        res_cust = self.client.get(f"/inventory/batches/{batch_a.id}/")
        self.assertEqual(res_cust.status_code, status.HTTP_403_FORBIDDEN)

        # 2. Rival Vendor B attempt to retrieve Vendor A batch -> 404 Not Found (filtered out of queryset)
        self.client.force_authenticate(user=self.rival_vendor)
        res_rival = self.client.get(f"/inventory/batches/{batch_a.id}/")
        self.assertEqual(res_rival.status_code, status.HTTP_404_NOT_FOUND)

        # 3. Rival Vendor B attempt to dispose Vendor A batch -> 404 Not Found
        res_rival_dispose = self.client.post(f"/inventory/batches/{batch_a.id}/dispose/", {
            "quantity": "5.000",
            "reason": "Malicious write-off"
        }, format="json")
        self.assertEqual(res_rival_dispose.status_code, status.HTTP_404_NOT_FOUND)

        # 4. Rival Vendor B attempt to allocate Vendor A product batches -> 403 Forbidden
        res_rival_alloc = self.client.post("/inventory/batches/fefo-allocate/", {
            "product_id": self.product_milk.id,
            "quantity": "5.000"
        }, format="json")
        self.assertEqual(res_rival_alloc.status_code, status.HTTP_403_FORBIDDEN)
