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


class InStoreAislePickingTests(APITestCase):
    """
    Test suite for in-store shelf location, aisle route organization,
    and basket picking checklist.
    """

    def setUp(self):
        self.vendor = User.objects.create_user(
            email="vendor_aisle@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.customer = User.objects.create_user(
            email="shopper_aisle@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )
        self.other_customer = User.objects.create_user(
            email="other_aisle@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )

        self.store = Store.objects.create(
            name="Super Mega Mart",
            vendor=self.vendor,
            address="Level 1, City Center",
            is_active=True
        )

        # Products located across distinct aisles in physical store layout
        self.p_dairy = Product.objects.create(
            store=self.store,
            name="Farm Fresh Milk 1L",
            price=Decimal('80.00'),
            stock=Decimal('100.000'),
            aisle="Aisle 1 - Dairy",
            shelf_location="Cooler Rack 2"
        )
        self.p_produce = Product.objects.create(
            store=self.store,
            name="Red Organic Apples 1kg",
            price=Decimal('150.00'),
            stock=Decimal('50.000'),
            aisle="Aisle 2 - Produce",
            shelf_location="Fresh Bin 4"
        )
        self.p_bakery = Product.objects.create(
            store=self.store,
            name="Whole Wheat Bread 400g",
            price=Decimal('55.00'),
            stock=Decimal('40.000'),
            aisle="Aisle 3 - Bakery",
            shelf_location="Bread Stand 1"
        )

    def test_products_with_aisle_and_shelf_location(self):
        self.client.force_authenticate(user=self.customer)

        res = self.client.get(f'/products/api/{self.p_dairy.id}/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertEqual(data['aisle'], "Aisle 1 - Dairy")
        self.assertEqual(data['shelf_location'], "Cooler Rack 2")

    def test_in_store_memo_shows_aisle_shelf_and_picking_progress(self):
        self.client.force_authenticate(user=self.customer)

        card = CardService.get_or_create_active_memo(
            user=self.customer,
            store=self.store,
            shopping_mode='walk_in'
        )

        item1 = CardService.add_product_to_card(card.id, self.p_dairy.id, Decimal('2'), actor=self.customer)
        item2 = CardService.add_product_to_card(card.id, self.p_produce.id, Decimal('1'), actor=self.customer)
        item3 = CardService.add_product_to_card(card.id, self.p_bakery.id, Decimal('1'), actor=self.customer)

        res = self.client.get(f'/cards/{card.id}/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        card_data = res.json()['data']

        self.assertEqual(card_data['total_items_count'], 3)
        self.assertEqual(card_data['picked_items_count'], 0)
        self.assertFalse(card_data['is_fully_picked'])
        self.assertEqual(card_data['picking_progress_percent'], 0.0)

        # Verify aisle snapshots on items
        items = card_data['items']
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0]['aisle'], "Aisle 1 - Dairy")
        self.assertEqual(items[0]['shelf_location'], "Cooler Rack 2")
        self.assertFalse(items[0]['is_picked'])
        self.assertIsNone(items[0]['picked_at'])

    def test_toggle_item_picked_status(self):
        self.client.force_authenticate(user=self.customer)

        card = CardService.get_or_create_active_memo(
            user=self.customer,
            store=self.store,
            shopping_mode='walk_in'
        )
        item1 = CardService.add_product_to_card(card.id, self.p_dairy.id, Decimal('1'), actor=self.customer)
        item2 = CardService.add_product_to_card(card.id, self.p_produce.id, Decimal('1'), actor=self.customer)

        # 1. Customer physically places item1 into basket
        res_pick1 = self.client.post(
            f'/cards/{card.id}/toggle-item-picked/',
            {'item_id': item1.id, 'is_picked': True},
            format='json'
        )
        self.assertEqual(res_pick1.status_code, status.HTTP_200_OK)
        data1 = res_pick1.json()['data']
        self.assertTrue(data1['item']['is_picked'])
        self.assertIsNotNone(data1['item']['picked_at'])
        self.assertEqual(data1['picked_items_count'], 1)
        self.assertEqual(data1['total_items_count'], 2)
        self.assertEqual(data1['picking_progress_percent'], 50.0)
        self.assertFalse(data1['is_fully_picked'])

        # 2. Customer places item2 into basket -> 100% complete
        res_pick2 = self.client.post(
            f'/cards/{card.id}/toggle-item-picked/',
            {'item_id': item2.id, 'is_picked': True},
            format='json'
        )
        self.assertEqual(res_pick2.status_code, status.HTTP_200_OK)
        data2 = res_pick2.json()['data']
        self.assertTrue(data2['item']['is_picked'])
        self.assertEqual(data2['picked_items_count'], 2)
        self.assertEqual(data2['picking_progress_percent'], 100.0)
        self.assertTrue(data2['is_fully_picked'])

        # 3. Un-pick (e.g. put back on shelf)
        res_unpick = self.client.post(
            f'/cards/{card.id}/toggle-item-picked/',
            {'item_id': item1.id, 'is_picked': False},
            format='json'
        )
        self.assertEqual(res_unpick.status_code, status.HTTP_200_OK)
        data3 = res_unpick.json()['data']
        self.assertFalse(data3['item']['is_picked'])
        self.assertIsNone(data3['item']['picked_at'])
        self.assertEqual(data3['picked_items_count'], 1)
        self.assertEqual(data3['picking_progress_percent'], 50.0)

    def test_batch_pick_items(self):
        self.client.force_authenticate(user=self.customer)

        card = CardService.get_or_create_active_memo(
            user=self.customer,
            store=self.store,
            shopping_mode='walk_in'
        )
        item1 = CardService.add_product_to_card(card.id, self.p_dairy.id, Decimal('1'), actor=self.customer)
        item2 = CardService.add_product_to_card(card.id, self.p_produce.id, Decimal('1'), actor=self.customer)
        item3 = CardService.add_product_to_card(card.id, self.p_bakery.id, Decimal('1'), actor=self.customer)

        # Batch mark item1 and item3 as picked
        res_batch = self.client.post(
            f'/cards/{card.id}/batch-pick/',
            {'item_ids': [item1.id, item3.id], 'is_picked': True},
            format='json'
        )
        self.assertEqual(res_batch.status_code, status.HTTP_200_OK)
        data = res_batch.json()['data']
        self.assertEqual(data['picked_items_count'], 2)
        self.assertEqual(data['total_items_count'], 3)
        self.assertEqual(data['picking_progress_percent'], 66.7)

    def test_walking_aisle_route_sorting(self):
        self.client.force_authenticate(user=self.customer)

        card = CardService.get_or_create_active_memo(
            user=self.customer,
            store=self.store,
            shopping_mode='walk_in'
        )
        # Added out of physical aisle order: Bakery (Aisle 3), Dairy (Aisle 1), Produce (Aisle 2)
        item_bakery = CardService.add_product_to_card(card.id, self.p_bakery.id, Decimal('1'), actor=self.customer)
        item_dairy = CardService.add_product_to_card(card.id, self.p_dairy.id, Decimal('1'), actor=self.customer)
        item_produce = CardService.add_product_to_card(card.id, self.p_produce.id, Decimal('1'), actor=self.customer)

        # Query with sort_by=aisle
        res_sorted = self.client.get(f'/cards/{card.id}/?sort_by=aisle')
        self.assertEqual(res_sorted.status_code, status.HTTP_200_OK)
        items = res_sorted.json()['data']['items']

        # Verifies items sequence follows physical store layout: Aisle 1 -> Aisle 2 -> Aisle 3
        self.assertEqual(items[0]['aisle'], "Aisle 1 - Dairy")
        self.assertEqual(items[1]['aisle'], "Aisle 2 - Produce")
        self.assertEqual(items[2]['aisle'], "Aisle 3 - Bakery")

        # Also via GET /cards/active/?store_id=...&sort_by=aisle
        res_active_sorted = self.client.get(f'/cards/active/?store_id={self.store.id}&sort_by=aisle')
        self.assertEqual(res_active_sorted.status_code, status.HTTP_200_OK)
        active_items = res_active_sorted.json()['data']['items']
        self.assertEqual(active_items[0]['aisle'], "Aisle 1 - Dairy")
        self.assertEqual(active_items[1]['aisle'], "Aisle 2 - Produce")
        self.assertEqual(active_items[2]['aisle'], "Aisle 3 - Bakery")

    def test_picking_tenant_isolation(self):
        card = CardService.get_or_create_active_memo(
            user=self.customer,
            store=self.store,
            shopping_mode='walk_in'
        )
        item = CardService.add_product_to_card(card.id, self.p_dairy.id, Decimal('1'), actor=self.customer)

        # Other customer attempts to toggle picked status
        self.client.force_authenticate(user=self.other_customer)
        res_toggle = self.client.post(
            f'/cards/{card.id}/toggle-item-picked/',
            {'item_id': item.id, 'is_picked': True},
            format='json'
        )
        self.assertIn(res_toggle.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

        res_batch = self.client.post(
            f'/cards/{card.id}/batch-pick/',
            {'item_ids': [item.id], 'is_picked': True},
            format='json'
        )
        self.assertIn(res_batch.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])
