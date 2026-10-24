from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from users.models.user_mod import User
from stores.models.store_mod import Store
from products.models.product_mod import Product
from cards.repositories.card_repository import CardRepository
from cards.services.card_service import CardService
from inventory.services.inventory_service import InventoryService
from orders.models.order_mod import Order, OrderStatus, FulfillmentType, PaymentStatus
from orders.services.order_service import OrderService
from shared.enums.enums import UserRoleEnum


class SalesMemosAndSpendingTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Vendor A & Store A
        self.vendor_a = User.objects.create_user(
            email="vendor_a@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.store_a = Store.objects.create(
            vendor=self.vendor_a,
            name="Green Valley Grocery",
            pickup_enabled=True,
            delivery_enabled=True
        )

        # Vendor B & Store B
        self.vendor_b = User.objects.create_user(
            email="vendor_b@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.store_b = Store.objects.create(
            vendor=self.vendor_b,
            name="Sunrise Bakery",
            pickup_enabled=True,
            delivery_enabled=True
        )

        # Products
        self.product_a = Product.objects.create(store=self.store_a, name="Basmati Rice 5kg", price=450.00, stock=0)
        InventoryService.receive_stock(self.store_a, self.product_a, Decimal('50.000'))

        self.product_b = Product.objects.create(store=self.store_b, name="Whole Wheat Bread", price=120.00, stock=0)
        InventoryService.receive_stock(self.store_b, self.product_b, Decimal('50.000'))

        # Customers
        self.customer_a = User.objects.create_user(
            email="shopper_a@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )
        self.customer_b = User.objects.create_user(
            email="shopper_b@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )

    def _complete_walk_in_order(self, customer, store, product, quantity=Decimal('1.000')):
        card = CardRepository.create_card(user=customer, store=store)
        CardService.add_product_to_card(card.id, product.id, quantity)
        order = OrderService.submit_order_from_card(
            card=card,
            customer=customer,
            fulfillment_type=FulfillmentType.WALK_IN
        )
        OrderService.handover_order(order=order, actor=store.vendor, payment_collected=True)
        order.refresh_from_db()
        return order

    def test_thermal_receipt_formatting(self):
        order = self._complete_walk_in_order(self.customer_a, self.store_a, self.product_a, Decimal('2.000'))
        sales_memo = order.sales_memo

        receipt = sales_memo.format_thermal_receipt(width=40)
        self.assertIn("GREEN VALLEY GROCERY", receipt)
        self.assertIn("Smart Memo System - Digital Receipt", receipt)
        self.assertIn(sales_memo.memo_number, receipt)
        self.assertIn(order.order_number, receipt)
        self.assertIn(self.customer_a.email, receipt)
        self.assertIn(sales_memo.walk_in_code_snapshot, receipt)
        self.assertIn("Basmati Rice 5Kg", receipt)
        self.assertIn("Subtotal:", receipt)
        self.assertIn("TOTAL AMOUNT:", receipt)
        self.assertIn("900.00", receipt)
        self.assertIn("Thank you for shopping with us!", receipt)

    def test_get_single_sales_memo_endpoints(self):
        order = self._complete_walk_in_order(self.customer_a, self.store_a, self.product_a, Decimal('1.000'))

        self.client.force_authenticate(user=self.customer_a)

        # JSON response with thermal_receipt field
        res_json = self.client.get(f'/orders/{order.id}/sales_memo/')
        self.assertEqual(res_json.status_code, status.HTTP_200_OK)
        data = res_json.json()['data']
        self.assertEqual(data['memo_number'], order.sales_memo.memo_number)
        self.assertEqual(data['order_number'], order.order_number)
        self.assertIn('thermal_receipt', data)
        self.assertIn("GREEN VALLEY GROCERY", data['thermal_receipt'])

        # Thermal raw plain text response via query param
        res_text = self.client.get(f'/orders/{order.id}/sales_memo/?receipt_format=thermal')
        self.assertEqual(res_text.status_code, status.HTTP_200_OK)
        self.assertEqual(res_text['Content-Type'], 'text/plain; charset=utf-8')
        self.assertIn("GREEN VALLEY GROCERY", res_text.content.decode('utf-8'))

        # Direct thermal-receipt action endpoint
        res_action = self.client.get(f'/orders/{order.id}/thermal-receipt/')
        self.assertEqual(res_action.status_code, status.HTTP_200_OK)
        self.assertEqual(res_action['Content-Type'], 'text/plain; charset=utf-8')
        self.assertIn("GREEN VALLEY GROCERY", res_action.content.decode('utf-8'))

    def test_customer_digital_sales_memos_wallet_listing(self):
        # Customer A visits Store A and Store B
        order_1 = self._complete_walk_in_order(self.customer_a, self.store_a, self.product_a, Decimal('1.000'))
        order_2 = self._complete_walk_in_order(self.customer_a, self.store_b, self.product_b, Decimal('2.000'))

        self.client.force_authenticate(user=self.customer_a)
        res = self.client.get('/orders/sales-memos/')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        memos = res.json()['data']
        self.assertEqual(len(memos), 2)
        memo_numbers = [m['memo_number'] for m in memos]
        self.assertIn(order_1.sales_memo.memo_number, memo_numbers)
        self.assertIn(order_2.sales_memo.memo_number, memo_numbers)

    def test_vendor_sales_memos_listing_with_as_vendor(self):
        # Customer A orders from Store A and Store B
        order_1 = self._complete_walk_in_order(self.customer_a, self.store_a, self.product_a, Decimal('1.000'))
        order_2 = self._complete_walk_in_order(self.customer_a, self.store_b, self.product_b, Decimal('2.000'))

        # Vendor A logs in
        self.client.force_authenticate(user=self.vendor_a)
        res = self.client.get('/orders/sales-memos/?as_vendor=true')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        memos = res.json()['data']
        self.assertEqual(len(memos), 1)
        self.assertEqual(memos[0]['memo_number'], order_1.sales_memo.memo_number)
        self.assertEqual(memos[0]['store_name_snapshot'], "Green Valley Grocery")

    def test_sales_memos_filtering_by_store_and_search(self):
        order_1 = self._complete_walk_in_order(self.customer_a, self.store_a, self.product_a, Decimal('1.000'))
        order_2 = self._complete_walk_in_order(self.customer_a, self.store_b, self.product_b, Decimal('2.000'))

        self.client.force_authenticate(user=self.customer_a)

        # Filter by store_id
        res_filter = self.client.get(f'/orders/sales-memos/?store_id={self.store_b.id}')
        self.assertEqual(res_filter.status_code, status.HTTP_200_OK)
        memos = res_filter.json()['data']
        self.assertEqual(len(memos), 1)
        self.assertEqual(memos[0]['store_name_snapshot'], "Sunrise Bakery")

        # Search by memo number
        res_search = self.client.get(f'/orders/sales-memos/?search={order_1.sales_memo.memo_number}')
        self.assertEqual(res_search.status_code, status.HTTP_200_OK)
        memos = res_search.json()['data']
        self.assertEqual(len(memos), 1)
        self.assertEqual(memos[0]['memo_number'], order_1.sales_memo.memo_number)

    def test_sales_memos_tenant_isolation_cross_customer_hidden(self):
        self._complete_walk_in_order(self.customer_a, self.store_a, self.product_a, Decimal('1.000'))

        # Customer B accesses sales memos
        self.client.force_authenticate(user=self.customer_b)
        res = self.client.get('/orders/sales-memos/')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.json()['data']), 0)

    def test_multi_store_customer_spending_analytics(self):
        # Customer A: 2 visits at Store A (450 + 900 = 1350) and 1 visit at Store B (240)
        self._complete_walk_in_order(self.customer_a, self.store_a, self.product_a, Decimal('1.000'))  # 450
        self._complete_walk_in_order(self.customer_a, self.store_a, self.product_a, Decimal('2.000'))  # 900
        self._complete_walk_in_order(self.customer_a, self.store_b, self.product_b, Decimal('2.000'))  # 240

        self.client.force_authenticate(user=self.customer_a)
        res = self.client.get('/orders/customer-spending/')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        stats = res.json()['data']
        self.assertEqual(stats['total_spent'], '1590.00')
        self.assertEqual(stats['total_memos'], 3)
        self.assertEqual(stats['stores_visited_count'], 2)

        breakdown = stats['store_breakdown']
        self.assertEqual(len(breakdown), 2)

        # Store A has highest spend (1350) so it's first
        self.assertEqual(breakdown[0]['store_name'], "Green Valley Grocery")
        self.assertEqual(breakdown[0]['total_spent'], '1350.00')
        self.assertEqual(breakdown[0]['memo_count'], 2)

        # Store B has 240
        self.assertEqual(breakdown[1]['store_name'], "Sunrise Bakery")
        self.assertEqual(breakdown[1]['total_spent'], '240.00')
        self.assertEqual(breakdown[1]['memo_count'], 1)

        # Customer B has 0 spending
        self.client.force_authenticate(user=self.customer_b)
        res_b = self.client.get('/orders/customer-spending/')
        stats_b = res_b.json()['data']
        self.assertEqual(stats_b['total_spent'], '0.00')
        self.assertEqual(stats_b['total_memos'], 0)
        self.assertEqual(stats_b['stores_visited_count'], 0)
        self.assertEqual(len(stats_b['store_breakdown']), 0)
