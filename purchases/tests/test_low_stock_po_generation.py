from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from stores.models.store_mod import Store
from products.models.product_mod import Product
from categories.models.category_mod import Category
from inventory.models.inventory_mod import StockBalance
from purchases.models.purchase_mod import Supplier, Purchase, PurchaseStatus
from purchases.services.purchase_service import PurchaseService
from notifications.models.notification_mod import Notification, NotificationType
from audit.models.audit_mod import AuditLog, AuditAction

User = get_user_model()


class LowStockPOGenerationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Primary Vendor & Store
        self.vendor = User.objects.create_user(
            email="supermarket_vendor@example.com",
            password="password123",
            role="vendor"
        )
        self.store = Store.objects.create(
            name="Mega Supermarket",
            vendor=self.vendor,
            is_active=True,
            is_verified=True
        )

        # Competing Vendor & Store
        self.rival_vendor = User.objects.create_user(
            email="rival_store_vendor@example.com",
            password="password123",
            role="vendor"
        )
        self.rival_store = Store.objects.create(
            name="Rival Grocery",
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

        # Category
        self.category = Category.objects.create(store=self.store, name="Grocery & Staples")

        # Suppliers
        self.supplier_beverage = Supplier.objects.create(
            store=self.store,
            name="Beverage Wholesale Ltd",
            email="orders@bevwholesale.com"
        )
        self.supplier_bakery = Supplier.objects.create(
            store=self.store,
            name="Sunrise Bakery Distributors",
            email="sales@sunrisebakery.com"
        )

        # Products
        # Prod 1: Beverage - low stock (avail: 2, threshold: 5, target: 30) -> reorder 28
        self.product_cola = Product.objects.create(
            store=self.store,
            category=self.category,
            name="Cola 500ml",
            sku="BEV-COLA-500",
            price=Decimal('25.00'),
            cost_price=Decimal('18.00'),
            primary_supplier=self.supplier_beverage,
            reorder_quantity=Decimal('25.000'),
            stock=Decimal('2.000')
        )
        StockBalance.objects.create(
            store=self.store,
            product=self.product_cola,
            on_hand=Decimal('2.000'),
            reserved=Decimal('0.000'),
            low_stock_threshold=Decimal('5.000'),
            reorder_quantity=Decimal('25.000'),
            target_stock_level=Decimal('30.000')
        )

        # Prod 2: Beverage - low stock (avail: 0, threshold: 10, target: 40) -> reorder 40
        self.product_water = Product.objects.create(
            store=self.store,
            category=self.category,
            name="Mineral Water 1L",
            sku="BEV-WATER-1L",
            price=Decimal('15.00'),
            cost_price=Decimal('10.00'),
            primary_supplier=self.supplier_beverage,
            reorder_quantity=Decimal('30.000'),
            stock=Decimal('0.000')
        )
        StockBalance.objects.create(
            store=self.store,
            product=self.product_water,
            on_hand=Decimal('0.000'),
            reserved=Decimal('0.000'),
            low_stock_threshold=Decimal('10.000'),
            reorder_quantity=Decimal('30.000'),
            target_stock_level=Decimal('40.000')
        )

        # Prod 3: Bakery - low stock (avail: 3, threshold: 8, target: 20) -> reorder 17
        self.product_bread = Product.objects.create(
            store=self.store,
            category=self.category,
            name="Whole Wheat Bread 400g",
            sku="BAKE-BREAD-400",
            price=Decimal('50.00'),
            cost_price=Decimal('35.00'),
            primary_supplier=self.supplier_bakery,
            reorder_quantity=Decimal('15.000'),
            stock=Decimal('3.000')
        )
        StockBalance.objects.create(
            store=self.store,
            product=self.product_bread,
            on_hand=Decimal('3.000'),
            reserved=Decimal('0.000'),
            low_stock_threshold=Decimal('8.000'),
            reorder_quantity=Decimal('15.000'),
            target_stock_level=Decimal('20.000')
        )

        # Prod 4: High stock - should NOT be reordered
        self.product_rice = Product.objects.create(
            store=self.store,
            category=self.category,
            name="Basmati Rice 5kg",
            sku="GROC-RICE-5KG",
            price=Decimal('450.00'),
            cost_price=Decimal('360.00'),
            primary_supplier=self.supplier_bakery,
            stock=Decimal('100.000')
        )
        StockBalance.objects.create(
            store=self.store,
            product=self.product_rice,
            on_hand=Decimal('100.000'),
            reserved=Decimal('0.000'),
            low_stock_threshold=Decimal('10.000')
        )

    def test_auto_generate_draft_pos_grouped_by_supplier(self):
        """Auto-generate draft POs grouping low-stock items by their primary supplier."""
        self.client.force_authenticate(user=self.vendor)

        payload = {
            "store_id": self.store.id,
            "include_open_order_guard": True
        }

        res = self.client.post("/purchases/orders/generate-low-stock-pos/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.data["data"]

        # Exactly 2 POs generated (1 for Beverage Wholesale Ltd with 2 items, 1 for Sunrise Bakery with 1 item)
        self.assertEqual(data["created_orders_count"], 2)
        orders = data["orders"]
        self.assertEqual(len(orders), 2)

        # Verify suppliers in generated orders
        supplier_ids = {o["supplier"] for o in orders}
        self.assertEqual(supplier_ids, {self.supplier_beverage.id, self.supplier_bakery.id})

        # Check Beverage PO items
        bev_order = next(o for o in orders if o["supplier"] == self.supplier_beverage.id)
        self.assertEqual(len(bev_order["items"]), 2)
        self.assertEqual(bev_order["status"], PurchaseStatus.DRAFT)
        self.assertIn("AUTO-REORDER-", bev_order["reference"])

        # Check Bakery PO items
        bake_order = next(o for o in orders if o["supplier"] == self.supplier_bakery.id)
        self.assertEqual(len(bake_order["items"]), 1)
        self.assertEqual(bake_order["items"][0]["product"], self.product_bread.id)

        # Verify Audit Logs generated
        audit_entries = AuditLog.objects.filter(action=AuditAction.PURCHASE_ORDER_AUTO_GENERATED)
        self.assertEqual(audit_entries.count(), 2)

        # Verify In-App Notification dispatched to store vendor
        notif = Notification.objects.filter(
            recipient=self.vendor,
            store=self.store,
            notification_type=NotificationType.PURCHASE_ORDER_GENERATED
        ).first()
        self.assertIsNotNone(notif)
        self.assertIn("Automated Purchase Orders Generated", notif.title)

    def test_open_order_guard_prevents_duplicate_pos(self):
        """Open order guard skips products already queued in a draft or submitted purchase order."""
        self.client.force_authenticate(user=self.vendor)

        # Pre-create a draft purchase for Cola
        PurchaseService.create_purchase(
            store=self.store,
            supplier=self.supplier_beverage,
            items_data=[{
                "product_id": self.product_cola.id,
                "quantity": Decimal('25.000'),
                "unit_cost": Decimal('18.00')
            }],
            reference="MANUAL-DRAFT-1"
        )

        # Run automated generator
        res = self.client.post("/purchases/orders/generate-low-stock-pos/", {
            "store_id": self.store.id,
            "include_open_order_guard": True
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.data["data"]

        # Cola was skipped because an open PO already exists
        self.assertEqual(data["skipped_open_orders_count"], 1)
        self.assertEqual(data["skipped_existing_orders"][0]["product_id"], self.product_cola.id)

        # The Beverage PO now only contains Mineral Water!
        bev_order = next(o for o in data["orders"] if o["supplier"] == self.supplier_beverage.id)
        self.assertEqual(len(bev_order["items"]), 1)
        self.assertEqual(bev_order["items"][0]["product"], self.product_water.id)

    def test_fallback_to_historical_and_default_supplier(self):
        """Low stock product without primary supplier resolves historical supplier or default supplier."""
        self.client.force_authenticate(user=self.vendor)

        # Create product with NO primary supplier
        product_snack = Product.objects.create(
            store=self.store,
            category=self.category,
            name="Potato Chips 50g",
            sku="SNACK-CHIPS-50",
            price=Decimal('30.00'),
            cost_price=Decimal('20.00'),
            primary_supplier=None,
            stock=Decimal('1.000')
        )
        StockBalance.objects.create(
            store=self.store,
            product=product_snack,
            on_hand=Decimal('1.000'),
            low_stock_threshold=Decimal('10.000')
        )

        # Simulate historical purchase receipt from Sunrise Bakery
        past_po = PurchaseService.create_purchase(
            store=self.store,
            supplier=self.supplier_bakery,
            items_data=[{
                "product_id": product_snack.id,
                "quantity": Decimal('50.000'),
                "unit_cost": Decimal('20.00')
            }]
        )
        past_po.status = PurchaseStatus.RECEIVED
        past_po.save(update_fields=['status'])

        # Run generator: snack should automatically be grouped into Sunrise Bakery!
        res = self.client.post("/purchases/orders/generate-low-stock-pos/", {
            "store_id": self.store.id
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.data["data"]

        bake_order = next(o for o in data["orders"] if o["supplier"] == self.supplier_bakery.id)
        product_ids = [it["product"] for it in bake_order["items"]]
        self.assertIn(product_snack.id, product_ids)

    def test_security_tenant_isolation_and_customer_forbidden(self):
        """Rival vendor cannot generate POs for Vendor A's store; Customer receives 403 Forbidden."""
        # 1. Customer attempt -> 403 Forbidden
        self.client.force_authenticate(user=self.customer)
        res_cust = self.client.post("/purchases/orders/generate-low-stock-pos/", {
            "store_id": self.store.id
        }, format="json")
        self.assertEqual(res_cust.status_code, status.HTTP_403_FORBIDDEN)

        # 2. Rival vendor attempt on Vendor A's store -> 403 Forbidden
        self.client.force_authenticate(user=self.rival_vendor)
        res_rival = self.client.post("/purchases/orders/generate-low-stock-pos/", {
            "store_id": self.store.id
        }, format="json")
        self.assertEqual(res_rival.status_code, status.HTTP_403_FORBIDDEN)
