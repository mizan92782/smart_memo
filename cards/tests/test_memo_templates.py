"""
cards/tests/test_memo_templates.py — Tests for Store Routine Shopping Templates & One-Tap Memo Hydration

Verifies:
- Saving active shopping memo as a routine template (POST /cards/{id}/save-as-template/).
- Direct template creation, line item management, and CRUD (cards/templates/).
- Real-time stock status and dynamic catalog pricing reflection.
- One-tap hydration into draft memo with 'replace' and 'merge' strategies.
- Graceful omission of out-of-stock or inactive products during hydration.
- Cross-store product boundary enforcement.
- Multi-tenant IDOR protection and vendor-scoped oversight.
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from cards.models.card_mod import Card, CardItem, ShoppingMode
from cards.models.template_mod import StoreMemoTemplate, StoreMemoTemplateItem
from cards.repositories.card_repository import CardRepository
from categories.models.category_mod import Category
from inventory.services.inventory_service import InventoryService
from products.models.product_mod import Product
from shared.enums.enums import UserRoleEnum
from stores.models.store_mod import Store

User = get_user_model()


class StoreMemoTemplateTests(APITestCase):
    def setUp(self):
        # Create users
        self.vendor_1 = User.objects.create_user(
            email="vendor1_tmpl@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.vendor_2 = User.objects.create_user(
            email="vendor2_tmpl@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.customer_a = User.objects.create_user(
            email="customer_a_tmpl@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )
        self.customer_b = User.objects.create_user(
            email="customer_b_tmpl@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )

        # Create stores
        self.store_1 = Store.objects.create(
            vendor=self.vendor_1,
            name="Fresh Fields Market",
            address="100 Market St",
            delivery_fee=Decimal('5.00')
        )
        self.store_2 = Store.objects.create(
            vendor=self.vendor_2,
            name="Corner Hardware",
            address="200 Broadway",
            delivery_fee=Decimal('7.50')
        )

        # Categories
        self.cat_groceries = Category.objects.create(store=self.store_1, name="Groceries")
        self.cat_hardware = Category.objects.create(store=self.store_2, name="Hardware")

        # Products for Store 1
        self.prod_milk = Product.objects.create(
            store=self.store_1,
            category=self.cat_groceries,
            name="Organic Whole Milk 1L",
            price=Decimal('4.50'),
            stock=50,
            aisle="Dairy",
            shelf_location="D-02"
        )
        self.prod_eggs = Product.objects.create(
            store=self.store_1,
            category=self.cat_groceries,
            name="Farm Fresh Eggs 12pk",
            price=Decimal('5.00'),
            stock=40,
            aisle="Dairy",
            shelf_location="D-04"
        )
        self.prod_bread = Product.objects.create(
            store=self.store_1,
            category=self.cat_groceries,
            name="Sourdough Bread",
            price=Decimal('6.00'),
            stock=0,  # Out of stock
            aisle="Bakery",
            shelf_location="B-01"
        )

        # Stock balances
        InventoryService.receive_stock(
            store=self.store_1, product=self.prod_milk, quantity=Decimal('50.000'), actor=self.vendor_1
        )
        InventoryService.receive_stock(
            store=self.store_1, product=self.prod_eggs, quantity=Decimal('40.000'), actor=self.vendor_1
        )

        # Product for Store 2
        self.prod_wrench = Product.objects.create(
            store=self.store_2,
            category=self.cat_hardware,
            name="Adjustable Wrench",
            price=Decimal('15.00'),
            stock=20
        )
        InventoryService.receive_stock(
            store=self.store_2, product=self.prod_wrench, quantity=Decimal('20.000'), actor=self.vendor_2
        )

    def test_save_active_memo_as_routine_template(self):
        """Customer can save their active shopping memo with line items into a routine basket template."""
        card = CardRepository.get_or_create_active_card_for_user(
            user=self.customer_a, store=self.store_1
        )
        CardRepository.add_item_to_card(card, self.prod_milk, Decimal('2.000'))
        CardRepository.add_item_to_card(card, self.prod_eggs, Decimal('1.000'))

        self.client.force_authenticate(user=self.customer_a)
        res = self.client.post(
            f'/cards/{card.id}/save-as-template/',
            {
                "name": "Weekly Breakfast Routine",
                "description": "Milk and eggs every Monday morning",
                "is_favorite": True
            },
            format='json'
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.data['data']
        self.assertEqual(data['name'], "Weekly Breakfast Routine")
        self.assertTrue(data['is_favorite'])
        self.assertEqual(data['store'], self.store_1.id)
        self.assertEqual(data['vendor'], self.vendor_1.id)
        self.assertEqual(data['total_items_count'], 2)
        # 2 * 4.50 + 1 * 5.00 = 14.00
        self.assertEqual(Decimal(data['estimated_total']), Decimal('14.00'))

        template = StoreMemoTemplate.objects.get(id=data['id'])
        self.assertEqual(template.items.count(), 2)
        self.assertEqual(template.vendor_id, self.vendor_1.id)

    def test_cannot_save_empty_memo_as_template(self):
        """Saving an empty memo as template raises validation error."""
        card = CardRepository.get_or_create_active_card_for_user(
            user=self.customer_a, store=self.store_1
        )
        self.client.force_authenticate(user=self.customer_a)
        res = self.client.post(
            f'/cards/{card.id}/save-as-template/',
            {"name": "Empty Routine"},
            format='json'
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("empty", str(res.data['message']).lower())

    def test_crud_routine_template_via_api(self):
        """Customer can create, read, update, and delete routine templates via /cards/templates/."""
        self.client.force_authenticate(user=self.customer_a)

        # 1. Create Template directly
        create_res = self.client.post(
            '/cards/templates/',
            {
                "store_id": self.store_1.id,
                "name": "Baking Staples",
                "description": "Essential baking ingredients",
                "shopping_mode": "walk_in",
                "is_favorite": True
            },
            format='json'
        )
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED)
        template_id = create_res.data['data']['id']
        self.assertEqual(create_res.data['data']['vendor'], self.vendor_1.id)

        # 2. Add Item to Template
        add_item_res = self.client.post(
            f'/cards/templates/{template_id}/add-item/',
            {
                "product_id": self.prod_milk.id,
                "quantity": "3.000",
                "notes": "Prefer latest expiration date"
            },
            format='json'
        )
        self.assertEqual(add_item_res.status_code, status.HTTP_200_OK)
        self.assertEqual(add_item_res.data['data']['total_items_count'], 1)
        item_id = add_item_res.data['data']['items'][0]['id']

        # 3. List Templates
        list_res = self.client.get(f'/cards/templates/?store_id={self.store_1.id}')
        self.assertEqual(list_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_res.data['data']), 1)

        # 4. Partial update template
        patch_res = self.client.patch(
            f'/cards/templates/{template_id}/',
            {"description": "Updated baking essentials description"},
            format='json'
        )
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.data['data']['description'], "Updated baking essentials description")

        # 5. Remove Item from Template
        remove_res = self.client.delete(f'/cards/templates/{template_id}/items/{item_id}/')
        self.assertEqual(remove_res.status_code, status.HTTP_200_OK)
        self.assertEqual(remove_res.data['data']['total_items_count'], 0)

        # 6. Delete Template (Soft Delete)
        del_res = self.client.delete(f'/cards/templates/{template_id}/')
        self.assertEqual(del_res.status_code, status.HTTP_200_OK)

        tmpl = StoreMemoTemplate.objects.get(id=template_id)
        self.assertTrue(tmpl.is_deleted)

    def test_cannot_add_foreign_store_product_to_template(self):
        """Cannot add a product from another vendor store into this store's routine template."""
        self.client.force_authenticate(user=self.customer_a)
        create_res = self.client.post(
            '/cards/templates/',
            {"store_id": self.store_1.id, "name": "Store 1 Template"},
            format='json'
        )
        template_id = create_res.data['data']['id']

        # Attempt to add wrench from Store 2 into Store 1 template
        res = self.client.post(
            f'/cards/templates/{template_id}/add-item/',
            {"product_id": self.prod_wrench.id, "quantity": 1},
            format='json'
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("does not belong", str(res.data['message']))

    def test_one_tap_hydration_replace_strategy(self):
        """Loading template with mode=replace clears existing memo items and loads template products."""
        # Setup Template with Milk (2) and Eggs (1)
        template = StoreMemoTemplate.objects.create(
            user=self.customer_a,
            store=self.store_1,
            vendor=self.vendor_1,
            name="Daily Breakfast",
            shopping_mode=ShoppingMode.REMOTE
        )
        StoreMemoTemplateItem.objects.create(template=template, product=self.prod_milk, quantity=Decimal('2.000'))
        StoreMemoTemplateItem.objects.create(template=template, product=self.prod_eggs, quantity=Decimal('1.000'))

        # Setup existing active memo with Eggs (5)
        card = CardRepository.get_or_create_active_card_for_user(user=self.customer_a, store=self.store_1)
        CardRepository.add_item_to_card(card, self.prod_eggs, Decimal('5.000'))
        self.assertEqual(card.items.count(), 1)
        self.assertEqual(card.items.first().quantity, Decimal('5.000'))

        self.client.force_authenticate(user=self.customer_a)
        res = self.client.post(
            f'/cards/templates/{template.id}/load-to-memo/',
            {"mode": "replace"},
            format='json'
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data['data']
        self.assertEqual(data['loaded_items_count'], 2)
        self.assertEqual(data['omitted_items_count'], 0)

        card.refresh_from_db()
        items = {it.product_id: it.quantity for it in card.items.all()}
        self.assertEqual(items[self.prod_milk.id], Decimal('2.000'))
        self.assertEqual(items[self.prod_eggs.id], Decimal('1.000'))

    def test_one_tap_hydration_merge_strategy(self):
        """Loading template with mode=merge stacks quantities for items already in the memo."""
        template = StoreMemoTemplate.objects.create(
            user=self.customer_a,
            store=self.store_1,
            vendor=self.vendor_1,
            name="Snack Refill",
            shopping_mode=ShoppingMode.WALK_IN
        )
        StoreMemoTemplateItem.objects.create(template=template, product=self.prod_milk, quantity=Decimal('2.000'))
        StoreMemoTemplateItem.objects.create(template=template, product=self.prod_eggs, quantity=Decimal('3.000'))

        # Customer already has 1 milk in active memo
        card = CardRepository.get_or_create_active_card_for_user(user=self.customer_a, store=self.store_1)
        CardRepository.add_item_to_card(card, self.prod_milk, Decimal('1.000'))

        self.client.force_authenticate(user=self.customer_a)
        res = self.client.post(
            f'/cards/templates/{template.id}/load-to-memo/',
            {"mode": "merge"},
            format='json'
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        card.refresh_from_db()
        items = {it.product_id: it.quantity for it in card.items.all()}
        # 1 existing + 2 from template = 3 milk
        self.assertEqual(items[self.prod_milk.id], Decimal('3.000'))
        # 3 eggs newly added
        self.assertEqual(items[self.prod_eggs.id], Decimal('3.000'))

    def test_one_tap_hydration_graceful_stock_omission(self):
        """Out of stock or unavailable products in template are gracefully omitted with reason reported."""
        template = StoreMemoTemplate.objects.create(
            user=self.customer_a,
            store=self.store_1,
            vendor=self.vendor_1,
            name="Grocery List With Out of Stock Item"
        )
        # Milk is in stock (50 on hand)
        StoreMemoTemplateItem.objects.create(template=template, product=self.prod_milk, quantity=Decimal('1.000'))
        # Bread is out of stock (0 on hand)
        StoreMemoTemplateItem.objects.create(template=template, product=self.prod_bread, quantity=Decimal('2.000'))

        self.client.force_authenticate(user=self.customer_a)
        res = self.client.post(
            f'/cards/templates/{template.id}/load-to-memo/',
            {"mode": "replace"},
            format='json'
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data['data']
        self.assertEqual(data['loaded_items_count'], 1)
        self.assertEqual(data['omitted_items_count'], 1)
        self.assertEqual(data['omitted_items'][0]['product_id'], self.prod_bread.id)
        self.assertIn("out of stock", data['omitted_items'][0]['reason'].lower())

    def test_idor_protection_customer_isolation(self):
        """Customer B cannot view, modify, or load Customer A's routine shopping template."""
        template_a = StoreMemoTemplate.objects.create(
            user=self.customer_a,
            store=self.store_1,
            vendor=self.vendor_1,
            name="Customer A Secret Grocery List"
        )

        self.client.force_authenticate(user=self.customer_b)

        # Retrieve
        get_res = self.client.get(f'/cards/templates/{template_a.id}/')
        self.assertEqual(get_res.status_code, status.HTTP_404_NOT_FOUND)

        # Load to memo
        load_res = self.client.post(
            f'/cards/templates/{template_a.id}/load-to-memo/',
            {"mode": "replace"},
            format='json'
        )
        self.assertEqual(load_res.status_code, status.HTTP_404_NOT_FOUND)

        # Modify
        patch_res = self.client.patch(
            f'/cards/templates/{template_a.id}/',
            {"name": "Hacked Name"},
            format='json'
        )
        self.assertEqual(patch_res.status_code, status.HTTP_404_NOT_FOUND)

        # Delete
        del_res = self.client.delete(f'/cards/templates/{template_a.id}/')
        self.assertEqual(del_res.status_code, status.HTTP_404_NOT_FOUND)

    def test_vendor_can_view_templates_for_their_store(self):
        """Vendor can inspect routine templates created for their store using ?as_vendor=true."""
        StoreMemoTemplate.objects.create(
            user=self.customer_a,
            store=self.store_1,
            vendor=self.vendor_1,
            name="Customer A Store 1 Routine"
        )
        StoreMemoTemplate.objects.create(
            user=self.customer_a,
            store=self.store_2,
            vendor=self.vendor_2,
            name="Customer A Store 2 Routine"
        )

        # Vendor 1 queries templates for their store
        self.client.force_authenticate(user=self.vendor_1)
        res = self.client.get('/cards/templates/?as_vendor=true')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['data']), 1)
        self.assertEqual(res.data['data'][0]['name'], "Customer A Store 1 Routine")
