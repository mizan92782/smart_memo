"""
cards/tests/test_database_level_fields.py — Database-Level User & Vendor Tests

Verifies that Card, Order, and SalesMemo contain direct database-level foreign keys
for user/customer and vendor, with automated synchronization and repository/API exposure.
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from cards.models.card_mod import Card, ShoppingMode
from cards.repositories.card_repository import CardRepository
from cards.serializers.card_ser import CardSerializer
from categories.models.category_mod import Category
from inventory.services.inventory_service import InventoryService
from orders.models.order_mod import Order, OrderStatus, FulfillmentType, SalesMemo
from orders.repositories.order_repository import OrderRepository
from orders.serializers.order_ser import OrderSerializer, SalesMemoSerializer
from orders.services.order_service import OrderService
from products.models.product_mod import Product
from shared.enums.enums import UserRoleEnum
from stores.models.store_mod import Store

User = get_user_model()


class DatabaseLevelUserVendorTests(APITestCase):
    def setUp(self):
        # Create users
        self.vendor_a = User.objects.create_user(
            email="vendor_a_db@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.vendor_b = User.objects.create_user(
            email="vendor_b_db@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.customer = User.objects.create_user(
            email="customer_db@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )

        # Create stores
        self.store_a = Store.objects.create(
            vendor=self.vendor_a,
            name="Alpha Supermarket",
            address="100 Alpha St",
            delivery_fee=Decimal('15.00')
        )
        self.store_b = Store.objects.create(
            vendor=self.vendor_b,
            name="Beta Pharmacy",
            address="200 Beta Ave",
            delivery_fee=Decimal('20.00')
        )

        # Create category and products
        self.category_a = Category.objects.create(
            store=self.store_a, name="Alpha Groceries"
        )
        self.product_a = Product.objects.create(
            store=self.store_a,
            category=self.category_a,
            name="Alpha Milk",
            price=Decimal('50.00'),
            stock=100
        )
        InventoryService.receive_stock(
            store=self.store_a,
            product=self.product_a,
            quantity=Decimal('100.000'),
            actor=self.vendor_a,
            notes="Initial stock intake"
        )

    def test_card_database_level_vendor_auto_population(self):
        """Card must auto-populate vendor from store upon creation and save."""
        card = CardRepository.get_or_create_active_card_for_user(
            user=self.customer,
            store=self.store_a,
            shopping_mode=ShoppingMode.WALK_IN
        )

        # Direct database checks
        self.assertEqual(card.user, self.customer)
        self.assertEqual(card.vendor, self.vendor_a)
        self.assertEqual(card.customer, self.customer)  # Property alias check

        # Verify raw database query matches
        raw_card = Card.objects.filter(pk=card.id, vendor=self.vendor_a, user=self.customer).first()
        self.assertIsNotNone(raw_card)

        # Verify serializer exposes vendor and vendor_email
        ser_data = CardSerializer(card).data
        self.assertEqual(ser_data['vendor'], self.vendor_a.id)
        self.assertEqual(ser_data['vendor_email'], "vendor_a_db@test.com")
        self.assertEqual(ser_data['user'], self.customer.id)

    def test_card_repository_get_by_vendor(self):
        """CardRepository.get_by_vendor returns cards scoped to the vendor."""
        card_a = CardRepository.get_or_create_active_card_for_user(
            user=self.customer, store=self.store_a
        )
        card_b = CardRepository.get_or_create_active_card_for_user(
            user=self.customer, store=self.store_b
        )

        vendor_a_cards = list(CardRepository.get_by_vendor(self.vendor_a.id))
        vendor_b_cards = list(CardRepository.get_by_vendor(self.vendor_b.id))

        self.assertIn(card_a, vendor_a_cards)
        self.assertNotIn(card_b, vendor_a_cards)
        self.assertIn(card_b, vendor_b_cards)
        self.assertNotIn(card_a, vendor_b_cards)

    def test_card_vendor_cleared_when_memo_emptied(self):
        """When an active draft memo items are deleted and store resets, vendor is also cleared."""
        card = CardRepository.get_or_create_active_card_for_user(
            user=self.customer, store=self.store_a
        )
        item = CardRepository.add_item_to_card(card, self.product_a, Decimal('2.000'))
        self.assertEqual(card.vendor, self.vendor_a)

        # Clear memo
        CardRepository.clear_card(card)
        card.refresh_from_db()

        self.assertIsNone(card.store)
        self.assertIsNone(card.vendor)

    def test_order_database_level_vendor_and_customer(self):
        """Order must contain direct database foreign keys for both customer and vendor."""
        card = CardRepository.get_or_create_active_card_for_user(
            user=self.customer, store=self.store_a
        )
        CardRepository.add_item_to_card(card, self.product_a, Decimal('2.000'))

        order = OrderService.submit_order_from_card(
            card=card,
            customer=self.customer,
            fulfillment_type=FulfillmentType.WALK_IN
        )

        # Database checks
        self.assertEqual(order.customer, self.customer)
        self.assertEqual(order.vendor, self.vendor_a)
        self.assertEqual(order.user, self.customer)  # Property alias check

        # Verify DB query directly on vendor
        order_from_db = Order.objects.filter(pk=order.id, vendor=self.vendor_a, customer=self.customer).first()
        self.assertIsNotNone(order_from_db)

        # OrderRepository.get_by_vendor
        vendor_orders = list(OrderRepository.get_by_vendor(self.vendor_a.id))
        self.assertIn(order, vendor_orders)

        # Verify OrderSerializer output
        ser_data = OrderSerializer(order).data
        self.assertEqual(ser_data['customer'], self.customer.id)
        self.assertEqual(ser_data['customer_email'], "customer_db@test.com")
        self.assertEqual(ser_data['vendor'], self.vendor_a.id)
        self.assertEqual(ser_data['vendor_email'], "vendor_a_db@test.com")

    def test_sales_memo_database_level_vendor_and_customer(self):
        """SalesMemo must contain direct database foreign keys for both customer and vendor."""
        card = CardRepository.get_or_create_active_card_for_user(
            user=self.customer, store=self.store_a
        )
        CardRepository.add_item_to_card(card, self.product_a, Decimal('1.000'))
        order = OrderService.submit_order_from_card(
            card=card, customer=self.customer, fulfillment_type=FulfillmentType.WALK_IN
        )

        # Vendor hands over products and issues sales memo
        completed_order = OrderService.handover_order(
            order=order, actor=self.vendor_a, payment_collected=True
        )

        sales_memo = SalesMemo.objects.filter(order=completed_order).first()
        self.assertIsNotNone(sales_memo)

        # Direct database checks
        self.assertEqual(sales_memo.customer, self.customer)
        self.assertEqual(sales_memo.vendor, self.vendor_a)
        self.assertEqual(sales_memo.user, self.customer)  # Property alias check

        # Verify DB query directly on customer and vendor
        db_memo = SalesMemo.objects.filter(pk=sales_memo.id, customer=self.customer, vendor=self.vendor_a).first()
        self.assertIsNotNone(db_memo)

        # Verify SalesMemoSerializer output
        ser_data = SalesMemoSerializer(sales_memo).data
        self.assertEqual(ser_data['customer'], self.customer.id)
        self.assertEqual(ser_data['customer_email'], "customer_db@test.com")
        self.assertEqual(ser_data['vendor'], self.vendor_a.id)
        self.assertEqual(ser_data['vendor_email'], "vendor_a_db@test.com")

    def test_vendor_can_query_store_cards_via_api(self):
        """Vendor can list cards targeted at their store using ?as_vendor=true."""
        # Create a walk-in card at store A
        card_a = CardRepository.get_or_create_active_card_for_user(
            user=self.customer, store=self.store_a, shopping_mode=ShoppingMode.WALK_IN
        )
        CardRepository.add_item_to_card(card_a, self.product_a, Decimal('3.000'))

        # Vendor A queries cards as vendor
        self.client.force_authenticate(user=self.vendor_a)
        response = self.client.get('/cards/?as_vendor=true')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data.get('data', response.data) if isinstance(response.data, dict) else response.data
        if isinstance(results, dict) and 'results' in results:
            results = results['results']

        card_ids = [c['id'] for c in results]
        self.assertIn(card_a.id, card_ids)

        # Vendor B queries cards as vendor — should not see Vendor A's card
        self.client.force_authenticate(user=self.vendor_b)
        response_b = self.client.get('/cards/?as_vendor=true')
        self.assertEqual(response_b.status_code, status.HTTP_200_OK)

        results_b = response_b.data.get('data', response_b.data) if isinstance(response_b.data, dict) else response_b.data
        if isinstance(results_b, dict) and 'results' in results_b:
            results_b = results_b['results']

        card_ids_b = [c['id'] for c in results_b]
        self.assertNotIn(card_a.id, card_ids_b)
