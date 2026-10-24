from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from users.models.user_mod import User
from stores.models.store_mod import Store
from products.models.product_mod import Product
from cards.models.card_mod import Card
from cards.repositories.card_repository import CardRepository
from cards.services.card_service import CardService
from inventory.services.inventory_service import InventoryService
from orders.models.order_mod import Order, OrderStatus, FulfillmentType
from orders.services.order_service import OrderService
from notifications.models.notification_mod import Notification, NotificationType
from shared.enums.enums import UserRoleEnum


class OrderFulfillmentPipelineTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Vendor & Store
        self.vendor = User.objects.create_user(
            email="vendor_pipe@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.store = Store.objects.create(
            vendor=self.vendor,
            name="Pipeline Store",
            delivery_fee=Decimal('25.00'),
            pickup_enabled=True,
            delivery_enabled=True
        )

        # Inventory
        self.product = Product.objects.create(store=self.store, name="Fresh Milk 1L", price=80.00, stock=0)
        InventoryService.receive_stock(self.store, self.product, Decimal('20.000'))

        # Customer & Draft Card
        self.customer = User.objects.create_user(
            email="customer_pipe@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )

        # Other Vendor (for cross-tenant IDOR checks)
        self.other_vendor = User.objects.create_user(
            email="other_v@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )

    def _create_submitted_order(self, fulfillment_type='pickup'):
        card = CardRepository.create_card(user=self.customer, store=self.store)
        CardService.add_product_to_card(card.id, self.product.id, Decimal('2.000'))
        return OrderService.submit_order_from_card(
            card=card,
            customer=self.customer,
            fulfillment_type=fulfillment_type,
            delivery_address="123 Dhaka Road" if fulfillment_type == 'delivery' else ""
        )

    def test_vendor_prepare_and_dispatch_pickup_pipeline(self):
        order = self._create_submitted_order(fulfillment_type='pickup')
        self.assertEqual(order.status, OrderStatus.SUBMITTED)

        # 1. Accept
        order = OrderService.accept_order(order, actor=self.vendor)
        self.assertEqual(order.status, OrderStatus.ACCEPTED)
        self.assertIsNotNone(order.accepted_at)

        # 2. Start Preparing
        order = OrderService.start_preparing(order, actor=self.vendor)
        self.assertEqual(order.status, OrderStatus.PREPARING)
        self.assertIsNotNone(order.preparing_at)

        # 3. Ready for Pickup
        order = OrderService.dispatch_order(order, actor=self.vendor)
        self.assertEqual(order.status, OrderStatus.READY_FOR_PICKUP)
        self.assertIsNotNone(order.dispatched_at)

        # Check notification dispatched for ready_for_pickup
        notif = Notification.objects.filter(
            recipient=self.customer,
            notification_type=NotificationType.ORDER_READY_FOR_PICKUP
        ).first()
        self.assertIsNotNone(notif)
        self.assertIn("ready_for_pickup", notif.message)

        # 4. Fulfill & complete
        order = OrderService.fulfill_order(order, actor=self.vendor)
        self.assertEqual(order.status, OrderStatus.COMPLETED)
        self.assertIsNotNone(order.completed_at)

    def test_vendor_dispatch_home_delivery_sets_out_for_delivery(self):
        order = self._create_submitted_order(fulfillment_type='delivery')
        order = OrderService.accept_order(order, actor=self.vendor)
        order = OrderService.start_preparing(order, actor=self.vendor)

        order = OrderService.dispatch_order(order, actor=self.vendor)
        self.assertEqual(order.status, OrderStatus.OUT_FOR_DELIVERY)
        self.assertIsNotNone(order.dispatched_at)

        # Notification for out_for_delivery
        notif = Notification.objects.filter(
            recipient=self.customer,
            notification_type=NotificationType.ORDER_OUT_FOR_DELIVERY
        ).first()
        self.assertIsNotNone(notif)

    def test_customer_cannot_cancel_order_in_preparation_or_transit(self):
        order = self._create_submitted_order(fulfillment_type='pickup')
        order = OrderService.accept_order(order, actor=self.vendor)
        order = OrderService.start_preparing(order, actor=self.vendor)

        # Customer attempts to cancel order in PREPARING
        with self.assertRaises(ValueError) as ctx:
            OrderService.cancel_order(order, actor=self.customer)
        self.assertIn("Customers cannot cancel an order once preparation or fulfillment has started", str(ctx.exception))

    def test_vendor_can_cancel_during_preparation_and_restore_stock(self):
        order = self._create_submitted_order(fulfillment_type='pickup')
        order = OrderService.accept_order(order, actor=self.vendor)
        order = OrderService.start_preparing(order, actor=self.vendor)

        balance = self.product.stock_balance
        balance.refresh_from_db()
        self.assertEqual(balance.reserved, Decimal('2.000'))

        # Vendor rejects/cancels
        order = OrderService.cancel_order(order, actor=self.vendor, reason="Kitchen equipment malfunction")
        self.assertEqual(order.status, OrderStatus.REJECTED)

        balance.refresh_from_db()
        self.assertEqual(balance.reserved, Decimal('0.000'))
        self.assertEqual(balance.available, Decimal('20.000'))

    def test_api_prepare_and_dispatch_endpoints_and_idor_prevention(self):
        order = self._create_submitted_order(fulfillment_type='pickup')
        OrderService.accept_order(order, actor=self.vendor)

        # 1. Other vendor cannot prepare order (403 IDOR or 404 Not Found)
        self.client.force_authenticate(user=self.other_vendor)
        res = self.client.post(f"/orders/{order.id}/prepare/")
        self.assertIn(res.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

        # 2. Store vendor prepares order
        self.client.force_authenticate(user=self.vendor)
        res = self.client.post(f"/orders/{order.id}/prepare/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['data']['status'], 'preparing')

        # 3. Store vendor dispatches order
        res = self.client.post(f"/orders/{order.id}/dispatch/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['data']['status'], 'ready_for_pickup')

        # 4. Customer attempts to cancel via API (should fail with 400)
        self.client.force_authenticate(user=self.customer)
        res = self.client.post(f"/orders/{order.id}/cancel/")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Customers cannot cancel", res.data.get('message', ''))
