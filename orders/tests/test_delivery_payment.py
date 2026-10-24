from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from users.models.user_mod import User
from users.models.profile_mod import Profile
from stores.models.store_mod import Store
from products.models.product_mod import Product
from cards.repositories.card_repository import CardRepository
from cards.services.card_service import CardService
from inventory.services.inventory_service import InventoryService
from orders.models.order_mod import Order, OrderStatus, PaymentStatus, FulfillmentType
from orders.services.order_service import OrderService
from shared.enums.enums import UserRoleEnum


class DeliveryAndPaymentLifecycleTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Vendor & Store with $50 delivery fee and $100 min order amount
        self.vendor = User.objects.create_user(
            email="vendor_dp@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.store = Store.objects.create(
            vendor=self.vendor,
            name="Supermart Express",
            delivery_enabled=True,
            pickup_enabled=True,
            delivery_fee=Decimal('50.00'),
            min_order_amount=Decimal('100.00')
        )

        # Products with inventory stock
        self.product = Product.objects.create(
            store=self.store, name="Premium Basmati Rice", price=Decimal('60.00'), stock=0
        )
        balance = InventoryService.receive_stock(self.store, self.product, Decimal('50.000'))
        balance.low_stock_threshold = Decimal('5.000')
        balance.save(update_fields=['low_stock_threshold', 'updated_at'])

        # Customer with profile phone
        self.customer = User.objects.create_user(
            email="cust_dp@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )
        profile, _ = Profile.objects.get_or_create(user=self.customer)
        profile.phone_number = "+8801712345678"
        profile.save()
        self.customer.refresh_from_db()


    def test_minimum_order_amount_enforced_for_delivery(self):
        # 1 item of $60 is below $100 min order amount for delivery
        card = CardRepository.create_card(user=self.customer, store=self.store)
        CardService.add_product_to_card(card.id, self.product.id, Decimal('1.000'))

        with self.assertRaises(ValueError) as ctx:
            OrderService.submit_order_from_card(
                card=card, customer=self.customer, fulfillment_type=FulfillmentType.DELIVERY
            )
        self.assertIn("Minimum order amount for delivery", str(ctx.exception))

    def test_unsupported_fulfillment_methods_rejected(self):
        self.store.delivery_enabled = False
        self.store.save(update_fields=['delivery_enabled'])

        card = CardRepository.create_card(user=self.customer, store=self.store)
        CardService.add_product_to_card(card.id, self.product.id, Decimal('2.000'))

        with self.assertRaises(ValueError) as ctx:
            OrderService.submit_order_from_card(
                card=card, customer=self.customer, fulfillment_type=FulfillmentType.DELIVERY
            )
        self.assertIn("does not support home delivery", str(ctx.exception))

    def test_phone_snapshot_and_fulfillment_with_cod_pending(self):
        # 2 items of $60 = $120 (>= $100 min)
        card = CardRepository.create_card(user=self.customer, store=self.store)
        CardService.add_product_to_card(card.id, self.product.id, Decimal('2.000'))

        order = OrderService.submit_order_from_card(
            card=card,
            customer=self.customer,
            fulfillment_type=FulfillmentType.DELIVERY,
            delivery_address="House 12, Road 5, Banani"
        )
        self.assertEqual(order.customer_phone_snapshot, "+8801712345678")
        self.assertEqual(order.payment_status, PaymentStatus.PENDING)

        # Accept order
        OrderService.accept_order(order, self.vendor)

        # Fulfill order with payment NOT yet collected (rider dispatched, COD pending)
        order = OrderService.fulfill_order(order, self.vendor, payment_collected=False)
        self.assertEqual(order.status, OrderStatus.COMPLETED)
        self.assertEqual(order.payment_status, PaymentStatus.PENDING)
        self.assertIsNone(order.paid_at)
        self.assertEqual(order.sales_memo.amount_paid, Decimal('0.00'))

        # Rider/Cashier collects COD payment via collect-payment endpoint
        self.client.force_authenticate(user=self.vendor)
        res = self.client.post(f'/orders/{order.id}/collect-payment/')
        self.assertEqual(res.status_code, 200)

        order.refresh_from_db()
        self.assertEqual(order.payment_status, PaymentStatus.COLLECTED)
        self.assertIsNotNone(order.paid_at)
        self.assertEqual(order.payment_collected_by, self.vendor)
        self.assertEqual(order.sales_memo.amount_paid, order.total_amount)

    def test_unauthorized_user_cannot_collect_payment(self):
        card = CardRepository.create_card(user=self.customer, store=self.store)
        CardService.add_product_to_card(card.id, self.product.id, Decimal('2.000'))
        order = OrderService.submit_order_from_card(card, self.customer)

        # Customer tries to call collect-payment
        self.client.force_authenticate(user=self.customer)
        res = self.client.post(f'/orders/{order.id}/collect-payment/')
        self.assertEqual(res.status_code, 403)
