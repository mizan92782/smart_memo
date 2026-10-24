from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.exceptions import PermissionDenied

from shared.enums.enums import UserRoleEnum
from stores.models.store_mod import Store
from products.models.product_mod import Product
from inventory.services.inventory_service import InventoryService
from orders.models.order_mod import Order, OrderStatus, FulfillmentType, PaymentStatus
from orders.services.order_service import OrderService
from audit.models.audit_mod import AuditLog, AuditAction
from audit.services.audit_service import AuditService

User = get_user_model()


class AuditTrailTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Users
        self.staff_user = User.objects.create_user(
            email='admin_audit@example.com',
            password='Password123!',
            role=UserRoleEnum.STAFF,
            is_staff=True
        )

        self.vendor_a = User.objects.create_user(
            email='vendor_a_audit@example.com',
            password='Password123!',
            role=UserRoleEnum.VENDOR
        )

        self.vendor_b = User.objects.create_user(
            email='vendor_b_audit@example.com',
            password='Password123!',
            role=UserRoleEnum.VENDOR
        )

        self.customer = User.objects.create_user(
            email='customer_audit@example.com',
            password='Password123!',
            role=UserRoleEnum.CUSTOMER
        )

        # Stores
        self.store_a = Store.objects.create(
            name="Vendor A Supermart",
            vendor=self.vendor_a,
            latitude=23.8103,
            longitude=90.4125,
            is_verified=True,
            is_active=True
        )

        self.store_b = Store.objects.create(
            name="Vendor B Electronics",
            vendor=self.vendor_b,
            latitude=23.7900,
            longitude=90.4000,
            is_verified=True,
            is_active=True
        )

        # Products
        self.product_a = Product.objects.create(
            store=self.store_a,
            name="Audit Milk",
            price=Decimal("50.00"),
            stock=Decimal("100.000"),
            is_active=True
        )

    def test_audit_log_immutability_update_fails(self):
        log = AuditService.log(
            action=AuditAction.STORE_VERIFIED,
            target_model="Store",
            target_id=self.store_a.id,
            actor=self.staff_user,
            store=self.store_a,
            details={"note": "Initial approval"}
        )
        self.assertIsNotNone(log.id)

        # Updating must raise PermissionDenied
        log.action = "TAMPERED_ACTION"
        with self.assertRaises(PermissionDenied):
            log.save()

    def test_audit_log_immutability_delete_fails(self):
        log = AuditService.log(
            action=AuditAction.STORE_VERIFIED,
            target_model="Store",
            target_id=self.store_a.id,
            actor=self.staff_user,
            store=self.store_a
        )
        with self.assertRaises(PermissionDenied):
            log.delete()

    def test_store_verification_creates_audit_log(self):
        self.client.force_authenticate(user=self.staff_user)
        store = Store.objects.create(
            name="Pending Verification Store",
            vendor=self.vendor_a,
            latitude=23.80,
            longitude=90.40,
            is_verified=False
        )
        resp = self.client.post(f"/stores/{store.id}/verify/", {"notes": "Inspected trade license."})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        log = AuditLog.objects.filter(
            action=AuditAction.STORE_VERIFIED,
            target_id=str(store.id)
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.actor, self.staff_user)
        self.assertEqual(log.details.get("notes"), "Inspected trade license.")

    def test_store_suspension_and_activation_creates_audit_logs(self):
        self.client.force_authenticate(user=self.staff_user)
        # Suspend
        resp_suspend = self.client.post(f"/stores/{self.store_a.id}/suspend/", {"reason": "Policy violation."})
        self.assertEqual(resp_suspend.status_code, status.HTTP_200_OK)

        suspend_log = AuditLog.objects.filter(
            action=AuditAction.STORE_SUSPENDED,
            target_id=str(self.store_a.id)
        ).first()
        self.assertIsNotNone(suspend_log)
        self.assertEqual(suspend_log.actor, self.staff_user)
        self.assertEqual(suspend_log.details.get("reason"), "Policy violation.")

        # Reactivate
        resp_activate = self.client.post(f"/stores/{self.store_a.id}/activate/")
        self.assertEqual(resp_activate.status_code, status.HTTP_200_OK)

        activate_log = AuditLog.objects.filter(
            action=AuditAction.STORE_ACTIVATED,
            target_id=str(self.store_a.id)
        ).first()
        self.assertIsNotNone(activate_log)
        self.assertEqual(activate_log.actor, self.staff_user)

    def test_inventory_manual_adjustment_creates_audit_log(self):
        InventoryService.adjust_stock(
            store=self.store_a,
            product=self.product_a,
            quantity=Decimal("15.000"),
            actor=self.vendor_a,
            notes="Physical inventory recount found extra stock"
        )

        log = AuditLog.objects.filter(
            action=AuditAction.INVENTORY_ADJUSTED,
            store=self.store_a
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.actor, self.vendor_a)
        self.assertEqual(log.details.get("adjustment_qty"), "15.000")
        self.assertEqual(log.details.get("notes"), "Physical inventory recount found extra stock")

    def test_order_cancellation_creates_audit_log(self):
        order = Order.objects.create(
            order_number="ORD-AUDIT-001",
            store=self.store_a,
            customer=self.customer,
            subtotal=Decimal("100.00"),
            delivery_fee=Decimal("0.00"),
            total_amount=Decimal("100.00"),
            status=OrderStatus.SUBMITTED,
            fulfillment_type=FulfillmentType.PICKUP
        )

        OrderService.cancel_order(order, actor=self.vendor_a, reason="Out of stock ingredient")

        log = AuditLog.objects.filter(
            action=AuditAction.ORDER_CANCELLED,
            target_id=str(order.id)
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.actor, self.vendor_a)
        self.assertEqual(log.details.get("reason"), "Out of stock ingredient")

    def test_order_payment_collected_creates_audit_log(self):
        order = Order.objects.create(
            order_number="ORD-AUDIT-002",
            store=self.store_a,
            customer=self.customer,
            subtotal=Decimal("75.00"),
            delivery_fee=Decimal("10.00"),
            total_amount=Decimal("85.00"),
            status=OrderStatus.ACCEPTED,
            fulfillment_type=FulfillmentType.DELIVERY,
            payment_status=PaymentStatus.PENDING
        )

        OrderService.collect_payment(order, collector=self.vendor_a)

        log = AuditLog.objects.filter(
            action=AuditAction.ORDER_PAYMENT_COLLECTED,
            target_id=str(order.id)
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.actor, self.vendor_a)
        self.assertEqual(log.details.get("amount"), "85.00")

    def test_password_change_creates_audit_log(self):
        self.client.force_authenticate(user=self.customer)
        resp = self.client.post("/users/change-password/", {
            "old_password": "Password123!",
            "new_password": "NewSecretPassword456!"
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        log = AuditLog.objects.filter(
            action=AuditAction.PASSWORD_CHANGED,
            target_id=str(self.customer.id)
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.actor, self.customer)
        self.assertEqual(log.details.get("email"), self.customer.email)

    def test_customer_cannot_access_audit_logs(self):
        self.client.force_authenticate(user=self.customer)
        resp = self.client.get("/audit/logs/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_access_audit_logs(self):
        resp = self.client.get("/audit/logs/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_vendor_isolation_on_audit_logs(self):
        # Create log for Store A
        AuditService.log(
            action=AuditAction.STORE_VERIFIED,
            target_model="Store",
            target_id=self.store_a.id,
            actor=self.staff_user,
            store=self.store_a,
            details={"store": "A"}
        )
        # Create log for Store B
        AuditService.log(
            action=AuditAction.STORE_VERIFIED,
            target_model="Store",
            target_id=self.store_b.id,
            actor=self.staff_user,
            store=self.store_b,
            details={"store": "B"}
        )

        # Vendor A queries /audit/logs/
        self.client.force_authenticate(user=self.vendor_a)
        resp = self.client.get("/audit/logs/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get("data", resp.data.get("results", []))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["store"], self.store_a.id)

        # Vendor A attempts to filter by Vendor B's store -> 403 Forbidden
        resp_other = self.client.get(f"/audit/logs/?store_id={self.store_b.id}")
        self.assertEqual(resp_other.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_can_view_all_audit_logs_and_filter(self):
        AuditService.log(
            action=AuditAction.STORE_VERIFIED,
            target_model="Store",
            target_id=self.store_a.id,
            actor=self.staff_user,
            store=self.store_a
        )
        AuditService.log(
            action=AuditAction.STORE_SUSPENDED,
            target_model="Store",
            target_id=self.store_b.id,
            actor=self.staff_user,
            store=self.store_b
        )

        self.client.force_authenticate(user=self.staff_user)
        # All logs
        resp_all = self.client.get("/audit/logs/")
        self.assertEqual(resp_all.status_code, status.HTTP_200_OK)
        results_all = resp_all.data.get("data", resp_all.data.get("results", []))
        self.assertGreaterEqual(len(results_all), 2)

        # Filter by action
        resp_filter = self.client.get(f"/audit/logs/?action={AuditAction.STORE_SUSPENDED}")
        self.assertEqual(resp_filter.status_code, status.HTTP_200_OK)
        results_filter = resp_filter.data.get("data", resp_filter.data.get("results", []))
        self.assertEqual(len(results_filter), 1)
        self.assertEqual(results_filter[0]["action"], AuditAction.STORE_SUSPENDED)

    def test_audit_logs_disallow_mutations_via_api(self):
        self.client.force_authenticate(user=self.staff_user)
        resp_post = self.client.post("/audit/logs/", {"action": "HACK"})
        self.assertEqual(resp_post.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        log = AuditService.log(
            action=AuditAction.STORE_VERIFIED,
            target_model="Store",
            target_id=self.store_a.id,
            actor=self.staff_user,
            store=self.store_a
        )
        resp_delete = self.client.delete(f"/audit/logs/{log.id}/")
        self.assertEqual(resp_delete.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
