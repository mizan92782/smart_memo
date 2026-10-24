from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from users.models.user_mod import User
from stores.models.store_mod import Store
from products.models.product_mod import Product
from orders.models.order_mod import Order, OrderStatus, PaymentStatus
from inventory.models.inventory_mod import StockBalance
from purchases.models.purchase_mod import Supplier, Purchase, PurchaseStatus


class ReportsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.vendor = User.objects.create_user(
            email="report_vendor@example.com",
            password="Password123!",
            role="vendor"
        )
        self.client.force_authenticate(user=self.vendor)

        self.store = Store.objects.create(
            name="Analytics Supermart",
            vendor=self.vendor,
            latitude=23.8103,
            longitude=90.4125
        )

        self.customer = User.objects.create_user(
            email="shopper@example.com",
            password="Password123!",
            role="customer"
        )

        # Products & Inventory
        self.prod_apple = Product.objects.create(
            store=self.store,
            name="Gala Apples",
            sku="APL-GALA",
            price=Decimal("120.00")
        )
        # Low stock balance: on_hand=3, low_stock_threshold=5 -> is_low_stock True
        StockBalance.objects.create(
            store=self.store,
            product=self.prod_apple,
            on_hand=Decimal("3.000"),
            reserved=Decimal("0.000"),
            low_stock_threshold=Decimal("5.000")
        )

        # Orders
        # 1 completed order
        Order.objects.create(
            customer=self.customer,
            store=self.store,
            status=OrderStatus.COMPLETED,
            subtotal=Decimal("240.00"),
            delivery_fee=Decimal("30.00"),
            total_amount=Decimal("270.00"),
            payment_status=PaymentStatus.COLLECTED
        )
        # 1 cancelled order
        Order.objects.create(
            customer=self.customer,
            store=self.store,
            status=OrderStatus.CANCELLED,
            subtotal=Decimal("120.00"),
            delivery_fee=Decimal("30.00"),
            total_amount=Decimal("150.00"),
            payment_status=PaymentStatus.PENDING
        )

        # Purchases
        supplier = Supplier.objects.create(store=self.store, name="Mega Farm Suppliers")
        Purchase.objects.create(
            store=self.store,
            supplier=supplier,
            status=PurchaseStatus.RECEIVED,
            subtotal=Decimal("500.00"),
            additional_charges=Decimal("50.00"),
            total_cost=Decimal("550.00")
        )

    def test_sales_report(self):
        """Sales report aggregates completed orders and separates cancelled orders."""
        res = self.client.get(f"/reports/sales/?store_id={self.store.id}")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data["data"]

        self.assertEqual(data["orders"]["total"], 2)
        self.assertEqual(data["orders"]["completed"], 1)
        self.assertEqual(data["orders"]["cancelled"], 1)
        self.assertEqual(data["financials"]["gross_sales"], "270.00")
        self.assertEqual(data["financials"]["net_product_sales"], "240.00")
        self.assertEqual(data["financials"]["delivery_fees_collected"], "30.00")
        self.assertEqual(data["financials"]["cod_collected"], "270.00")

    def test_inventory_report(self):
        """Inventory report detects low-stock items correctly."""
        res = self.client.get(f"/reports/inventory/?store_id={self.store.id}")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data["data"]

        self.assertEqual(data["total_tracked_products"], 1)
        self.assertEqual(data["low_stock_count"], 1)
        self.assertEqual(len(data["low_stock_items"]), 1)
        self.assertEqual(data["low_stock_items"][0]["sku"], "APL-GALA")

    def test_purchases_report(self):
        """Purchases report computes total procurement cost for received purchases."""
        res = self.client.get(f"/reports/purchases/?store_id={self.store.id}")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data["data"]

        self.assertEqual(data["purchases"]["total"], 1)
        self.assertEqual(data["purchases"]["received"], 1)
        self.assertEqual(data["financials"]["total_procurement_cost"], "550.00")
