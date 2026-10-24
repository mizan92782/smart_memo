from decimal import Decimal
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from users.models.user_mod import User
from stores.models.store_mod import Store
from products.models.product_mod import Product
from cards.models.card_mod import Card
from cards.repositories.card_repository import CardRepository
from cards.services.card_service import CardService
from inventory.services.inventory_service import InventoryService
from orders.models.order_mod import Order, OrderStatus
from shared.enums.enums import UserRoleEnum


class MemoManagementTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Vendor & Store
        self.vendor = User.objects.create_user(
            email="memo_v@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.store = Store.objects.create(
            vendor=self.vendor,
            name="Memo Grocery",
            delivery_fee=Decimal('15.00')
        )

        # Products with inventory stock
        self.prod1 = Product.objects.create(
            store=self.store,
            name="Almond Milk",
            price=Decimal('150.00'),
            stock=0
        )
        InventoryService.receive_stock(self.store, self.prod1, Decimal('30.000'))

        self.prod2 = Product.objects.create(
            store=self.store,
            name="Brown Eggs 12pc",
            price=Decimal('120.00'),
            stock=0
        )
        InventoryService.receive_stock(self.store, self.prod2, Decimal('40.000'))

        # Customer 1
        self.customer = User.objects.create_user(
            email="memo_c1@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )

        # Customer 2 (for IDOR tests)
        self.other_customer = User.objects.create_user(
            email="memo_c2@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )

    def test_get_or_create_active_memo(self):
        self.client.force_authenticate(user=self.customer)
        res = self.client.get("/cards/active/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        card_data = res.data['data']
        self.assertIsNotNone(card_data['id'])
        self.assertFalse(card_data['is_completed'])
        self.assertEqual(len(card_data['items']), 0)

        # Calling active again returns the same active card
        res2 = self.client.get("/cards/active/")
        self.assertEqual(res2.data['data']['id'], card_data['id'])

    def test_add_update_remove_and_clear_items(self):
        self.client.force_authenticate(user=self.customer)
        active_res = self.client.get("/cards/active/")
        card_id = active_res.data['data']['id']

        # 1. Add item 1
        res = self.client.post(f"/cards/{card_id}/add-item/", {'product_id': self.prod1.id, 'quantity': '2.0'})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        item1_id = res.data['data']['item_id']

        # 2. Add item 2
        res2 = self.client.post(f"/cards/{card_id}/add-item/", {'product_id': self.prod2.id, 'quantity': '1.0'})
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)
        item2_id = res2.data['data']['item_id']

        # Verify memo total price: 2 * 150 + 1 * 120 = 420
        memo_res = self.client.get(f"/cards/{card_id}/")
        self.assertEqual(Decimal(str(memo_res.data['data']['total_price'])), Decimal('420.00'))
        self.assertEqual(memo_res.data['data']['store'], self.store.id)

        # 3. Update quantity of item 1 from 2 to 3
        res3 = self.client.post(f"/cards/{card_id}/update-item/", {'item_id': item1_id, 'quantity': '3.0'})
        self.assertEqual(res3.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(str(res3.data['data']['quantity'])), Decimal('3.00'))

        memo_res = self.client.get(f"/cards/{card_id}/")
        # 3 * 150 + 1 * 120 = 570
        self.assertEqual(Decimal(str(memo_res.data['data']['total_price'])), Decimal('570.00'))

        # 4. Remove item 2
        res4 = self.client.post(f"/cards/{card_id}/remove-item/", {'item_id': item2_id})
        self.assertEqual(res4.status_code, status.HTTP_200_OK)

        memo_res = self.client.get(f"/cards/{card_id}/")
        self.assertEqual(len(memo_res.data['data']['items']), 1)
        self.assertEqual(Decimal(str(memo_res.data['data']['total_price'])), Decimal('450.00'))

        # 5. Clear memo
        res5 = self.client.post(f"/cards/{card_id}/clear/")
        self.assertEqual(res5.status_code, status.HTTP_200_OK)

        memo_res = self.client.get(f"/cards/{card_id}/")
        self.assertEqual(len(memo_res.data['data']['items']), 0)
        self.assertIsNone(memo_res.data['data']['store'])

    def test_cross_customer_memo_idor_isolation(self):
        # Customer 1 creates an active memo with items
        self.client.force_authenticate(user=self.customer)
        active_res = self.client.get("/cards/active/")
        card_id = active_res.data['data']['id']
        self.client.post(f"/cards/{card_id}/add-item/", {'product_id': self.prod1.id, 'quantity': 1})

        # Customer 2 attempts to view Customer 1's memo
        self.client.force_authenticate(user=self.other_customer)
        res = self.client.get(f"/cards/{card_id}/")
        self.assertIn(res.status_code, [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN])

        # Customer 2 attempts to add item to Customer 1's memo
        res_add = self.client.post(f"/cards/{card_id}/add-item/", {'product_id': self.prod2.id, 'quantity': 1})
        self.assertIn(res_add.status_code, [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN])

        # Customer 2 attempts to clear Customer 1's memo
        res_clear = self.client.post(f"/cards/{card_id}/clear/")
        self.assertIn(res_clear.status_code, [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN])

    def test_unauthenticated_access_is_blocked(self):
        res = self.client.get("/cards/")
        self.assertIn(res.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

        res_active = self.client.get("/cards/active/")
        self.assertIn(res_active.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_checkout_revalidates_expired_offer_and_recalculates_price(self):
        # Product with an offer expiring in the past
        past_time = timezone.now() - timedelta(days=2)
        expired_product = Product.objects.create(
            store=self.store,
            name="Promo Juice",
            price=Decimal('100.00'),
            offer=True,
            offered_discount=Decimal('20.00'),  # offered_price = 80.00
            offer_start_date=past_time - timedelta(days=5),
            offer_end_date=past_time,  # EXPIRED
            stock=0
        )
        InventoryService.receive_stock(self.store, expired_product, Decimal('10.000'))

        self.client.force_authenticate(user=self.customer)
        card = CardRepository.create_card(user=self.customer, store=self.store)

        # Manually create card item with stale discounted price of 80.00
        item = CardRepository.add_item_to_card(card, expired_product, Decimal('2.000'), unit_price=Decimal('80.00'))
        self.assertEqual(item.unit_price, Decimal('80.00'))

        # Checkout executes revalidation against catalog
        res = self.client.post(
            f"/cards/{card.id}/checkout/",
            {'fulfillment_type': 'pickup'},
            format='json'
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # Effective price for expired product reverted to base price (100.00)
        # Total for 2 units = 2 * 100.00 = 200.00
        order_data = res.data['data']
        self.assertEqual(Decimal(str(order_data['subtotal'])), Decimal('200.00'))
        self.assertEqual(Decimal(str(order_data['total_amount'])), Decimal('200.00'))
