from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from users.models.user_mod import User
from stores.models.store_mod import Store
from products.models.product_mod import Product
from cards.repositories.card_repository import CardRepository
from cards.services.card_service import CardService
from inventory.services.inventory_service import InventoryService
from orders.models.order_mod import Order, OrderStatus
from shared.enums.enums import UserRoleEnum


class CardCheckoutTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Vendor & Store
        self.vendor = User.objects.create_user(
            email="vendor_chk@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.store = Store.objects.create(
            vendor=self.vendor,
            name="Checkout Mart",
            delivery_fee=Decimal('20.00'),
            is_active=True
        )

        # Products with inventory stock
        self.product = Product.objects.create(
            store=self.store,
            name="Organic Milk 1L",
            price=Decimal('90.00'),
            stock=0
        )
        InventoryService.receive_stock(self.store, self.product, Decimal('20.000'))

        # Customer A
        self.customer = User.objects.create_user(
            email="customer_chk@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )
        self.card = CardRepository.create_card(user_id=self.customer.id, store=self.store, title="Weekly Groceries")
        CardService.add_product_to_card(self.card.id, self.product.id, Decimal('2.000'))

        # Customer B (for isolation tests)
        self.customer_b = User.objects.create_user(
            email="customer_chk_b@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )

    def test_authenticated_customer_checkout_success(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(
            f'/cards/{self.card.id}/checkout/',
            {
                'fulfillment_type': 'delivery',
                'delivery_address': 'Flat 4B, Green Road, Dhaka',
                'notes': 'Call upon arrival'
            },
            format='json'
        )
        self.assertEqual(response.status_code, 201)
        order_data = response.data['data']
        self.assertIsNotNone(order_data['id'])
        self.assertEqual(order_data['status'], OrderStatus.SUBMITTED)
        self.assertEqual(Decimal(str(order_data['total_amount'])), Decimal('200.00'))  # 2 * 90 + 20 fee

        # Verify stock reservation
        balance = self.product.stock_balance
        balance.refresh_from_db()
        self.assertEqual(balance.reserved, Decimal('2.000'))
        self.assertEqual(balance.available, Decimal('18.000'))

        # Verify card completed
        self.card.refresh_from_db()
        self.assertTrue(self.card.is_completed)

    def test_customer_cannot_checkout_another_users_card(self):
        # Customer B tries to checkout Customer A's card
        self.client.force_authenticate(user=self.customer_b)
        response = self.client.post(
            f'/cards/{self.card.id}/checkout/',
            {'fulfillment_type': 'pickup'},
            format='json'
        )
        self.assertEqual(response.status_code, 403)

    def test_cannot_checkout_already_completed_card(self):
        self.card.is_completed = True
        self.card.save()

        self.client.force_authenticate(user=self.customer)
        response = self.client.post(
            f'/cards/{self.card.id}/checkout/',
            {'fulfillment_type': 'pickup'},
            format='json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("already been checked out", response.data['message'])

    def test_delivery_without_address_fails(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(
            f'/cards/{self.card.id}/checkout/',
            {
                'fulfillment_type': 'delivery',
                'delivery_address': ''
            },
            format='json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("delivery_address is required", response.data['message'])
