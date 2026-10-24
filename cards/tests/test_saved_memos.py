"""
cards/tests/test_saved_memos.py — Tests for Saved "Buy Next Time" Store Memos

Verifies:
- Creating saved planning memos with custom title and planned visit dates.
- Moving active draft shopping memos to saved for later status.
- Activating saved memos with swap/merge strategies into the active store cart.
- Duplicating memos and all item snapshots.
- Scoped listing of saved planning memos via GET /cards/saved/.
- Tenant isolation and IDOR protection.
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from cards.models.card_mod import Card, ShoppingMode
from cards.repositories.card_repository import CardRepository
from cards.services.card_service import CardService
from categories.models.category_mod import Category
from inventory.services.inventory_service import InventoryService
from products.models.product_mod import Product
from shared.enums.enums import UserRoleEnum
from stores.models.store_mod import Store

User = get_user_model()


class SavedStoreMemosTests(APITestCase):
    def setUp(self):
        # Create users
        self.vendor = User.objects.create_user(
            email="vendor_saved@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.customer_a = User.objects.create_user(
            email="customer_a_saved@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )
        self.customer_b = User.objects.create_user(
            email="customer_b_saved@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )

        # Create store
        self.store = Store.objects.create(
            vendor=self.vendor,
            name="Apex Hardware & Supplies",
            address="742 Evergreen Terrace",
            delivery_fee=Decimal('10.00')
        )

        # Category and Products
        self.category = Category.objects.create(store=self.store, name="Tools")
        self.product_hammer = Product.objects.create(
            store=self.store, category=self.category, name="Claw Hammer", price=Decimal('25.00'), stock=50
        )
        self.product_nails = Product.objects.create(
            store=self.store, category=self.category, name="Steel Nails Box", price=Decimal('8.50'), stock=100
        )

        InventoryService.receive_stock(
            store=self.store, product=self.product_hammer, quantity=Decimal('50.000'), actor=self.vendor
        )
        InventoryService.receive_stock(
            store=self.store, product=self.product_nails, quantity=Decimal('100.000'), actor=self.vendor
        )

    def test_create_saved_memo_directly_via_api(self):
        """Customer can create a named planning memo for a future store visit."""
        self.client.force_authenticate(user=self.customer_a)
        payload = {
            "store_id": self.store.id,
            "title": "Weekend Home Renovation Supplies",
            "planned_visit_date": "2026-11-05",
            "notes": "Pick up hammer and 2 boxes of steel nails at aisle 4",
            "shopping_mode": "walk_in"
        }
        res = self.client.post('/cards/create-saved/', payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res.data['data']['is_saved_for_later'])
        self.assertEqual(res.data['data']['title'], "Weekend Home Renovation Supplies")
        self.assertEqual(res.data['data']['planned_visit_date'], "2026-11-05")
        self.assertEqual(res.data['data']['vendor'], self.vendor.id)

    def test_save_active_memo_for_later(self):
        """Customer can move an active shopping memo with items to saved for later status."""
        active_card = CardRepository.get_or_create_active_card_for_user(
            user=self.customer_a, store=self.store
        )
        CardRepository.add_item_to_card(active_card, self.product_hammer, Decimal('1.000'))

        self.client.force_authenticate(user=self.customer_a)
        res = self.client.post(
            f'/cards/{active_card.id}/save-for-later/',
            {"title": "Deferred Tool Shopping", "planned_visit_date": "2026-11-10"},
            format='json'
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        active_card.refresh_from_db()
        self.assertTrue(active_card.is_saved_for_later)
        self.assertEqual(active_card.title, "Deferred Tool Shopping")

        # Verify active card endpoint now creates/returns a new active card since previous is saved
        res_active = self.client.get(f'/cards/active/?store_id={self.store.id}')
        self.assertEqual(res_active.status_code, status.HTTP_200_OK)
        new_active_id = res_active.data['data']['id']
        self.assertNotEqual(new_active_id, active_card.id)

    def test_activate_saved_memo_swaps_active(self):
        """Activating a saved memo swaps it with the currently active non-empty memo so no items are lost."""
        # 1. Existing active card has nails
        active_card = CardRepository.get_or_create_active_card_for_user(
            user=self.customer_a, store=self.store, title="Current Active Cart"
        )
        CardRepository.add_item_to_card(active_card, self.product_nails, Decimal('2.000'))

        # 2. Saved card has hammer
        saved_card = CardService.create_saved_memo(
            user=self.customer_a,
            store=self.store,
            title="Saved Hammer List"
        )
        CardRepository.add_item_to_card(saved_card, self.product_hammer, Decimal('1.000'))

        # 3. Activate saved card
        self.client.force_authenticate(user=self.customer_a)
        res = self.client.post(f'/cards/{saved_card.id}/activate/', {"strategy": "swap"}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        saved_card.refresh_from_db()
        active_card.refresh_from_db()

        # The saved card is now active
        self.assertFalse(saved_card.is_saved_for_later)
        # The previous active card was safely swapped to saved_for_later
        self.assertTrue(active_card.is_saved_for_later)

    def test_activate_saved_memo_merge_strategy(self):
        """Activating with strategy='merge' combines items into active memo."""
        active_card = CardRepository.get_or_create_active_card_for_user(
            user=self.customer_a, store=self.store
        )
        CardRepository.add_item_to_card(active_card, self.product_nails, Decimal('2.000'))

        saved_card = CardService.create_saved_memo(
            user=self.customer_a, store=self.store, title="Saved List"
        )
        CardRepository.add_item_to_card(saved_card, self.product_hammer, Decimal('1.000'))

        self.client.force_authenticate(user=self.customer_a)
        res = self.client.post(f'/cards/{saved_card.id}/activate/', {"strategy": "merge"}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        active_card.refresh_from_db()
        item_product_ids = [item.product.id for item in active_card.items.all()]
        self.assertIn(self.product_nails.id, item_product_ids)
        self.assertIn(self.product_hammer.id, item_product_ids)

    def test_duplicate_memo(self):
        """Duplicating a memo creates a distinct copy with all items."""
        card = CardRepository.get_or_create_active_card_for_user(user=self.customer_a, store=self.store)
        CardRepository.add_item_to_card(card, self.product_hammer, Decimal('2.000'))

        self.client.force_authenticate(user=self.customer_a)
        res = self.client.post(f'/cards/{card.id}/duplicate/', {"title": "Duplicated Tool List", "as_saved": True}, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        new_card_id = res.data['data']['id']
        self.assertNotEqual(new_card_id, card.id)
        self.assertTrue(res.data['data']['is_saved_for_later'])
        self.assertEqual(res.data['data']['title'], "Duplicated Tool List")

        new_card = CardRepository.get_by_id(new_card_id)
        self.assertEqual(new_card.items.count(), 1)
        self.assertEqual(new_card.items.first().product, self.product_hammer)

    def test_list_saved_memos_endpoint(self):
        """GET /cards/saved/?store_id=... returns only saved planning memos for the user."""
        saved_1 = CardService.create_saved_memo(user=self.customer_a, store=self.store, title="Plan 1")
        saved_2 = CardService.create_saved_memo(user=self.customer_a, store=self.store, title="Plan 2")
        active_memo = CardRepository.get_or_create_active_card_for_user(user=self.customer_a, store=self.store)

        self.client.force_authenticate(user=self.customer_a)
        res = self.client.get(f'/cards/saved/?store_id={self.store.id}')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        results = res.data.get('data', res.data) if isinstance(res.data, dict) else res.data
        if isinstance(results, dict) and 'results' in results:
            results = results['results']

        retrieved_ids = [c['id'] for c in results]
        self.assertIn(saved_1.id, retrieved_ids)
        self.assertIn(saved_2.id, retrieved_ids)
        self.assertNotIn(active_memo.id, retrieved_ids)

    def test_tenant_isolation_idor_on_saved_memos(self):
        """Customer B cannot save, activate, or duplicate Customer A's memo."""
        card_a = CardService.create_saved_memo(user=self.customer_a, store=self.store, title="Customer A Memo")

        self.client.force_authenticate(user=self.customer_b)
        # Attempt to save for later
        res_save = self.client.post(f'/cards/{card_a.id}/save-for-later/', {})
        self.assertIn(res_save.status_code, [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN])

        # Attempt to activate
        res_act = self.client.post(f'/cards/{card_a.id}/activate/', {})
        self.assertIn(res_act.status_code, [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN])

        # Attempt to duplicate
        res_dup = self.client.post(f'/cards/{card_a.id}/duplicate/', {})
        self.assertIn(res_dup.status_code, [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN])
