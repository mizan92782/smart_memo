from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from shared.enums.enums import UserRoleEnum
from stores.models.store_mod import Store
from products.models.product_mod import Product
from cards.models.card_mod import Card
from cards.services.card_service import CardService

User = get_user_model()


class StoreComparisonAndBudgetTests(APITestCase):
    """
    Test suite for shopping memo budget controls, cross-store price/stock
    comparison, and 1-tap cross-store memo transfer.
    """

    def setUp(self):
        # Two distinct vendors and stores
        self.vendor_a = User.objects.create_user(
            email="vendor_a_cmp@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.vendor_b = User.objects.create_user(
            email="vendor_b_cmp@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.customer = User.objects.create_user(
            email="shopper_cmp@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )
        self.other_customer = User.objects.create_user(
            email="other_cmp@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )

        self.store_a = Store.objects.create(
            name="Green Valley Mart",
            vendor=self.vendor_a,
            address="Gulshan 1, Dhaka",
            is_active=True
        )
        self.store_b = Store.objects.create(
            name="City Discount Store",
            vendor=self.vendor_b,
            address="Gulshan 2, Dhaka",
            is_active=True
        )

        # Products in Store A
        self.prod_a_milk = Product.objects.create(
            store=self.store_a,
            name="Full Cream Milk 1L",
            barcode="890123450001",
            sku="SKU-MILK-1L",
            price=Decimal('90.00'),
            stock=Decimal('50.000')
        )
        self.prod_a_cereal = Product.objects.create(
            store=self.store_a,
            name="Corn Flakes 500g",
            barcode="890123450002",
            sku="SKU-CORN-500",
            price=Decimal('180.00'),
            stock=Decimal('30.000')
        )
        self.prod_a_exclusive = Product.objects.create(
            store=self.store_a,
            name="Store A Exclusive Herbal Tea",
            barcode="890123450099",
            sku="SKU-TEA-HERBAL",
            price=Decimal('250.00'),
            stock=Decimal('10.000')
        )

        # Products in Store B (Cheaper Milk, slightly more expensive cereal, no exclusive tea)
        self.prod_b_milk = Product.objects.create(
            store=self.store_b,
            name="Full Cream Milk 1L",
            barcode="890123450001",
            sku="SKU-MILK-1L-B",
            price=Decimal('80.00'),  # 10 BDT cheaper
            stock=Decimal('100.000')
        )
        self.prod_b_cereal = Product.objects.create(
            store=self.store_b,
            name="Corn Flakes 500g",
            barcode="890123450002",
            sku="SKU-CORN-500-B",
            price=Decimal('160.00'),  # 20 BDT cheaper
            stock=Decimal('40.000')
        )

    def test_set_and_update_memo_budget_limit(self):
        self.client.force_authenticate(user=self.customer)

        card = CardService.get_or_create_active_memo(
            user=self.customer,
            store=self.store_a,
            shopping_mode='walk_in'
        )

        # 1. Set budget limit to 300.00
        res_budget = self.client.patch(
            f'/cards/{card.id}/set-budget/',
            {'budget_limit': '300.00'},
            format='json'
        )
        self.assertEqual(res_budget.status_code, status.HTTP_200_OK)
        card_data = res_budget.json()['data']
        self.assertEqual(card_data['budget_limit'], '300.00')
        self.assertEqual(card_data['budget_remaining'], '300.00')
        self.assertFalse(card_data['is_over_budget'])
        self.assertEqual(card_data['budget_used_percent'], 0.0)

        # 2. Add milk (90.00) -> 30.0% used, 210.00 remaining
        CardService.add_product_to_card(card.id, self.prod_a_milk.id, Decimal('1'), actor=self.customer)
        res_view = self.client.get(f'/cards/{card.id}/')
        data = res_view.json()['data']
        self.assertEqual(data['total_price'], '90.00')
        self.assertEqual(data['budget_remaining'], '210.00')
        self.assertFalse(data['is_over_budget'])
        self.assertEqual(data['budget_used_percent'], 30.0)

        # 3. Add 2 cereals (360.00) -> Total = 450.00 -> OVER BUDGET by 150.00
        CardService.add_product_to_card(card.id, self.prod_a_cereal.id, Decimal('2'), actor=self.customer)
        res_view2 = self.client.get(f'/cards/{card.id}/')
        data2 = res_view2.json()['data']
        self.assertEqual(data2['total_price'], '450.00')
        self.assertEqual(data2['budget_remaining'], '-150.00')
        self.assertTrue(data2['is_over_budget'])
        self.assertEqual(data2['budget_used_percent'], 150.0)

        # 4. Clear budget limit
        res_clear = self.client.patch(
            f'/cards/{card.id}/set-budget/',
            {'budget_limit': None},
            format='json'
        )
        self.assertEqual(res_clear.status_code, status.HTTP_200_OK)
        data_clear = res_clear.json()['data']
        self.assertIsNone(data_clear['budget_limit'])
        self.assertIsNone(data_clear['budget_remaining'])
        self.assertFalse(data_clear['is_over_budget'])
        self.assertIsNone(data_clear['budget_used_percent'])

    def test_cross_store_price_and_availability_comparison(self):
        self.client.force_authenticate(user=self.customer)

        card = CardService.get_or_create_active_memo(
            user=self.customer,
            store=self.store_a,
            shopping_mode='remote'
        )
        # Milk x 2 (180.00 in Store A), Cereal x 1 (180.00 in Store A), Exclusive Tea x 1 (250.00 in Store A)
        CardService.add_product_to_card(card.id, self.prod_a_milk.id, Decimal('2'), actor=self.customer)
        CardService.add_product_to_card(card.id, self.prod_a_cereal.id, Decimal('1'), actor=self.customer)
        CardService.add_product_to_card(card.id, self.prod_a_exclusive.id, Decimal('1'), actor=self.customer)

        res_compare = self.client.post(
            f'/cards/{card.id}/compare-store/',
            {'target_store_id': self.store_b.id},
            format='json'
        )
        self.assertEqual(res_compare.status_code, status.HTTP_200_OK)
        comp = res_compare.json()['data']

        self.assertEqual(comp['source_store']['id'], self.store_a.id)
        self.assertEqual(comp['target_store']['id'], self.store_b.id)
        self.assertEqual(comp['total_items_in_memo'], 3)
        self.assertEqual(comp['matched_items_count'], 2)
        self.assertEqual(comp['missing_items_count'], 1)

        # Matched items in Store A: Milk (2 * 90 = 180) + Cereal (1 * 180 = 180) = 360.00
        # Matched items in Store B: Milk (2 * 80 = 160) + Cereal (1 * 160 = 160) = 320.00
        # Savings = 360.00 - 320.00 = 40.00
        self.assertEqual(comp['source_matched_total'], '360.00')
        self.assertEqual(comp['target_matched_total'], '320.00')
        self.assertEqual(comp['savings_at_target'], '40.00')
        self.assertTrue(comp['is_target_cheaper'])
        self.assertFalse(comp['can_fully_fulfill'])  # because tea is missing in Store B

        # Verify missing items list
        missing = comp['missing_items']
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0]['product_name'], "Store A Exclusive Herbal Tea")

    def test_transfer_memo_to_target_store_in_place(self):
        self.client.force_authenticate(user=self.customer)

        card = CardService.get_or_create_active_memo(
            user=self.customer,
            store=self.store_a,
            shopping_mode='walk_in'
        )
        CardService.add_product_to_card(card.id, self.prod_a_milk.id, Decimal('2'), actor=self.customer)
        CardService.add_product_to_card(card.id, self.prod_a_cereal.id, Decimal('1'), actor=self.customer)
        CardService.add_product_to_card(card.id, self.prod_a_exclusive.id, Decimal('1'), actor=self.customer)

        # 1. Attempt transfer with omit_missing=False -> Fails because tea is not carried
        res_fail = self.client.post(
            f'/cards/{card.id}/transfer-store/',
            {'target_store_id': self.store_b.id, 'omit_missing': False},
            format='json'
        )
        self.assertEqual(res_fail.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("does not carry 1 item(s)", res_fail.json()['message'])

        # 2. Transfer with omit_missing=True (default) -> In-place update to Store B
        res_transfer = self.client.post(
            f'/cards/{card.id}/transfer-store/',
            {'target_store_id': self.store_b.id, 'omit_missing': True, 'clone': False},
            format='json'
        )
        self.assertEqual(res_transfer.status_code, status.HTTP_200_OK)
        data = res_transfer.json()['data']

        self.assertEqual(data['id'], card.id)
        self.assertEqual(data['store'], self.store_b.id)
        self.assertEqual(data['vendor'], self.vendor_b.id)
        self.assertEqual(data['store_name'], "City Discount Store")
        # 2 items remain (exclusive tea was omitted)
        self.assertEqual(len(data['items']), 2)
        # 2 * 80 + 1 * 160 = 320.00
        self.assertEqual(data['total_price'], '320.00')

        # Check item product binding points to Store B's products
        item_products = [item['product']['id'] for item in data['items']]
        self.assertIn(self.prod_b_milk.id, item_products)
        self.assertIn(self.prod_b_cereal.id, item_products)
        self.assertNotIn(self.prod_a_milk.id, item_products)

    def test_clone_transfer_memo_to_target_store(self):
        self.client.force_authenticate(user=self.customer)

        card = CardService.get_or_create_active_memo(
            user=self.customer,
            store=self.store_a,
            title="Weekly Breakfast List"
        )
        CardService.add_product_to_card(card.id, self.prod_a_milk.id, Decimal('1'), actor=self.customer)

        # Clone transfer to Store B
        res_clone = self.client.post(
            f'/cards/{card.id}/transfer-store/',
            {'target_store_id': self.store_b.id, 'clone': True},
            format='json'
        )
        self.assertEqual(res_clone.status_code, status.HTTP_201_CREATED)
        new_card = res_clone.json()['data']

        # Original card unchanged
        self.assertNotEqual(new_card['id'], card.id)
        card.refresh_from_db()
        self.assertEqual(card.store_id, self.store_a.id)

        # New card belongs to Store B
        self.assertEqual(new_card['store'], self.store_b.id)
        self.assertEqual(new_card['vendor'], self.vendor_b.id)
        self.assertEqual(new_card['total_price'], '80.00')  # Store B's milk price

    def test_budget_and_transfer_tenant_isolation(self):
        card = CardService.get_or_create_active_memo(
            user=self.customer,
            store=self.store_a
        )
        CardService.add_product_to_card(card.id, self.prod_a_milk.id, Decimal('1'), actor=self.customer)

        # Other customer attempts to mutate or compare
        self.client.force_authenticate(user=self.other_customer)

        # 1. Set budget on other's card
        res_set = self.client.patch(
            f'/cards/{card.id}/set-budget/',
            {'budget_limit': '500.00'},
            format='json'
        )
        self.assertIn(res_set.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

        # 2. Compare other's card
        res_cmp = self.client.post(
            f'/cards/{card.id}/compare-store/',
            {'target_store_id': self.store_b.id},
            format='json'
        )
        self.assertIn(res_cmp.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

        # 3. Transfer other's card
        res_xfr = self.client.post(
            f'/cards/{card.id}/transfer-store/',
            {'target_store_id': self.store_b.id},
            format='json'
        )
        self.assertIn(res_xfr.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])
