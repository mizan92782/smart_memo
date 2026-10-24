from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework import status

from shared.enums.enums import UserRoleEnum
from stores.models.store_mod import Store
from stores.models.review_mod import StoreReview
from orders.models.order_mod import Order, OrderStatus, FulfillmentType, PaymentStatus, PaymentMethod

User = get_user_model()


class StoreReviewsTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

        # Users
        self.customer_a = User.objects.create_user(
            email='customer_a_rev@example.com',
            password='Password123!',
            role=UserRoleEnum.CUSTOMER
        )
        self.customer_b = User.objects.create_user(
            email='customer_b_rev@example.com',
            password='Password123!',
            role=UserRoleEnum.CUSTOMER
        )
        self.vendor_a = User.objects.create_user(
            email='vendor_a_rev@example.com',
            password='Password123!',
            role=UserRoleEnum.VENDOR
        )
        self.vendor_b = User.objects.create_user(
            email='vendor_b_rev@example.com',
            password='Password123!',
            role=UserRoleEnum.VENDOR
        )

        # Store
        self.store = Store.objects.create(
            name="Organic Greens & Groceries",
            vendor=self.vendor_a,
            latitude=23.8103,
            longitude=90.4125,
            is_active=True,
            is_verified=True
        )

        # Completed Orders
        self.completed_order_a = Order.objects.create(
            customer=self.customer_a,
            store=self.store,
            status=OrderStatus.COMPLETED,
            fulfillment_type=FulfillmentType.DELIVERY,
            delivery_address="House 1, Road 2",
            subtotal=Decimal("200.00"),
            total_amount=Decimal("230.00"),
            payment_status=PaymentStatus.COLLECTED,
            payment_method=PaymentMethod.COD,
            order_number="ORD-REV-001"
        )
        self.completed_order_b = Order.objects.create(
            customer=self.customer_b,
            store=self.store,
            status=OrderStatus.COMPLETED,
            fulfillment_type=FulfillmentType.PICKUP,
            subtotal=Decimal("150.00"),
            total_amount=Decimal("150.00"),
            payment_status=PaymentStatus.COLLECTED,
            payment_method=PaymentMethod.COD,
            order_number="ORD-REV-002"
        )

        # Incomplete Order (in progress)
        self.pending_order_a = Order.objects.create(
            customer=self.customer_a,
            store=self.store,
            status=OrderStatus.PREPARING,
            fulfillment_type=FulfillmentType.DELIVERY,
            delivery_address="House 1, Road 2",
            subtotal=Decimal("100.00"),
            total_amount=Decimal("130.00"),
            payment_status=PaymentStatus.PENDING,
            order_number="ORD-REV-003"
        )

    def tearDown(self):
        cache.clear()

    def test_verified_customer_review_creation_updates_store_rating(self):
        self.client.force_authenticate(user=self.customer_a)
        payload = {
            "order_id": self.completed_order_a.id,
            "rating": 5,
            "comment": "Exceptional fresh greens and super fast delivery!"
        }
        resp = self.client.post(f"/stores/{self.store.id}/reviews/", payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.data["data"]

        self.assertEqual(data["rating"], 5)
        self.assertEqual(data["comment"], "Exceptional fresh greens and super fast delivery!")
        self.assertTrue(data["is_verified_purchase"])

        # Check store rating fields recalculated
        self.store.refresh_from_db()
        self.assertEqual(self.store.average_rating, Decimal("5.00"))
        self.assertEqual(self.store.total_reviews, 1)

    def test_subsequent_review_recalculates_average_rating(self):
        # Customer A leaves 5 stars
        self.client.force_authenticate(user=self.customer_a)
        self.client.post(f"/stores/{self.store.id}/reviews/", {
            "order_id": self.completed_order_a.id,
            "rating": 5,
            "comment": "Perfect!"
        }, format='json')

        # Customer B leaves 3 stars
        self.client.force_authenticate(user=self.customer_b)
        resp_b = self.client.post(f"/stores/{self.store.id}/reviews/", {
            "order_id": self.completed_order_b.id,
            "rating": 3,
            "comment": "Decent quality."
        }, format='json')
        self.assertEqual(resp_b.status_code, status.HTTP_201_CREATED)

        # Average = (5 + 3) / 2 = 4.00, Total = 2
        self.store.refresh_from_db()
        self.assertEqual(self.store.average_rating, Decimal("4.00"))
        self.assertEqual(self.store.total_reviews, 2)

    def test_customer_cannot_review_uncompleted_order(self):
        self.client.force_authenticate(user=self.customer_a)
        resp = self.client.post(f"/stores/{self.store.id}/reviews/", {
            "order_id": self.pending_order_a.id,
            "rating": 4,
            "comment": "Looks good so far"
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("after your order has been completed", resp.data["message"])

    def test_customer_cannot_review_other_customers_order(self):
        # Customer B attempts to review Customer A's completed order
        self.client.force_authenticate(user=self.customer_b)
        resp = self.client.post(f"/stores/{self.store.id}/reviews/", {
            "order_id": self.completed_order_a.id,
            "rating": 1,
            "comment": "Fake negative review"
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("where you have placed an order", resp.data["message"])

    def test_customer_cannot_review_same_order_twice(self):
        self.client.force_authenticate(user=self.customer_a)
        # First review
        resp1 = self.client.post(f"/stores/{self.store.id}/reviews/", {
            "order_id": self.completed_order_a.id,
            "rating": 5
        }, format='json')
        self.assertEqual(resp1.status_code, status.HTTP_201_CREATED)

        # Second review on same order
        resp2 = self.client.post(f"/stores/{self.store.id}/reviews/", {
            "order_id": self.completed_order_a.id,
            "rating": 4
        }, format='json')
        self.assertEqual(resp2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already reviewed this completed order", resp2.data["message"])

    def test_rating_bounds_validation(self):
        self.client.force_authenticate(user=self.customer_a)
        # Rating 0 (invalid)
        resp_low = self.client.post(f"/stores/{self.store.id}/reviews/", {
            "order_id": self.completed_order_a.id,
            "rating": 0
        }, format='json')
        self.assertEqual(resp_low.status_code, status.HTTP_400_BAD_REQUEST)

        # Rating 6 (invalid)
        resp_high = self.client.post(f"/stores/{self.store.id}/reviews/", {
            "order_id": self.completed_order_a.id,
            "rating": 6
        }, format='json')
        self.assertEqual(resp_high.status_code, status.HTTP_400_BAD_REQUEST)

    def test_vendor_reply_to_review(self):
        # Customer creates review
        self.client.force_authenticate(user=self.customer_a)
        resp_rev = self.client.post(f"/stores/{self.store.id}/reviews/", {
            "order_id": self.completed_order_a.id,
            "rating": 5,
            "comment": "Love the organic apples!"
        }, format='json')
        review_id = resp_rev.data["data"]["id"]

        # Store Vendor replies
        self.client.force_authenticate(user=self.vendor_a)
        resp_reply = self.client.post(f"/stores/reviews/{review_id}/reply/", {
            "reply": "Thank you so much Alice, we appreciate your patronage!"
        }, format='json')
        self.assertEqual(resp_reply.status_code, status.HTTP_200_OK)
        data = resp_reply.data["data"]
        self.assertEqual(data["vendor_reply"], "Thank you so much Alice, we appreciate your patronage!")
        self.assertIsNotNone(data["vendor_replied_at"])

    def test_other_vendor_cannot_reply_to_store_review(self):
        # Customer creates review
        self.client.force_authenticate(user=self.customer_a)
        resp_rev = self.client.post(f"/stores/{self.store.id}/reviews/", {
            "order_id": self.completed_order_a.id,
            "rating": 5
        }, format='json')
        review_id = resp_rev.data["data"]["id"]

        # Vendor B tries to reply to Store A review
        self.client.force_authenticate(user=self.vendor_b)
        resp_reply = self.client.post(f"/stores/reviews/{review_id}/reply/", {
            "reply": "Imposter reply"
        }, format='json')
        self.assertEqual(resp_reply.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Only the store vendor can reply", resp_reply.data["message"])

    def test_customer_delete_review_recalculates_store_rating(self):
        # Customer A reviews (5 stars)
        self.client.force_authenticate(user=self.customer_a)
        resp_rev = self.client.post(f"/stores/{self.store.id}/reviews/", {
            "order_id": self.completed_order_a.id,
            "rating": 5
        }, format='json')
        review_id = resp_rev.data["data"]["id"]

        self.store.refresh_from_db()
        self.assertEqual(self.store.total_reviews, 1)

        # Customer A deletes their review
        resp_del = self.client.delete(f"/stores/reviews/{review_id}/")
        self.assertEqual(resp_del.status_code, status.HTTP_200_OK)

        self.store.refresh_from_db()
        self.assertEqual(self.store.total_reviews, 0)
        self.assertEqual(self.store.average_rating, Decimal("0.00"))

    def test_public_can_view_store_reviews(self):
        # Authenticated customer writes review
        self.client.force_authenticate(user=self.customer_a)
        self.client.post(f"/stores/{self.store.id}/reviews/", {
            "order_id": self.completed_order_a.id,
            "rating": 5,
            "comment": "Publicly visible review!"
        }, format='json')

        # Anonymous user views reviews
        self.client.logout()
        resp = self.client.get(f"/stores/{self.store.id}/reviews/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data.get("data", resp.data.get("results", []))
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["rating"], 5)
        self.assertEqual(data[0]["comment"], "Publicly visible review!")
