import csv
import io
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
from inventory.models.inventory_mod import StockBalance
from inventory.models.batch_mod import ProductBatch
from purchases.models.purchase_mod import Supplier, Purchase
from purchases.services.purchase_service import PurchaseService
from orders.models.order_mod import Order, OrderStatus, PaymentStatus, PaymentMethod

User = get_user_model()


class CSVExportTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.today = timezone.now().date()

        # Primary Vendor & Store
        self.vendor = User.objects.create_user(
            email="accounting_vendor@example.com",
            password="password123",
            role="vendor"
        )
        self.store = Store.objects.create(
            name="Apex Retailers",
            vendor=self.vendor,
            is_active=True,
            is_verified=True
        )

        # Competing Vendor & Store
        self.rival_vendor = User.objects.create_user(
            email="competing_vendor@example.com",
            password="password123",
            role="vendor"
        )
        self.rival_store = Store.objects.create(
            name="Competing Store",
            vendor=self.rival_vendor,
            is_active=True,
            is_verified=True
        )

        # Customer User
        self.customer = User.objects.create_user(
            email="shopper_jane@example.com",
            password="password123",
            role="customer"
        )

        # Category and Products
        self.category = Category.objects.create(store=self.store, name="Electronics & Gadgets")
        self.product_phone = Product.objects.create(
            store=self.store,
            category=self.category,
            name="Smartphone Pro 128GB",
            sku="ELEC-PHONE-128",
            barcode="8801234567890",
            price=Decimal('500.00'),
            cost_price=Decimal('350.00'),
            stock=Decimal('10.000'),
            unit="piece"
        )
        self.product_cable = Product.objects.create(
            store=self.store,
            category=self.category,
            name="USB-C Fast Cable 1m",
            sku="ELEC-CABLE-1M",
            barcode="8801234567891",
            price=Decimal('20.00'),
            cost_price=Decimal('8.00'),
            stock=Decimal('2.000'),
            unit="piece"
        )

        # Balances
        StockBalance.objects.create(
            store=self.store,
            product=self.product_phone,
            on_hand=Decimal('10.000'),
            reserved=Decimal('1.000'),
            low_stock_threshold=Decimal('3.000')
        )
        StockBalance.objects.create(
            store=self.store,
            product=self.product_cable,
            on_hand=Decimal('2.000'),
            reserved=Decimal('0.000'),
            low_stock_threshold=Decimal('5.000')  # Low stock!
        )

        # Completed Order
        self.order_completed = Order.objects.create(
            store=self.store,
            customer=self.customer,
            order_number="ORD-2026-EX-001",
            status=OrderStatus.COMPLETED,
            payment_method=PaymentMethod.COD,
            payment_status=PaymentStatus.COLLECTED,
            subtotal=Decimal('520.00'),
            discount_amount=Decimal('20.00'),
            delivery_fee=Decimal('15.00'),
            total_amount=Decimal('515.00')
        )

        # Supplier and Purchase
        self.supplier = Supplier.objects.create(
            store=self.store,
            name="Global Tech Imports",
            tax_id="TAX-US-998877",
            email="billing@globaltech.com"
        )
        self.purchase = PurchaseService.create_purchase(
            store=self.store,
            supplier=self.supplier,
            items_data=[{
                "product_id": self.product_phone.id,
                "quantity": Decimal('10.000'),
                "unit_cost": Decimal('350.00')
            }],
            reference="PO-INVOICE-88",
            additional_charges=Decimal('50.00')
        )
        self.purchase.status = "received"
        self.purchase.received_date = timezone.now()
        self.purchase.save(update_fields=['status', 'received_date'])

        # Perishable Batch
        self.batch = ProductBatch.objects.create(
            store=self.store,
            product=self.product_cable,
            batch_number="LOT-CABLE-EXP",
            manufacture_date=self.today - timedelta(days=30),
            expiry_date=self.today + timedelta(days=90),
            initial_quantity=Decimal('20.000'),
            current_quantity=Decimal('2.000'),
            cost_price=Decimal('8.00'),
            is_clearance=True,
            clearance_discount_percent=Decimal('15.00')
        )

    def test_export_sales_tax_csv(self):
        """Vendor exports sales and tax accounting report in Excel-compatible UTF-8 CSV."""
        self.client.force_authenticate(user=self.vendor)

        res = self.client.get(f"/reports/export-sales-tax/?store_id={self.store.id}")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("text/csv", res["Content-Type"])
        self.assertIn("attachment; filename=", res["Content-Disposition"])

        content = res.content.decode('utf-8')
        # Check UTF-8 BOM
        self.assertTrue(content.startswith('\ufeff'))

        reader = list(csv.reader(io.StringIO(content.lstrip('\ufeff'))))
        headers = reader[0]
        self.assertIn("Order Number", headers)
        self.assertIn("Customer Email", headers)
        self.assertIn("Estimated Tax (5%)", headers)

        data_rows = reader[1:]
        self.assertEqual(len(data_rows), 1)
        row = data_rows[0]
        self.assertEqual(row[0], "ORD-2026-EX-001")
        self.assertEqual(row[2], "shopper_jane@example.com")
        self.assertEqual(row[6], "520.00")  # Subtotal
        self.assertEqual(row[9], "515.00")  # Total Amount
        self.assertEqual(row[10], "26.00")  # 5% of 520.00 = 26.00

    def test_export_inventory_valuation_csv(self):
        """Vendor exports inventory asset valuation report with cost values and stock statuses."""
        self.client.force_authenticate(user=self.vendor)

        res = self.client.get(f"/reports/export-inventory-valuation/?store_id={self.store.id}")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("text/csv", res["Content-Type"])

        content = res.content.decode('utf-8')
        self.assertTrue(content.startswith('\ufeff'))

        reader = list(csv.reader(io.StringIO(content.lstrip('\ufeff'))))
        headers = reader[0]
        self.assertIn("SKU", headers)
        self.assertIn("Total Cost Value", headers)
        self.assertIn("Stock Status", headers)

        data_rows = reader[1:]
        self.assertEqual(len(data_rows), 2)

        # Phone row: 10 on hand * 350 cost = 3500.00 total cost value
        phone_row = next(r for r in data_rows if r[0] == "ELEC-PHONE-128")
        self.assertEqual(phone_row[2], self.product_phone.name)
        self.assertEqual(phone_row[10], "3500.00")
        self.assertEqual(phone_row[13], "In Stock")

        # Cable row: 2 on hand (<= threshold 5) -> Low Stock
        cable_row = next(r for r in data_rows if r[0] == "ELEC-CABLE-1M")
        self.assertEqual(cable_row[13], "Low Stock")

    def test_export_purchases_procurement_csv(self):
        """Vendor exports supplier procurement and accounts payable ledger as CSV."""
        self.client.force_authenticate(user=self.vendor)

        res = self.client.get(f"/reports/export-purchases/?store_id={self.store.id}")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("text/csv", res["Content-Type"])

        content = res.content.decode('utf-8')
        reader = list(csv.reader(io.StringIO(content.lstrip('\ufeff'))))
        headers = reader[0]
        self.assertIn("PO Number", headers)
        self.assertIn("Supplier Tax ID", headers)
        self.assertIn("Total Procurement Cost", headers)

        data_rows = reader[1:]
        self.assertEqual(len(data_rows), 1)
        row = data_rows[0]
        self.assertEqual(row[1], "Global Tech Imports")
        self.assertEqual(row[2], "TAX-US-998877")
        self.assertEqual(row[9], "3550.00")  # 3500 items + 50 charges

    def test_export_perishable_batches_csv(self):
        """Vendor exports perishable batch inventory, days remaining, and clearance pricing as CSV."""
        self.client.force_authenticate(user=self.vendor)

        res = self.client.get(f"/reports/export-batches/?store_id={self.store.id}")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("text/csv", res["Content-Type"])

        content = res.content.decode('utf-8')
        reader = list(csv.reader(io.StringIO(content.lstrip('\ufeff'))))
        headers = reader[0]
        self.assertIn("Batch Number", headers)
        self.assertIn("Clearance Unit Price", headers)

        data_rows = reader[1:]
        self.assertEqual(len(data_rows), 1)
        row = data_rows[0]
        self.assertEqual(row[0], "LOT-CABLE-EXP")
        self.assertEqual(row[11], "YES")  # Is Clearance
        self.assertEqual(row[12], "15.00")  # Discount %
        self.assertEqual(row[13], "17.00")  # 20.00 * 0.85 = 17.00

    def test_export_tenant_isolation_and_security(self):
        """Cross-tenant export is blocked (403); Customer export blocked (403); Unauthenticated blocked (401)."""
        # 1. Unauthenticated -> 401 Unauthorized
        res_anon = self.client.get(f"/reports/export-sales-tax/?store_id={self.store.id}")
        self.assertEqual(res_anon.status_code, status.HTTP_401_UNAUTHORIZED)

        # 2. Customer -> 403 Forbidden
        self.client.force_authenticate(user=self.customer)
        res_cust = self.client.get(f"/reports/export-sales-tax/?store_id={self.store.id}")
        self.assertEqual(res_cust.status_code, status.HTTP_403_FORBIDDEN)

        # 3. Rival Vendor attempting to export Vendor A's store -> 403 Forbidden
        self.client.force_authenticate(user=self.rival_vendor)
        res_rival = self.client.get(f"/reports/export-sales-tax/?store_id={self.store.id}")
        self.assertEqual(res_rival.status_code, status.HTTP_403_FORBIDDEN)

        res_rival_inv = self.client.get(f"/reports/export-inventory-valuation/?store_id={self.store.id}")
        self.assertEqual(res_rival_inv.status_code, status.HTTP_403_FORBIDDEN)
