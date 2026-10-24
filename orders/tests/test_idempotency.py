from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from users.models.user_mod import User
from stores.models.store_mod import Store
from products.models.product_mod import Product
from cards.models.card_mod import Card
from cards.repositories.card_repository import CardRepository
from cards.services.card_service import CardService
from inventory.services.inventory_service import InventoryService
from orders.services.order_service import OrderService
from shared.enums.enums import UserRoleEnum


class OrderIdempotencyAndSecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Vendor A & Store A
        self.vendor_a = User.objects.create_user(
            email="order_va@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.store_a = Store.objects.create(vendor=self.vendor_a, name="Store A")
        self.prod_a = Product.objects.create(store=self.store_a, name="Flour", price=50.00, stock=0)
        InventoryService.receive_stock(self.store_a, self.prod_a, Decimal('100.000'))

        # Vendor B & Store B
        self.vendor_b = User.objects.create_user(
            email="order_vb@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.store_b = Store.objects.create(vendor=self.vendor_b, name="Store B")
        self.prod_b = Product.objects.create(store=self.store_b, name="Sugar", price=80.00, stock=0)
        InventoryService.receive_stock(self.store_b, self.prod_b, Decimal('100.000'))

        # Customer A
        self.customer_a = User.objects.create_user(
            email="cust_a@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )
        self.card_a = CardRepository.create_card(user=self.customer_a, store=self.store_a)
        CardService.add_product_to_card(self.card_a.id, self.prod_a.id, Decimal('2.000'))

        # Customer B
        self.customer_b = User.objects.create_user(
            email="cust_b@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )

    def test_idempotent_order_submission_prevents_duplicate_reservations(self):
        key = "idemp-key-xyz-12345"
        order1 = OrderService.submit_order_from_card(
            self.card_a, self.customer_a, idempotency_key=key
        )
        # Attempt identical submission with same key
        order2 = OrderService.submit_order_from_card(
            self.card_a, self.customer_a, idempotency_key=key
        )
        self.assertEqual(order1.id, order2.id)

        # Ensure stock is reserved only ONCE (2 units, not 4)
        balance = self.prod_a.stock_balance
        balance.refresh_from_db()
        self.assertEqual(balance.reserved, Decimal('2.000'))

    def test_customer_cannot_see_other_customer_orders(self):
        order_a = OrderService.submit_order_from_card(self.card_a, self.customer_a)

        self.client.force_authenticate(user=self.customer_b)
        response = self.client.get('/orders/')
        self.assertEqual(response.status_code, 200)
        order_ids = [o['id'] for o in response.data['data']]
        self.assertNotIn(order_a.id, order_ids)

    def test_vendor_b_cannot_accept_vendor_a_order(self):
        order_a = OrderService.submit_order_from_card(self.card_a, self.customer_a)

        self.client.force_authenticate(user=self.vendor_b)
        response = self.client.post(f'/orders/{order_a.id}/accept/')
        # Returns 404 because filtered out of Vendor B's queryset
        self.assertEqual(response.status_code, 404)
