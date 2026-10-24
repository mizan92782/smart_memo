from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from users.models.user_mod import User
from stores.models.store_mod import Store
from categories.models.category_mod import Category
from products.models.product_mod import Product
from orders.models.order_mod import Order, OrderItem, OrderStatus, SalesMemo


class QueryOptimizationTestCase(TestCase):
    """
    Test suite enforcing N+1 query prevention.
    Verifies that list endpoints execute a constant, bounded number of SQL queries
    regardless of how many rows/child items are returned.
    """

    def setUp(self):
        self.client = APIClient()
        self.vendor = User.objects.create_user(
            email="query_vendor@example.com",
            password="Password123!",
            role="vendor"
        )
        self.client.force_authenticate(user=self.vendor)

        self.store = Store.objects.create(
            name="Scale Test Store",
            vendor=self.vendor,
            latitude=23.8103,
            longitude=90.4125
        )
        self.category = Category.objects.create(
            store=self.store,
            name="Groceries"
        )

        # Seed 15 products with categories and store relations
        for i in range(15):
            Product.objects.create(
                store=self.store,
                category=self.category,
                name=f"Bulk Product {i}",
                sku=f"SKU-BULK-{i}",
                price=Decimal("50.00"),
                stock=Decimal("100.000")
            )

        # Seed 5 orders each with 3 items and sales memo
        customer = User.objects.create_user(
            email="bulk_customer@example.com",
            password="Password123!",
            role="customer"
        )
        products = list(Product.objects.filter(store=self.store)[:3])

        for j in range(5):
            order = Order.objects.create(
                customer=customer,
                store=self.store,
                status=OrderStatus.COMPLETED,
                subtotal=Decimal("150.00"),
                total_amount=Decimal("150.00")
            )
            for p in products:
                OrderItem.objects.create(
                    order=order,
                    product=p,
                    product_name_snapshot=p.name,
                    unit_price_snapshot=p.price,
                    quantity=Decimal("1.000"),
                    line_total=Decimal("50.00")
                )
            SalesMemo.objects.create(
                order=order,
                store_name_snapshot=self.store.name,
                customer_email_snapshot=customer.email,
                items_snapshot=[{"name": p.name, "qty": "1.000", "price": "50.00"} for p in products],
                subtotal=Decimal("150.00"),
                delivery_fee=Decimal("0.00"),
                total_amount=Decimal("150.00"),
                amount_paid=Decimal("150.00")
            )

    def test_catalog_search_query_count_bounded(self):
        """Catalog search endpoint executes bounded queries with select_related for store & category."""
        # Warmup and execute with query capture
        with self.assertNumQueries(2):
            # 1 query for COUNT (pagination), 1 query for SELECT with JOINs
            res = self.client.get("/products/api/catalog/?search=Bulk")
            self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_orders_listing_query_count_bounded(self):
        """Order listing avoids N+1 by select_related on store/customer and prefetching items/memo."""
        with self.assertNumQueries(4):
            # 1 query for COUNT (pagination)
            # 1 query for base Orders with customer & store JOINs
            # 1 prefetch query for OrderItem IN (ids)
            # 1 prefetch query for SalesMemo IN (ids)
            res = self.client.get("/orders/")
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(len(res.data), 5)
