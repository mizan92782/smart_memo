from decimal import Decimal
from django.test import TestCase
from users.models.user_mod import User
from stores.models.store_mod import Store
from products.models.product_mod import Product
from cards.models.card_mod import Card
from cards.repositories.card_repository import CardRepository
from cards.services.card_service import CardService
from inventory.services.inventory_service import InventoryService
from orders.models.order_mod import Order, OrderStatus, PaymentStatus
from orders.services.order_service import OrderService
from shared.enums.enums import UserRoleEnum


class OrderStateMachineTests(TestCase):
    def setUp(self):
        # Vendor & Store
        self.vendor = User.objects.create_user(
            email="order_v@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.store = Store.objects.create(vendor=self.vendor, name="Order Mart", delivery_fee=Decimal('30.00'))

        # Product with 50 units in stock
        self.product = Product.objects.create(store=self.store, name="Cooking Oil 1L", price=190.00, stock=0)
        InventoryService.receive_stock(self.store, self.product, Decimal('50.000'))

        # Customer & Draft Memo Card
        self.customer = User.objects.create_user(
            email="order_c@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )
        self.card = CardRepository.create_card(user=self.customer, store=self.store)
        CardService.add_product_to_card(self.card.id, self.product.id, Decimal('3.000'))

    def test_order_submission_reserves_stock(self):
        order = OrderService.submit_order_from_card(
            card=self.card,
            customer=self.customer,
            fulfillment_type='delivery',
            delivery_address='45 Lake View'
        )
        self.assertEqual(order.status, OrderStatus.SUBMITTED)
        self.assertEqual(order.subtotal, Decimal('570.00'))
        self.assertEqual(order.delivery_fee, Decimal('30.00'))
        self.assertEqual(order.total_amount, Decimal('600.00'))

        # Check stock balance: reserved=3, available=47
        balance = self.product.stock_balance
        balance.refresh_from_db()
        self.assertEqual(balance.reserved, Decimal('3.000'))
        self.assertEqual(balance.available, Decimal('47.000'))
        self.assertEqual(balance.on_hand, Decimal('50.000'))

        # Verify draft card is completed
        self.card.refresh_from_db()
        self.assertTrue(self.card.is_completed)

    def test_full_order_lifecycle_to_completion(self):
        # 1. Submit order
        order = OrderService.submit_order_from_card(self.card, self.customer)

        # 2. Accept order
        order = OrderService.accept_order(order, actor=self.vendor)
        self.assertEqual(order.status, OrderStatus.ACCEPTED)

        # 3. Fulfill order & collect cash
        order = OrderService.fulfill_order(order, actor=self.vendor, payment_collected=True)
        self.assertEqual(order.status, OrderStatus.COMPLETED)
        self.assertEqual(order.payment_status, PaymentStatus.COLLECTED)

        # Check inventory: on_hand=47, reserved=0, available=47
        balance = self.product.stock_balance
        balance.refresh_from_db()
        self.assertEqual(balance.on_hand, Decimal('47.000'))
        self.assertEqual(balance.reserved, Decimal('0.000'))

        # Check immutable Sales Memo generated
        self.assertTrue(hasattr(order, 'sales_memo'))
        self.assertEqual(order.sales_memo.total_amount, Decimal('570.00'))
        self.assertEqual(order.sales_memo.amount_paid, Decimal('570.00'))

    def test_cancel_order_releases_reserved_stock(self):
        order = OrderService.submit_order_from_card(self.card, self.customer)
        balance = self.product.stock_balance
        balance.refresh_from_db()
        self.assertEqual(balance.reserved, Decimal('3.000'))

        # Customer cancels
        order = OrderService.cancel_order(order, actor=self.customer)
        self.assertEqual(order.status, OrderStatus.CANCELLED)

        balance.refresh_from_db()
        self.assertEqual(balance.reserved, Decimal('0.000'))
        self.assertEqual(balance.available, Decimal('50.000'))

    def test_cannot_fulfill_cancelled_order(self):
        order = OrderService.submit_order_from_card(self.card, self.customer)
        OrderService.cancel_order(order, actor=self.customer)
        with self.assertRaises(ValueError):
            OrderService.fulfill_order(order, actor=self.vendor)
