from django.test import TestCase
from rest_framework.test import APIClient
from users.models.user_mod import User
from stores.models.store_mod import Store
from notifications.models.notification_mod import Notification
from notifications.services.notification_service import NotificationService
from shared.enums.enums import UserRoleEnum


class NotificationSecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # User A
        self.user_a = User.objects.create_user(
            email="user_a@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )
        self.notif_a = NotificationService.create_notification(
            recipient=self.user_a, title="Private Notice A", message="Confidential details A"
        )

        # User B
        self.user_b = User.objects.create_user(
            email="user_b@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )
        self.notif_b = NotificationService.create_notification(
            recipient=self.user_b, title="Private Notice B", message="Confidential details B"
        )

        # Vendor A
        self.vendor_a = User.objects.create_user(
            email="vendor_sec_a@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.store_a = Store.objects.create(vendor=self.vendor_a, name="Vendor A Mart")
        self.notif_vendor_a = NotificationService.create_notification(
            recipient=self.vendor_a, store=self.store_a, title="Vendor A Alert", message="Stock warning A"
        )

    def test_user_a_cannot_view_user_b_notifications(self):
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get('/notifications/')
        self.assertEqual(response.status_code, 200)

        titles = [n['title'] for n in response.data['data']]
        self.assertIn("Private Notice A", titles)
        self.assertNotIn("Private Notice B", titles)
        self.assertNotIn("Vendor A Alert", titles)

    def test_user_a_cannot_mark_user_b_notification_as_read(self):
        self.client.force_authenticate(user=self.user_a)
        response = self.client.patch(f'/notifications/{self.notif_b.id}/read/')
        self.assertEqual(response.status_code, 403)
        self.notif_b.refresh_from_db()
        self.assertFalse(self.notif_b.is_read)

    def test_unauthenticated_requests_are_denied(self):
        # Listing
        res_list = self.client.get('/notifications/')
        self.assertIn(res_list.status_code, [401, 403])

        # Read state mutation
        res_patch = self.client.patch(f'/notifications/{self.notif_a.id}/read/')
        self.assertIn(res_patch.status_code, [401, 403])

        # Mark all read
        res_all = self.client.post('/notifications/mark-all-read/')
        self.assertIn(res_all.status_code, [401, 403])
