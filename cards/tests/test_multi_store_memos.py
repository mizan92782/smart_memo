from decimal import Decimal
from rest_framework.test import APITestCase
from rest_framework import status

from users.models.user_mod import User
from shared.enums.enums import UserRoleEnum
from stores.models.store_mod import Store
from products.models.product_mod import Product
from categories.models.category_mod import Category
from cards.models.card_mod import Card, ShoppingMode
from orders.models.order_mod import Order, OrderStatus, FulfillmentType, PaymentStatus, SalesMemo


class MultiStoreWalkInMemoTests(APITestCase):
    def setUp(self):
        # Users
        self.vendor_a = User.objects.create_user(
            email='vendor_a_ms@example.com',
            password='Password123!',
            role=UserRoleEnum.VENDOR
        )
        self.vendor_b = User.objects.create_user(
            email='vendor_b_ms@example.com',
            password='Password123!',
            role=UserRoleEnum.VENDOR
        )
        self.customer = User.objects.create_user(
            email='customer_ms@example.com',
            password='Password123!',
            role=UserRoleEnum.CUSTOMER
        )

        # Store A: Fresh Bazaar (Supports walk-in, pickup and delivery)
        self.store_a = Store.objects.create(
            vendor=self.vendor_a,
            name="Fresh Bazaar",
            address="Market Place A, Dhaka",
            is_active=True,
            is_verified=True,
            pickup_enabled=True,
            delivery_enabled=True,
            delivery_fee=Decimal('30.00'),
            min_order_amount=Decimal('100.00')
        )
        self.cat_a = Category.objects.create(store=self.store_a, name="Vegetables")
        self.product_a1 = Product.objects.create(
            store=self.store_a,
            category=self.cat_a,
            name="Farm Carrots",
            price=Decimal('40.00'),
            sku="CAR-01",
            stock=Decimal('100.000'),
            is_active=True
        )
        self.product_a2 = Product.objects.create(
            store=self.store_a,
            category=self.cat_a,
            name="Fresh Spinach",
            price=Decimal('25.00'),
            sku="SPN-01",
            stock=Decimal('50.000'),
            is_active=True
        )

        # Store B: City Pharmacy (Different store in the market)
        self.store_b = Store.objects.create(
            vendor=self.vendor_b,
            name="City Pharmacy",
            address="Market Place B, Dhaka",
            is_active=True,
            is_verified=True,
            pickup_enabled=True,
            delivery_enabled=True,
            delivery_fee=Decimal('20.00')
        )
        self.cat_b = Category.objects.create(store=self.store_b, name="Healthcare")
        self.product_b1 = Product.objects.create(
            store=self.store_b,
            category=self.cat_b,
            name="Vitamin C 500mg",
            price=Decimal('150.00'),
            sku="VIT-01",
            stock=Decimal('200.000'),
            is_active=True
        )

        from inventory.services.inventory_service import InventoryService
        InventoryService.receive_stock(self.store_a, self.product_a1, Decimal('100.000'))
        InventoryService.receive_stock(self.store_a, self.product_a2, Decimal('50.000'))
        InventoryService.receive_stock(self.store_b, self.product_b1, Decimal('200.000'))

    def test_customer_enters_multiple_stores_and_maintains_parallel_memos(self):
        """Customer enters Store A and Store B, maintaining separate parallel active draft memos."""
        self.client.force_authenticate(user=self.customer)

        # Customer enters Store A and initializes memo
        resp_a = self.client.post(f"/stores/{self.store_a.id}/memo/", {"shopping_mode": "walk_in"}, format='json')
        self.assertEqual(resp_a.status_code, status.HTTP_200_OK)
        card_a_id = resp_a.data['data']['id']
        self.assertEqual(resp_a.data['data']['store'], self.store_a.id)
        self.assertEqual(resp_a.data['data']['shopping_mode'], ShoppingMode.WALK_IN)

        # Customer adds items from Store A
        resp_add_a = self.client.post(
            f"/cards/{card_a_id}/add-item/",
            {"product_id": self.product_a1.id, "quantity": 2},
            format='json'
        )
        self.assertEqual(resp_add_a.status_code, status.HTTP_201_CREATED)

        # Customer enters Store B and initializes memo for Store B
        resp_b = self.client.post(f"/stores/{self.store_b.id}/memo/", {"shopping_mode": "remote"}, format='json')
        self.assertEqual(resp_b.status_code, status.HTTP_200_OK)
        card_b_id = resp_b.data['data']['id']
        self.assertEqual(resp_b.data['data']['store'], self.store_b.id)
        self.assertNotEqual(card_a_id, card_b_id)

        # Customer adds items from Store B
        resp_add_b = self.client.post(
            f"/cards/{card_b_id}/add-item/",
            {"product_id": self.product_b1.id, "quantity": 1},
            format='json'
        )
        self.assertEqual(resp_add_b.status_code, status.HTTP_201_CREATED)

        # List all draft memos for the customer
        list_resp = self.client.get("/cards/?is_completed=false")
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        results = list_resp.data['data'] if isinstance(list_resp.data, dict) and 'data' in list_resp.data else list_resp.data
        card_ids = [c['id'] for c in results]
        self.assertIn(card_a_id, card_ids)
        self.assertIn(card_b_id, card_ids)

    def test_active_memo_endpoint_scoped_to_store(self):
        """GET /cards/active/?store_id=X retrieves the active memo for that specific store."""
        self.client.force_authenticate(user=self.customer)

        # Initialize memo for Store A
        self.client.post(f"/stores/{self.store_a.id}/memo/", format='json')
        # Initialize memo for Store B
        self.client.post(f"/stores/{self.store_b.id}/memo/", format='json')

        # Request active card for Store A specifically
        resp_a = self.client.get(f"/cards/active/?store_id={self.store_a.id}")
        self.assertEqual(resp_a.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_a.data['data']['store'], self.store_a.id)

        # Request active card for Store B specifically
        resp_b = self.client.get(f"/cards/active/?store_id={self.store_b.id}")
        self.assertEqual(resp_b.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_b.data['data']['store'], self.store_b.id)

    def test_in_store_walk_in_shopping_memo_creation_and_item_addition(self):
        """Customer walks in store, adds products to walk-in memo as they shop."""
        self.client.force_authenticate(user=self.customer)

        # Initialize walk-in memo
        resp = self.client.post(
            f"/stores/{self.store_a.id}/memo/",
            {"shopping_mode": "walk_in"},
            format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        card_id = resp.data['data']['id']
        self.assertEqual(resp.data['data']['shopping_mode'], 'walk_in')

        # Add carrots and spinach while walking in store
        self.client.post(f"/cards/{card_id}/add-item/", {"product_id": self.product_a1.id, "quantity": 3}, format='json')
        self.client.post(f"/cards/{card_id}/add-item/", {"product_id": self.product_a2.id, "quantity": 2}, format='json')

        # Check total
        card_resp = self.client.get(f"/cards/{card_id}/")
        self.assertEqual(card_resp.status_code, status.HTTP_200_OK)
        # 3 * 40 + 2 * 25 = 120 + 50 = 170.00
        self.assertEqual(card_resp.data['data']['total_price'], '170.00')

    def test_walk_in_memo_checkout_zero_delivery_fee_no_address(self):
        """Checking out walk-in memo requires no delivery address and charges 0.00 delivery fee."""
        self.client.force_authenticate(user=self.customer)

        memo_resp = self.client.post(f"/stores/{self.store_a.id}/memo/", {"shopping_mode": "walk_in"}, format='json')
        card_id = memo_resp.data['data']['id']
        self.client.post(f"/cards/{card_id}/add-item/", {"product_id": self.product_a1.id, "quantity": 3}, format='json')

        # Checkout with fulfillment_type='walk_in'
        payload = {
            "fulfillment_type": "walk_in",
            "notes": "Picked up from shelf B3"
        }
        checkout_resp = self.client.post(f"/cards/{card_id}/checkout/", payload, format='json')
        self.assertEqual(checkout_resp.status_code, status.HTTP_201_CREATED, checkout_resp.data)

        order_data = checkout_resp.data['data']
        self.assertEqual(order_data['fulfillment_type'], FulfillmentType.WALK_IN)
        self.assertEqual(order_data['delivery_fee'], '0.00')
        self.assertEqual(order_data['status'], OrderStatus.SUBMITTED)
        self.assertEqual(order_data['total_amount'], '120.00')

    def test_store_owner_in_store_handover_and_instant_fulfillment(self):
        """Store owner collects picked items, executes in-store handover, and collects payment on the spot."""
        self.client.force_authenticate(user=self.customer)

        memo_resp = self.client.post(f"/stores/{self.store_a.id}/memo/", {"shopping_mode": "walk_in"}, format='json')
        card_id = memo_resp.data['data']['id']
        self.client.post(f"/cards/{card_id}/add-item/", {"product_id": self.product_a1.id, "quantity": 2}, format='json')

        checkout_resp = self.client.post(f"/cards/{card_id}/checkout/", {"fulfillment_type": "walk_in"}, format='json')
        order_id = checkout_resp.data['data']['id']

        # Vendor A collects items and hands them over to customer at the counter
        self.client.force_authenticate(user=self.vendor_a)
        handover_resp = self.client.post(
            f"/orders/{order_id}/handover/",
            {"payment_collected": True},
            format='json'
        )
        self.assertEqual(handover_resp.status_code, status.HTTP_200_OK)

        order_data = handover_resp.data['data']
        self.assertEqual(order_data['status'], OrderStatus.COMPLETED)
        self.assertEqual(order_data['payment_status'], PaymentStatus.COLLECTED)
        self.assertIsNotNone(order_data['completed_at'])
        self.assertIsNotNone(order_data['paid_at'])

        # Verify finalized SalesMemo receipt exists
        sales_memo = SalesMemo.objects.filter(order_id=order_id).first()
        self.assertIsNotNone(sales_memo)
        self.assertEqual(sales_memo.amount_paid, Decimal('80.00'))

    def test_cross_tenant_guards_on_handover(self):
        """Vendor B cannot hand over Store A's orders, and customers cannot hand over their own orders."""
        self.client.force_authenticate(user=self.customer)
        memo_resp = self.client.post(f"/stores/{self.store_a.id}/memo/", {"shopping_mode": "walk_in"}, format='json')
        card_id = memo_resp.data['data']['id']
        self.client.post(f"/cards/{card_id}/add-item/", {"product_id": self.product_a1.id, "quantity": 1}, format='json')
        checkout_resp = self.client.post(f"/cards/{card_id}/checkout/", {"fulfillment_type": "walk_in"}, format='json')
        order_id = checkout_resp.data['data']['id']

        # Other vendor attempts handover
        self.client.force_authenticate(user=self.vendor_b)
        resp_b = self.client.post(f"/orders/{order_id}/handover/", format='json')
        self.assertIn(resp_b.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

        # Customer attempts handover on own order
        self.client.force_authenticate(user=self.customer)
        resp_c = self.client.post(f"/orders/{order_id}/handover/", format='json')
        self.assertEqual(resp_c.status_code, status.HTTP_403_FORBIDDEN)

        # Unauthenticated
        self.client.force_authenticate(user=None)
        resp_anon = self.client.post(f"/orders/{order_id}/handover/", format='json')
        self.assertEqual(resp_anon.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_filter_cards_by_store_id(self):
        """GET /cards/?store_id=X filters draft cards strictly for that store."""
        self.client.force_authenticate(user=self.customer)
        self.client.post(f"/stores/{self.store_a.id}/memo/", format='json')
        self.client.post(f"/stores/{self.store_b.id}/memo/", format='json')

        resp_a = self.client.get(f"/cards/?store_id={self.store_a.id}")
        self.assertEqual(resp_a.status_code, status.HTTP_200_OK)
        results_a = resp_a.data['data'] if isinstance(resp_a.data, dict) and 'data' in resp_a.data else resp_a.data
        for card in results_a:
            self.assertEqual(card['store'], self.store_a.id)

        resp_b = self.client.get(f"/cards/?store_id={self.store_b.id}")
        self.assertEqual(resp_b.status_code, status.HTTP_200_OK)
        results_b = resp_b.data['data'] if isinstance(resp_b.data, dict) and 'data' in resp_b.data else resp_b.data
        for card in results_b:
            self.assertEqual(card['store'], self.store_b.id)

    def test_home_delivery_memo_checkout_still_requires_address_and_charges_delivery_fee(self):
        """Home delivery memos still enforce address requirement and charge delivery fee."""
        self.client.force_authenticate(user=self.customer)
        memo_resp = self.client.post(f"/stores/{self.store_a.id}/memo/", {"shopping_mode": "remote"}, format='json')
        card_id = memo_resp.data['data']['id']
        self.client.post(f"/cards/{card_id}/add-item/", {"product_id": self.product_a1.id, "quantity": 3}, format='json')

        # Checkout without delivery address
        resp_fail = self.client.post(f"/cards/{card_id}/checkout/", {"fulfillment_type": "delivery"}, format='json')
        self.assertEqual(resp_fail.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("delivery_address is required", resp_fail.data['message'])

        # Checkout with delivery address succeeds and charges store delivery fee
        resp_ok = self.client.post(
            f"/cards/{card_id}/checkout/",
            {"fulfillment_type": "delivery", "delivery_address": "House 10, Road 4, Sector 7, Uttara"},
            format='json'
        )
        self.assertEqual(resp_ok.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp_ok.data['data']['delivery_fee'], '30.00')
        # Subtotal: 3 * 40 = 120 + 30 fee = 150.00
        self.assertEqual(resp_ok.data['data']['total_amount'], '150.00')

    def test_rejection_of_handover_on_cancelled_or_completed_order(self):
        """Handover is rejected on cancelled or completed orders."""
        self.client.force_authenticate(user=self.customer)
        memo_resp = self.client.post(f"/stores/{self.store_a.id}/memo/", {"shopping_mode": "walk_in"}, format='json')
        card_id = memo_resp.data['data']['id']
        self.client.post(f"/cards/{card_id}/add-item/", {"product_id": self.product_a1.id, "quantity": 1}, format='json')
        checkout_resp = self.client.post(f"/cards/{card_id}/checkout/", {"fulfillment_type": "walk_in"}, format='json')
        order_id = checkout_resp.data['data']['id']

        # Cancel the order
        self.client.post(f"/orders/{order_id}/cancel/", {"reason": "Customer changed mind"}, format='json')

        # Vendor attempts handover on cancelled order
        self.client.force_authenticate(user=self.vendor_a)
        handover_resp = self.client.post(f"/orders/{order_id}/handover/", format='json')
        self.assertEqual(handover_resp.status_code, status.HTTP_400_BAD_REQUEST)

