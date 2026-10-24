from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from users.models.user_mod import User
from stores.models.store_mod import Store
from products.models.product_mod import Product
from cards.repositories.card_repository import CardRepository
from cards.services.card_service import CardService
from inventory.services.inventory_service import InventoryService
from orders.models.order_mod import Order, OrderStatus, FulfillmentType, PaymentStatus
from orders.services.order_service import OrderService
from shared.enums.enums import UserRoleEnum


class CounterPOSWalkInTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Vendor & Store A
        self.vendor = User.objects.create_user(
            email="vendor_counter@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.store = Store.objects.create(
            vendor=self.vendor,
            name="Counter Mart",
            delivery_fee=Decimal('20.00'),
            pickup_enabled=True,
            delivery_enabled=True
        )

        # Inventory
        self.product = Product.objects.create(store=self.store, name="Organic Honey 500g", price=250.00, stock=0)
        InventoryService.receive_stock(self.store, self.product, Decimal('50.000'))

        # Customer & Draft Shopping Memo
        self.customer = User.objects.create_user(
            email="shopper@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )

        # Competing Vendor (Store B)
        self.competing_vendor = User.objects.create_user(
            email="competitor@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.competing_store = Store.objects.create(
            vendor=self.competing_vendor,
            name="Competitor Mart",
            pickup_enabled=True
        )

    def _create_order(self, fulfillment_type=FulfillmentType.WALK_IN):
        card = CardRepository.create_card(user=self.customer, store=self.store)
        CardService.add_product_to_card(card.id, self.product.id, Decimal('2.000'))
        return OrderService.submit_order_from_card(
            card=card,
            customer=self.customer,
            fulfillment_type=fulfillment_type,
            delivery_address="456 City Center" if fulfillment_type == FulfillmentType.DELIVERY else ""
        )

    def test_walk_in_order_auto_generates_6_digit_code(self):
        walk_in_order = self._create_order(fulfillment_type=FulfillmentType.WALK_IN)
        self.assertTrue(bool(walk_in_order.walk_in_code))
        self.assertEqual(len(walk_in_order.walk_in_code), 6)
        self.assertTrue(walk_in_order.walk_in_code.isdigit())

        pickup_order = self._create_order(fulfillment_type=FulfillmentType.PICKUP)
        self.assertTrue(bool(pickup_order.walk_in_code))
        self.assertEqual(len(pickup_order.walk_in_code), 6)
        self.assertTrue(pickup_order.walk_in_code.isdigit())

        delivery_order = self._create_order(fulfillment_type=FulfillmentType.DELIVERY)
        self.assertEqual(delivery_order.walk_in_code, "")

    def test_counter_lookup_success_as_store_vendor(self):
        order = self._create_order(fulfillment_type=FulfillmentType.WALK_IN)
        code = order.walk_in_code

        self.client.force_authenticate(user=self.vendor)
        response = self.client.post('/orders/counter-lookup/', {'code': code}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()['data']
        self.assertEqual(data['id'], order.id)
        self.assertEqual(data['order_number'], order.order_number)
        self.assertEqual(data['walk_in_code'], code)
        self.assertEqual(data['status'], OrderStatus.SUBMITTED)
        self.assertEqual(data['customer_email'], self.customer.email)
        self.assertEqual(len(data['items']), 1)
        self.assertEqual(data['items'][0]['product_name_snapshot'], self.product.name)

    def test_counter_lookup_with_store_id_validation(self):
        order = self._create_order(fulfillment_type=FulfillmentType.WALK_IN)
        code = order.walk_in_code

        self.client.force_authenticate(user=self.vendor)

        # Correct store ID succeeds
        response = self.client.post(
            '/orders/counter-lookup/',
            {'code': code, 'store_id': self.store.id},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Mismatched store ID fails
        response_wrong_store = self.client.post(
            '/orders/counter-lookup/',
            {'code': code, 'store_id': self.competing_store.id},
            format='json'
        )
        self.assertEqual(response_wrong_store.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("does not belong to the selected store", response_wrong_store.json()['message'])

    def test_counter_lookup_tenant_isolation_cross_vendor_forbidden(self):
        order = self._create_order(fulfillment_type=FulfillmentType.WALK_IN)
        code = order.walk_in_code

        # Competing vendor attempts to look up Vendor A's order code
        self.client.force_authenticate(user=self.competing_vendor)
        response = self.client.post('/orders/counter-lookup/', {'code': code}, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("do not have permission", response.json()['message'])

    def test_counter_lookup_customer_cannot_use_counter_pos(self):
        order = self._create_order(fulfillment_type=FulfillmentType.WALK_IN)
        code = order.walk_in_code

        # Customer attempts to use counter lookup
        self.client.force_authenticate(user=self.customer)
        response = self.client.post('/orders/counter-lookup/', {'code': code}, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_counter_lookup_invalid_or_missing_code(self):
        self.client.force_authenticate(user=self.vendor)

        # Missing code
        response_empty = self.client.post('/orders/counter-lookup/', {'code': ''}, format='json')
        self.assertEqual(response_empty.status_code, status.HTTP_400_BAD_REQUEST)

        # Non-existent code
        response_missing = self.client.post('/orders/counter-lookup/', {'code': '999999'}, format='json')
        self.assertEqual(response_missing.status_code, status.HTTP_404_NOT_FOUND)

    def test_in_store_counter_handover_flow_and_sales_memo_snapshot(self):
        order = self._create_order(fulfillment_type=FulfillmentType.WALK_IN)
        code = order.walk_in_code

        self.client.force_authenticate(user=self.vendor)

        # 1. Counter POS look up
        lookup_resp = self.client.post('/orders/counter-lookup/', {'code': code}, format='json')
        self.assertEqual(lookup_resp.status_code, status.HTTP_200_OK)

        # 2. Store Owner hands over items & collects cash payment
        handover_resp = self.client.post(
            f'/orders/{order.id}/handover/',
            {'payment_collected': True},
            format='json'
        )
        self.assertEqual(handover_resp.status_code, status.HTTP_200_OK)

        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.COMPLETED)
        self.assertEqual(order.payment_status, PaymentStatus.COLLECTED)

        # 3. Check Sales Memo snapshot contains walk_in_code_snapshot
        sales_memo = order.sales_memo
        self.assertIsNotNone(sales_memo)
        self.assertEqual(sales_memo.walk_in_code_snapshot, code)

        # 4. Check Sales Memo via API endpoint
        memo_resp = self.client.get(f'/orders/{order.id}/sales_memo/')
        self.assertEqual(memo_resp.status_code, status.HTTP_200_OK)
        memo_data = memo_resp.json()['data']
        self.assertEqual(memo_data['walk_in_code_snapshot'], code)
        self.assertEqual(memo_data['total_amount'], '500.00')
