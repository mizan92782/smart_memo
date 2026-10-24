from decimal import Decimal
from django.test import TestCase
from users.models.user_mod import User
from stores.models.store_mod import Store
from products.models.product_mod import Product
from cards.models.card_mod import Card
from cards.repositories.card_repository import CardRepository
from cards.services.card_service import CardService
from shared.enums.enums import UserRoleEnum


class CardModelAndServiceTests(TestCase):
    def setUp(self):
        self.vendor_a = User.objects.create_user(
            email="card_v_a@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.store_a = Store.objects.create(vendor=self.vendor_a, name="Store A")
        self.prod_a1 = Product.objects.create(store=self.store_a, name="Bread", price=40.00, stock=20)
        self.prod_a2 = Product.objects.create(store=self.store_a, name="Butter", price=120.00, stock=10)

        self.vendor_b = User.objects.create_user(
            email="card_v_b@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.store_b = Store.objects.create(vendor=self.vendor_b, name="Store B")
        self.prod_b = Product.objects.create(store=self.store_b, name="Jam", price=90.00, stock=15)

        self.customer = User.objects.create_user(
            email="card_cust@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )
        self.card = CardRepository.create_card(user_id=self.customer.id, title="Customer Memo")

    def test_add_items_from_same_store_succeeds(self):
        item1 = CardService.add_product_to_card(self.card.id, self.prod_a1.id, Decimal('2'))
        item2 = CardService.add_product_to_card(self.card.id, self.prod_a2.id, Decimal('1'))

        self.card.refresh_from_db()
        self.assertEqual(self.card.store, self.store_a)
        self.assertEqual(self.card.items.count(), 2)
        # Total price: 2 * 40 + 1 * 120 = 200
        self.assertEqual(self.card.total_price, Decimal('200.00'))

    def test_cannot_add_items_from_different_stores_to_same_card(self):
        CardService.add_product_to_card(self.card.id, self.prod_a1.id, Decimal('1'))
        with self.assertRaises(ValueError):
            CardService.add_product_to_card(self.card.id, self.prod_b.id, Decimal('1'))

    def test_draft_memo_does_not_deduct_inventory_stock(self):
        initial_stock = self.prod_a1.stock
        CardService.add_product_to_card(self.card.id, self.prod_a1.id, Decimal('5'))
        self.prod_a1.refresh_from_db()
        self.assertEqual(self.prod_a1.stock, initial_stock)
