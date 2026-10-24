from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from users.models.user_mod import User
from stores.models.store_mod import Store
from products.models.product_mod import Product
from cards.repositories.card_repository import CardRepository
from cards.services.card_service import CardService
from inventory.services.inventory_service import InventoryService
from orders.services.order_service import OrderService
from orders.models.order_mod import OrderStatus
from notifications.models.notification_mod import Notification, NotificationType
from notifications.services.notification_service import NotificationService
from shared.enums.enums import UserRoleEnum


class NotificationUnitAndWorkflowTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Vendor & Store
        self.vendor = User.objects.create_user(
            email="vendor_notif@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.store = Store.objects.create(
            vendor=self.vendor, name="Notification Mart", delivery_fee=Decimal('20.00')
        )

        # Product with initial stock of 10 and low_stock_threshold of 5
        self.product = Product.objects.create(
            store=self.store, name="Rice 5kg", price=Decimal('350.00'), stock=0
        )
        balance = InventoryService.receive_stock(self.store, self.product, Decimal('10.000'))
        balance.low_stock_threshold = Decimal('5.000')
        balance.save(update_fields=['low_stock_threshold', 'updated_at'])
        self.product.refresh_from_db()


        # Customer & Draft Memo Card
        self.customer = User.objects.create_user(
            email="cust_notif@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )
        self.card = CardRepository.create_card(user=self.customer, store=self.store)
        CardService.add_product_to_card(self.card.id, self.product.id, Decimal('6.000'))

    def test_idempotent_notification_creation(self):
        notif1 = NotificationService.create_notification(
            recipient=self.customer,
            title="System Alert",
            message="Server maintenance soon.",
            idempotency_key="maint_2026_10"
        )
        notif2 = NotificationService.create_notification(
            recipient=self.customer,
            title="System Alert",
            message="Server maintenance soon.",
            idempotency_key="maint_2026_10"
        )
        self.assertEqual(notif1.id, notif2.id)
        self.assertEqual(Notification.objects.filter(recipient=self.customer).count(), 1)

    def test_order_submission_triggers_vendor_notification_and_low_stock_alert(self):
        # Customer orders 6 units, reducing available stock from 10 to 4 (<= 5 threshold)
        order = OrderService.submit_order_from_card(self.card, self.customer)

        vendor_notifs = Notification.objects.filter(recipient=self.vendor)
        # Should have 2 notifications: order submitted + low stock alert
        self.assertEqual(vendor_notifs.count(), 2)

        order_notif = vendor_notifs.filter(notification_type=NotificationType.ORDER_SUBMITTED).first()
        self.assertIsNotNone(order_notif)
        self.assertIn(order.order_number, order_notif.title)

        low_stock_notif = vendor_notifs.filter(notification_type=NotificationType.LOW_STOCK_ALERT).first()
        self.assertIsNotNone(low_stock_notif)
        self.assertIn("Rice", low_stock_notif.title)
        self.assertEqual(low_stock_notif.store, self.store)


    def test_order_status_transitions_notify_customer(self):
        order = OrderService.submit_order_from_card(self.card, self.customer)

        # 1. Vendor accepts order
        OrderService.accept_order(order, self.vendor)
        cust_notifs = Notification.objects.filter(recipient=self.customer)
        self.assertEqual(cust_notifs.count(), 1)
        self.assertEqual(cust_notifs.first().notification_type, NotificationType.ORDER_ACCEPTED)

        # 2. Vendor fulfills order
        OrderService.fulfill_order(order, self.vendor)
        cust_notifs = Notification.objects.filter(recipient=self.customer)
        self.assertEqual(cust_notifs.count(), 2)
        latest = cust_notifs.latest('created_at')
        self.assertEqual(latest.notification_type, NotificationType.ORDER_COMPLETED)

    def test_mark_as_read_and_unread_count_apis(self):
        notif = NotificationService.create_notification(
            recipient=self.customer,
            title="Welcome!",
            message="Thanks for signing up."
        )

        self.client.force_authenticate(user=self.customer)

        # Check unread count
        count_res = self.client.get('/notifications/unread-count/')
        self.assertEqual(count_res.status_code, 200)
        self.assertEqual(count_res.data['data']['unread_count'], 1)

        # Mark as read
        read_res = self.client.patch(f'/notifications/{notif.id}/read/')
        self.assertEqual(read_res.status_code, 200)
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)
        self.assertIsNotNone(notif.read_at)

        # Unread count now 0
        count_res2 = self.client.get('/notifications/unread-count/')
        self.assertEqual(count_res2.data['data']['unread_count'], 0)

    def test_mark_all_read_api(self):
        NotificationService.create_notification(self.customer, "N1", "M1")
        NotificationService.create_notification(self.customer, "N2", "M2")

        self.client.force_authenticate(user=self.customer)
        res = self.client.post('/notifications/mark-all-read/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['data']['marked_count'], 2)

        # Verify in DB
        self.assertEqual(Notification.objects.filter(recipient=self.customer, is_read=False).count(), 0)
