from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from stores.models.store_mod import Store
from products.models.product_mod import Product
from inventory.models.inventory_mod import StockBalance, StockLedgerEntry, StockMovementType
from orders.models.order_mod import Order, OrderItem, OrderStatus, PaymentStatus, FulfillmentType
from orders.models.return_mod import OrderReturn, OrderReturnItem, ReturnStatus, ReturnReason
from stores.models.loyalty_mod import StoreLoyaltyProgram, LoyaltyProgramType, CustomerStoreLoyalty

User = get_user_model()


class OrderReturnsTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Vendor 1 and Store 1
        self.vendor = User.objects.create_user(
            email="vendor1@example.com",
            password="password123",
            role="vendor"
        )
        self.store = Store.objects.create(
            name="Super Grocers",
            vendor=self.vendor,
            is_active=True,
            is_verified=True,
            delivery_enabled=True,
            pickup_enabled=True
        )

        # Vendor 2 and Store 2 (for tenant isolation tests)
        self.other_vendor = User.objects.create_user(
            email="other_vendor@example.com",
            password="password123",
            role="vendor"
        )
        self.other_store = Store.objects.create(
            name="Rival Grocers",
            vendor=self.other_vendor,
            is_active=True,
            is_verified=True
        )

        # Customer 1 and Customer 2
        self.customer = User.objects.create_user(
            email="customer1@example.com",
            password="password123",
            role="customer"
        )
        self.other_customer = User.objects.create_user(
            email="customer2@example.com",
            password="password123",
            role="customer"
        )

        # Product and Stock Balance
        self.product = Product.objects.create(
            name="Organic Milk 1L",
            store=self.store,
            price=Decimal('50.00'),
            stock=Decimal('20.000'),
            is_active=True
        )
        self.stock_balance = StockBalance.objects.create(
            store=self.store,
            product=self.product,
            on_hand=Decimal('20.000'),
            reserved=Decimal('0.000')
        )

        # Product 2
        self.product2 = Product.objects.create(
            name="Brown Eggs 12pk",
            store=self.store,
            price=Decimal('120.00'),
            stock=Decimal('15.000'),
            is_active=True
        )
        self.stock_balance2 = StockBalance.objects.create(
            store=self.store,
            product=self.product2,
            on_hand=Decimal('15.000'),
            reserved=Decimal('0.000')
        )

        # Create a COMPLETED Order
        self.completed_order = Order.objects.create(
            store=self.store,
            customer=self.customer,
            vendor=self.vendor,
            status=OrderStatus.COMPLETED,
            fulfillment_type=FulfillmentType.PICKUP,
            subtotal=Decimal('220.00'),
            discount_amount=Decimal('20.00'),  # Coupon discount
            total_amount=Decimal('200.00'),
            payment_status=PaymentStatus.COLLECTED,
            loyalty_points_earned=20
        )
        self.order_item1 = OrderItem.objects.create(
            order=self.completed_order,
            product=self.product,
            product_name_snapshot=self.product.name,
            unit_price_snapshot=Decimal('50.00'),
            quantity=Decimal('2.000'),
            line_total=Decimal('100.00')
        )
        self.order_item2 = OrderItem.objects.create(
            order=self.completed_order,
            product=self.product2,
            product_name_snapshot=self.product2.name,
            unit_price_snapshot=Decimal('120.00'),
            quantity=Decimal('1.000'),
            line_total=Decimal('120.00')
        )

        # Set up customer loyalty
        self.loyalty_program = StoreLoyaltyProgram.objects.create(
            store=self.store,
            program_type=LoyaltyProgramType.POINTS,
            is_active=True,
            points_per_currency_unit=Decimal('0.1')
        )
        self.customer_loyalty = CustomerStoreLoyalty.objects.create(
            store=self.store,
            customer=self.customer,
            points_balance=50
        )

    def test_customer_request_return_on_completed_order(self):
        """Customer successfully submits a return request for completed order items."""
        self.client.force_authenticate(user=self.customer)
        url = "/orders/returns/request/"
        payload = {
            "order_id": self.completed_order.id,
            "reason": ReturnReason.DAMAGED_DEFECTIVE,
            "reason_notes": "Leaking carton on milk bottle",
            "items": [
                {
                    "order_item_id": self.order_item1.id,
                    "quantity": "1.000"
                }
            ]
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])

        ret_data = response.data['data']

        self.assertTrue(ret_data['return_number'].startswith("RET-"))
        self.assertEqual(ret_data['status'], ReturnStatus.REQUESTED)
        self.assertEqual(len(ret_data['items']), 1)
        # Unit price is proportionally discounted: 50 * (200 / 220) = ~45.45
        self.assertGreater(Decimal(ret_data['total_refund_amount']), Decimal('0.00'))

    def test_return_rejected_on_non_completed_order(self):
        """Returns cannot be requested on orders that are still SUBMITTED or PREPARING."""
        self.completed_order.status = OrderStatus.PREPARING
        self.completed_order.save()

        self.client.force_authenticate(user=self.customer)
        url = "/orders/returns/request/"
        payload = {
            "order_id": self.completed_order.id,
            "reason": ReturnReason.WRONG_PRODUCT,
            "items": [{"order_item_id": self.order_item1.id, "quantity": "1.000"}]
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Only COMPLETED orders can be returned", response.data['message'])

    def test_return_rejected_if_quantity_exceeds_purchased(self):
        """Cannot request to return more quantity than was purchased in the order item."""
        self.client.force_authenticate(user=self.customer)
        url = "/orders/returns/request/"
        payload = {
            "order_id": self.completed_order.id,
            "items": [{"order_item_id": self.order_item1.id, "quantity": "5.000"}]  # Purchased only 2
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("exceeds available refundable quantity", response.data['message'])

    def test_vendor_approves_return_with_inventory_restock(self):
        """Vendor approves return: stock increases, ledger logs RETURN, customer loyalty adjusts."""
        # 1. Customer creates return request
        self.client.force_authenticate(user=self.customer)
        req_resp = self.client.post("/orders/returns/request/", {
            "order_id": self.completed_order.id,
            "reason": ReturnReason.CUSTOMER_CHANGED_MIND,
            "items": [{"order_item_id": self.order_item1.id, "quantity": "1.000"}]
        }, format='json')
        return_id = req_resp.data['data']['id']

        initial_on_hand = self.stock_balance.on_hand  # 20.000

        # 2. Vendor processes and approves with restock_inventory=True
        self.client.force_authenticate(user=self.vendor)
        process_resp = self.client.post(f"/orders/returns/{return_id}/process/", {
            "decision": "approved",
            "restock_inventory": True
        }, format='json')
        self.assertEqual(process_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(process_resp.data['data']['status'], ReturnStatus.COMPLETED)

        # 3. Verify stock balance was restored atomically
        self.stock_balance.refresh_from_db()
        self.assertEqual(self.stock_balance.on_hand, initial_on_hand + Decimal('1.000'))

        # 4. Verify StockLedgerEntry audit log
        ledger = StockLedgerEntry.objects.filter(
            product=self.product,
            movement_type=StockMovementType.RETURN
        ).first()
        self.assertIsNotNone(ledger)
        self.assertEqual(ledger.quantity, Decimal('1.000'))
        self.assertEqual(ledger.balance_after, self.stock_balance.on_hand)

        # 5. Verify loyalty points reversed proportionally
        self.customer_loyalty.refresh_from_db()
        self.assertLess(self.customer_loyalty.points_balance, 50)

    def test_vendor_approves_return_without_restock_damaged_goods(self):
        """Vendor approves defective return without restocking: stock is NOT incremented."""
        self.client.force_authenticate(user=self.customer)
        req_resp = self.client.post("/orders/returns/request/", {
            "order_id": self.completed_order.id,
            "reason": ReturnReason.DAMAGED_DEFECTIVE,
            "items": [{"order_item_id": self.order_item2.id, "quantity": "1.000"}]
        }, format='json')
        return_id = req_resp.data['data']['id']

        initial_on_hand = self.stock_balance2.on_hand

        self.client.force_authenticate(user=self.vendor)
        process_resp = self.client.post(f"/orders/returns/{return_id}/process/", {
            "decision": "approved",
            "restock_inventory": False  # Damaged goods discarded
        }, format='json')
        self.assertEqual(process_resp.status_code, status.HTTP_200_OK)

        self.stock_balance2.refresh_from_db()
        # Stock balance did not increase
        self.assertEqual(self.stock_balance2.on_hand, initial_on_hand)

        # Ledger logged as DAMAGE_LOSS
        damage_ledger = StockLedgerEntry.objects.filter(
            product=self.product2,
            movement_type=StockMovementType.DAMAGE_LOSS
        ).first()
        self.assertIsNotNone(damage_ledger)

    def test_vendor_rejects_return_with_reason(self):
        """Vendor rejects return request with mandatory rejection reason."""
        self.client.force_authenticate(user=self.customer)
        req_resp = self.client.post("/orders/returns/request/", {
            "order_id": self.completed_order.id,
            "reason": ReturnReason.CUSTOMER_CHANGED_MIND,
            "items": [{"order_item_id": self.order_item1.id, "quantity": "1.000"}]
        }, format='json')
        return_id = req_resp.data['data']['id']

        self.client.force_authenticate(user=self.vendor)
        reject_resp = self.client.post(f"/orders/returns/{return_id}/process/", {
            "decision": "rejected",
            "rejection_reason": "Seal broken and consumed"
        }, format='json')
        self.assertEqual(reject_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(reject_resp.data['data']['status'], ReturnStatus.REJECTED)
        self.assertEqual(reject_resp.data['data']['rejection_reason'], "Seal broken and consumed")

    def test_thermal_credit_note_receipt_generation(self):
        """Printable 40-column monospace thermal credit note slip generation."""
        self.client.force_authenticate(user=self.customer)
        req_resp = self.client.post("/orders/returns/request/", {
            "order_id": self.completed_order.id,
            "reason": ReturnReason.DAMAGED_DEFECTIVE,
            "items": [{"order_item_id": self.order_item1.id, "quantity": "1.000"}]
        }, format='json')
        return_id = req_resp.data['data']['id']

        # Vendor approves
        self.client.force_authenticate(user=self.vendor)
        self.client.post(f"/orders/returns/{return_id}/process/", {
            "decision": "approved",
            "restock_inventory": True
        }, format='json')

        # Customer or vendor fetches thermal credit note
        slip_resp = self.client.get(f"/orders/returns/{return_id}/credit-note/?receipt_format=text")
        self.assertEqual(slip_resp.status_code, status.HTTP_200_OK)

        self.assertEqual(slip_resp['content-type'], 'text/plain; charset=utf-8')
        content = slip_resp.content.decode('utf-8')
        self.assertIn("CREDIT NOTE / RETURN RECEIPT", content)
        self.assertIn("SUPER GROCERS", content)
        self.assertIn("TOTAL REFUND:", content)

    def test_tenant_isolation_and_cross_vendor_defense(self):
        """Cross-tenant defense: Other vendors cannot process another store's return requests."""
        self.client.force_authenticate(user=self.customer)
        req_resp = self.client.post("/orders/returns/request/", {
            "order_id": self.completed_order.id,
            "reason": ReturnReason.DAMAGED_DEFECTIVE,
            "items": [{"order_item_id": self.order_item1.id, "quantity": "1.000"}]
        }, format='json')
        return_id = req_resp.data['data']['id']

        # Other vendor tries to approve this return -> 403 Forbidden
        self.client.force_authenticate(user=self.other_vendor)
        cross_resp = self.client.post(f"/orders/returns/{return_id}/process/", {
            "decision": "approved",
            "restock_inventory": True
        }, format='json')
        self.assertEqual(cross_resp.status_code, status.HTTP_403_FORBIDDEN)

        # Customer tries to approve their own return -> 403 Forbidden
        self.client.force_authenticate(user=self.customer)
        self_approve_resp = self.client.post(f"/orders/returns/{return_id}/process/", {
            "decision": "approved"
        }, format='json')
        self.assertEqual(self_approve_resp.status_code, status.HTTP_403_FORBIDDEN)

        # Other customer tries to request return for customer 1's order -> 403 Forbidden
        self.client.force_authenticate(user=self.other_customer)
        other_cust_resp = self.client.post("/orders/returns/request/", {
            "order_id": self.completed_order.id,
            "items": [{"order_item_id": self.order_item1.id, "quantity": "1.000"}]
        }, format='json')
        self.assertEqual(other_cust_resp.status_code, status.HTTP_403_FORBIDDEN)
