from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from users.models.user_mod import User
from shared.enums.enums import UserRoleEnum
from stores.models.store_mod import Store
from products.models.product_mod import Product
from categories.models.category_mod import Category
from orders.models.order_mod import Order, OrderStatus, FulfillmentType, PaymentStatus
from notifications.models.notification_mod import Notification


class DeliveryAssignmentTests(APITestCase):
    def setUp(self):
        # Users
        self.vendor = User.objects.create_user(
            email='vendor_da@example.com',
            password='Password123!',
            role=UserRoleEnum.VENDOR
        )
        self.vendor_b = User.objects.create_user(
            email='vendor_b_da@example.com',
            password='Password123!',
            role=UserRoleEnum.VENDOR
        )
        self.customer = User.objects.create_user(
            email='customer_da@example.com',
            password='Password123!',
            role=UserRoleEnum.CUSTOMER
        )

        # Stores
        self.store = Store.objects.create(
            vendor=self.vendor,
            name="Express Grocery",
            address="123 Delivery Road",
            is_active=True,
            is_verified=True,
            pickup_enabled=True,
            delivery_enabled=True,
            delivery_fee=Decimal('25.00')
        )
        self.category = Category.objects.create(store=self.store, name="Produce")
        self.product = Product.objects.create(
            store=self.store,
            category=self.category,
            name="Organic Bananas",
            price=Decimal('15.00'),
            sku="BAN-01",
            stock=Decimal('100.000'),
            is_active=True
        )

        # Active Delivery Order
        self.delivery_order = Order.objects.create(
            customer=self.customer,
            store=self.store,
            status=OrderStatus.PREPARING,
            fulfillment_type=FulfillmentType.DELIVERY,
            delivery_address="Flat 4B, Green Avenue, Dhaka",
            delivery_fee=Decimal('25.00'),
            subtotal=Decimal('60.00'),
            total_amount=Decimal('85.00')
        )

        # Active Pickup Order
        self.pickup_order = Order.objects.create(
            customer=self.customer,
            store=self.store,
            status=OrderStatus.PREPARING,
            fulfillment_type=FulfillmentType.PICKUP,
            subtotal=Decimal('60.00'),
            total_amount=Decimal('60.00')
        )

    def test_vendor_assign_delivery_driver_success(self):
        """Vendor assigns driver to a home delivery order successfully."""
        self.client.force_authenticate(user=self.vendor)
        eta = timezone.now() + timedelta(minutes=45)
        payload = {
            "driver_name": "Tariqul Islam",
            "driver_phone": "+8801812345678",
            "vehicle_type": "Motorbike",
            "tracking_notes": "Insulated food delivery bag #12",
            "estimated_delivery_time": eta.isoformat()
        }
        url = f"/orders/{self.delivery_order.id}/assign-delivery/"
        resp = self.client.post(url, payload, format='json')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['success'])
        order_data = resp.data['data']
        self.assertEqual(order_data['delivery_person_name'], 'Tariqul Islam')
        self.assertEqual(order_data['delivery_person_phone'], '+8801812345678')
        self.assertEqual(order_data['delivery_vehicle_type'], 'Motorbike')
        self.assertEqual(order_data['delivery_tracking_notes'], 'Insulated food delivery bag #12')
        self.assertIsNotNone(order_data['delivery_assigned_at'])

    def test_driver_details_exposed_in_order_serializer_for_customer(self):
        """Customer viewing their order can see assigned delivery driver contact info."""
        self.delivery_order.delivery_person_name = "Kamal Hossain"
        self.delivery_order.delivery_person_phone = "+8801700112233"
        self.delivery_order.delivery_vehicle_type = "Bicycle"
        self.delivery_order.delivery_assigned_at = timezone.now()
        self.delivery_order.save()

        self.client.force_authenticate(user=self.customer)
        resp = self.client.get(f"/orders/{self.delivery_order.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['delivery_person_name'], 'Kamal Hossain')
        self.assertEqual(resp.data['delivery_person_phone'], '+8801700112233')
        self.assertEqual(resp.data['delivery_vehicle_type'], 'Bicycle')

    def test_reject_assign_driver_to_pickup_order(self):
        """Driver assignment is rejected with 400 Bad Request on in-store pickup orders."""
        self.client.force_authenticate(user=self.vendor)
        payload = {
            "driver_name": "Tariqul Islam",
            "driver_phone": "+8801812345678"
        }
        url = f"/orders/{self.pickup_order.id}/assign-delivery/"
        resp = self.client.post(url, payload, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("home delivery orders", resp.data['message'])

    def test_reject_assign_driver_to_completed_or_cancelled_order(self):
        """Driver assignment is rejected on completed or cancelled orders."""
        self.client.force_authenticate(user=self.vendor)
        payload = {"driver_name": "Driver", "driver_phone": "+8801700000000"}

        # Completed
        self.delivery_order.status = OrderStatus.COMPLETED
        self.delivery_order.save()
        resp = self.client.post(f"/orders/{self.delivery_order.id}/assign-delivery/", payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

        # Cancelled
        self.delivery_order.status = OrderStatus.CANCELLED
        self.delivery_order.save()
        resp = self.client.post(f"/orders/{self.delivery_order.id}/assign-delivery/", payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cross_tenant_driver_assignment_blocked(self):
        """Vendor B and Customers cannot assign delivery drivers to Vendor A's orders."""
        payload = {"driver_name": "Rogue Driver", "driver_phone": "+8801999999999"}
        url = f"/orders/{self.delivery_order.id}/assign-delivery/"

        # Other vendor (Order is excluded from vendor B's queryset -> 404, or rejected with 403)
        self.client.force_authenticate(user=self.vendor_b)
        resp = self.client.post(url, payload, format='json')
        self.assertIn(resp.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

        # Customer (Order is in customer's queryset, but customer is forbidden from assigning drivers)
        self.client.force_authenticate(user=self.customer)
        resp = self.client.post(url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        # Unauthenticated
        self.client.force_authenticate(user=None)
        resp = self.client.post(url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_auto_dispatch_flag_advances_order_status(self):
        """Assigning driver with auto_dispatch=True transitions order to OUT_FOR_DELIVERY."""
        self.client.force_authenticate(user=self.vendor)
        self.assertEqual(self.delivery_order.status, OrderStatus.PREPARING)

        payload = {
            "driver_name": "Sabbir Rahman",
            "driver_phone": "+8801555555555",
            "auto_dispatch": True
        }
        url = f"/orders/{self.delivery_order.id}/assign-delivery/"
        resp = self.client.post(url, payload, format='json')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['data']['status'], OrderStatus.OUT_FOR_DELIVERY)
        self.delivery_order.refresh_from_db()
        self.assertEqual(self.delivery_order.status, OrderStatus.OUT_FOR_DELIVERY)
        self.assertIsNotNone(self.delivery_order.dispatched_at)

    def test_reassign_driver_while_out_for_delivery(self):
        """Vendor can reassign/update driver details while order is OUT_FOR_DELIVERY."""
        self.delivery_order.status = OrderStatus.OUT_FOR_DELIVERY
        self.delivery_order.delivery_person_name = "Original Driver"
        self.delivery_order.delivery_person_phone = "+8801111111111"
        self.delivery_order.save()

        self.client.force_authenticate(user=self.vendor)
        payload = {
            "driver_name": "Replacement Driver",
            "driver_phone": "+8801222222222",
            "tracking_notes": "Driver replacement due to vehicle puncture."
        }
        resp = self.client.post(f"/orders/{self.delivery_order.id}/assign-delivery/", payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['data']['delivery_person_name'], 'Replacement Driver')
        self.assertEqual(resp.data['data']['delivery_person_phone'], '+8801222222222')

    def test_notification_generated_for_customer_with_driver_details(self):
        """Customer notification is created containing driver contact information."""
        self.client.force_authenticate(user=self.vendor)
        payload = {
            "driver_name": "Mizan Driver",
            "driver_phone": "+8801999888777",
            "vehicle_type": "Motorcycle"
        }
        resp = self.client.post(f"/orders/{self.delivery_order.id}/assign-delivery/", payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        notif = Notification.objects.filter(recipient=self.customer).order_by('-created_at').first()
        self.assertIsNotNone(notif)
        self.assertIn("Mizan Driver", notif.message)
        self.assertIn("+8801999888777", notif.message)
        self.assertIn("Motorcycle", notif.message)

    def test_blank_driver_name_or_phone_rejected(self):
        """Empty driver name or phone fails serializer validation."""
        self.client.force_authenticate(user=self.vendor)
        url = f"/orders/{self.delivery_order.id}/assign-delivery/"

        resp = self.client.post(url, {"driver_name": "  ", "driver_phone": "+8801000000000"}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

        resp2 = self.client.post(url, {"driver_name": "Valid Driver", "driver_phone": "   "}, format='json')
        self.assertEqual(resp2.status_code, status.HTTP_400_BAD_REQUEST)
