from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from shared.enums.enums import UserRoleEnum
from stores.models.store_mod import Store
from products.models.product_mod import Product
from cards.models.card_mod import Card
from orders.models.order_mod import Order, PaymentMethod
from inventory.services.inventory_service import InventoryService
from users.models.address_mod import CustomerAddress

User = get_user_model()


class NamedStoreMemoTests(APITestCase):
    """
    Customers must consciously open a named memo per store before shopping.
    A memo is never implicitly visible across stores.
    """

    def setUp(self):
        self.vendor = User.objects.create_user(
            email="vendor_named@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.customer = User.objects.create_user(
            email="shopper_named@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )
        self.store_a = Store.objects.create(
            name="Corner Grocery", vendor=self.vendor, address="Road 3", is_active=True
        )
        self.store_b = Store.objects.create(
            name="Fresh Bazaar", vendor=self.vendor, address="Road 9", is_active=True
        )
        self.client.force_authenticate(user=self.customer)

    def test_peek_returns_null_when_no_memo_opened_yet(self):
        res = self.client.get(f'/stores/{self.store_a.id}/memo/?create=false')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIsNone(res.data['data'])
        self.assertFalse(Card.objects.filter(user=self.customer).exists())

    def test_customer_opens_memo_with_their_own_name(self):
        res = self.client.post(
            f'/stores/{self.store_a.id}/memo/',
            {'title': 'Weekly Ramadan Bazaar', 'shopping_mode': 'walk_in'},
            format='json'
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['data']['title'], 'Weekly Ramadan Bazaar')
        self.assertEqual(res.data['data']['shopping_mode'], 'walk_in')
        self.assertEqual(res.data['data']['store'], self.store_a.id)

    def test_reopening_memo_keeps_identity_and_applies_rename(self):
        first = self.client.post(
            f'/stores/{self.store_a.id}/memo/', {'title': 'Draft One'}, format='json'
        )
        memo_id = first.data['data']['id']

        again = self.client.post(
            f'/stores/{self.store_a.id}/memo/',
            {'title': 'Eid Shopping', 'shopping_mode': 'walk_in'},
            format='json'
        )
        self.assertEqual(again.data['data']['id'], memo_id)
        self.assertEqual(again.data['data']['title'], 'Eid Shopping')
        self.assertEqual(again.data['data']['shopping_mode'], 'walk_in')
        self.assertEqual(Card.objects.filter(user=self.customer, store=self.store_a).count(), 1)

    def test_each_store_gets_its_own_isolated_named_memo(self):
        self.client.post(f'/stores/{self.store_a.id}/memo/', {'title': 'Grocery Run'}, format='json')
        res_b = self.client.post(f'/stores/{self.store_b.id}/memo/', {'title': 'Fish & Meat'}, format='json')

        memo_a = Card.objects.get(user=self.customer, store=self.store_a)
        memo_b = Card.objects.get(user=self.customer, store=self.store_b)
        self.assertNotEqual(memo_a.id, memo_b.id)
        self.assertEqual(memo_a.title, 'Grocery Run')
        self.assertEqual(res_b.data['data']['title'], 'Fish & Meat')

        # Opening store B must not surface store A's memo
        peek_b = self.client.get(f'/stores/{self.store_b.id}/memo/?create=false')
        self.assertEqual(peek_b.data['data']['id'], memo_b.id)

    def test_peek_does_not_leak_another_customers_memo(self):
        self.client.post(f'/stores/{self.store_a.id}/memo/', {'title': 'Mine'}, format='json')
        intruder = User.objects.create_user(
            email="intruder_named@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )
        self.client.force_authenticate(user=intruder)
        res = self.client.get(f'/stores/{self.store_a.id}/memo/?create=false')
        self.assertIsNone(res.data['data'])


class MemoCheckoutPaymentMethodTests(APITestCase):
    """Payment method selection at checkout: COD / bKash / Nagad for home delivery,
    physical cash only for in-store handover."""

    def setUp(self):
        self.vendor = User.objects.create_user(
            email="vendor_pay@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.customer = User.objects.create_user(
            email="shopper_pay@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )
        self.store = Store.objects.create(
            name="Pay Test Mart", vendor=self.vendor, address="Road 7",
            is_active=True, delivery_enabled=True, pickup_enabled=True
        )
        self.product = Product.objects.create(
            store=self.store, name="Basmati Rice 5kg",
            price=Decimal('650.00'), stock=0
        )
        InventoryService.receive_stock(self.store, self.product, Decimal('40.000'))
        self.client.force_authenticate(user=self.customer)

    def _memo_with_item(self):
        res = self.client.post(f'/stores/{self.store.id}/memo/', {'title': 'Pay Memo'}, format='json')
        memo_id = res.data['data']['id']
        self.client.post(
            f'/cards/{memo_id}/add-item/',
            {'product_id': self.product.id, 'quantity': '2'},
            format='json'
        )
        return memo_id

    def test_home_delivery_accepts_bkash(self):
        memo_id = self._memo_with_item()
        res = self.client.post(
            f'/cards/{memo_id}/checkout/',
            {
                'fulfillment_type': 'delivery',
                'delivery_address': 'House 4, Road 7, Dhaka',
                'payment_method': 'bkash',
            },
            format='json'
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['data']['payment_method'], 'bkash')
        self.assertEqual(res.data['data']['payment_method_display'], 'bKash')
        # "UI only" stage: nothing is settled until the vendor collects/verifies it.
        self.assertEqual(res.data['data']['payment_status'], 'pending')

    def test_home_delivery_accepts_nagad(self):
        memo_id = self._memo_with_item()
        res = self.client.post(
            f'/cards/{memo_id}/checkout/',
            {
                'fulfillment_type': 'delivery',
                'delivery_address': 'House 4, Road 7, Dhaka',
                'payment_method': 'nagad',
            },
            format='json'
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['data']['payment_method'], 'nagad')

    def test_home_delivery_defaults_to_cash_on_delivery(self):
        memo_id = self._memo_with_item()
        res = self.client.post(
            f'/cards/{memo_id}/checkout/',
            {'fulfillment_type': 'delivery', 'delivery_address': 'House 4, Road 7, Dhaka'},
            format='json'
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['data']['payment_method'], PaymentMethod.COD)

    def test_walk_in_rejects_mobile_payment(self):
        memo_id = self._memo_with_item()
        res = self.client.post(
            f'/cards/{memo_id}/checkout/',
            {'fulfillment_type': 'walk_in', 'payment_method': 'bkash'},
            format='json'
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.filter(customer=self.customer).count(), 0)

    def test_walk_in_accepts_counter_cash_and_issues_handover_code(self):
        memo_id = self._memo_with_item()
        res = self.client.post(
            f'/cards/{memo_id}/checkout/',
            {'fulfillment_type': 'walk_in', 'payment_method': 'cash_counter'},
            format='json'
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['data']['payment_method'], 'cash_counter')
        self.assertEqual(res.data['data']['status'], 'submitted')
        self.assertTrue(res.data['data']['walk_in_code'])

    def test_unknown_payment_method_is_rejected(self):
        memo_id = self._memo_with_item()
        res = self.client.post(
            f'/cards/{memo_id}/checkout/',
            {
                'fulfillment_type': 'delivery',
                'delivery_address': 'House 4, Road 7, Dhaka',
                'payment_method': 'crypto',
            },
            format='json'
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.filter(customer=self.customer).count(), 0)


class FrontendCheckoutPayloadTests(APITestCase):
    """Guards the exact field names the React checkout form posts
    (src/pages/customer/CheckoutPage.jsx) against the API contract."""

    def setUp(self):
        self.vendor = User.objects.create_user(
            email="vendor_payload@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.customer = User.objects.create_user(
            email="shopper_payload@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )
        self.store = Store.objects.create(
            name="Payload Mart", vendor=self.vendor, address="Road 11",
            is_active=True, delivery_enabled=True, pickup_enabled=True
        )
        self.product = Product.objects.create(
            store=self.store, name="Mustard Oil 1L", price=Decimal('320.00'), stock=0
        )
        InventoryService.receive_stock(self.store, self.product, Decimal('25.000'))
        self.address = CustomerAddress.objects.create(
            customer=self.customer,
            label="Home",
            recipient_name="Shopper",
            phone_number="01711111111",
            address_line="House 12, Road 11, Banani",
            city="Dhaka",
            is_default=True,
        )
        self.client.force_authenticate(user=self.customer)
        res = self.client.post(f'/stores/{self.store.id}/memo/', {'title': 'Payload Memo'}, format='json')
        self.memo_id = res.data['data']['id']
        self.client.post(
            f'/cards/{self.memo_id}/add-item/',
            {'product_id': self.product.id, 'quantity': '3'},
            format='json'
        )

    def test_home_delivery_payload_resolves_saved_address(self):
        res = self.client.post(
            f'/cards/{self.memo_id}/checkout/',
            {
                'fulfillment_type': 'delivery',
                'payment_method': 'bkash',
                'notes': 'Ring the bell twice',
                'address_id': self.address.id,
            },
            format='json'
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        order = Order.objects.get(id=res.data['data']['id'])
        self.assertEqual(order.fulfillment_type, 'delivery')
        self.assertEqual(order.payment_method, 'bkash')
        self.assertEqual(order.notes, 'Ring the bell twice')
        # The saved address must be snapshotted onto the order, not left blank.
        self.assertIn('Banani', order.delivery_address)
        self.assertEqual(order.customer_phone_snapshot, '01711111111')

    def test_walk_in_payload_uses_counter_cash(self):
        res = self.client.post(
            f'/cards/{self.memo_id}/checkout/',
            {
                'fulfillment_type': 'walk_in',
                'payment_method': 'cash_counter',
                'notes': '',
            },
            format='json'
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        order = Order.objects.get(id=res.data['data']['id'])
        self.assertEqual(order.fulfillment_type, 'walk_in')
        self.assertEqual(order.payment_method, 'cash_counter')
        self.assertEqual(len(order.walk_in_code), 6)
