from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from shared.enums.enums import UserRoleEnum
from stores.models.store_mod import Store
from products.models.product_mod import Product
from cards.models.card_mod import Card
from inventory.services.inventory_service import InventoryService

User = get_user_model()


class MultipleMemosPerStoreTests(APITestCase):
    """
    A shopper can run several named memos at the same store at once and review
    the ones they already checked out. Memos never leak across stores or users.
    """

    def setUp(self):
        self.vendor = User.objects.create_user(
            email="vendor_multi@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.customer = User.objects.create_user(
            email="shopper_multi@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )
        self.store = Store.objects.create(
            name="Multi Memo Mart", vendor=self.vendor, address="Road 5",
            is_active=True, delivery_enabled=True, pickup_enabled=True
        )
        self.other_store = Store.objects.create(
            name="Other Mart", vendor=self.vendor, address="Road 6", is_active=True
        )
        self.product = Product.objects.create(
            store=self.store, name="Sugar 1kg", price=Decimal('120.00'), stock=0
        )
        InventoryService.receive_stock(self.store, self.product, Decimal('50.000'))
        self.client.force_authenticate(user=self.customer)

    def _open(self, title, force_new=False, store=None):
        store = store or self.store
        payload = {'title': title}
        if force_new:
            payload['force_new'] = True
        return self.client.post(f'/stores/{store.id}/memo/', payload, format='json')

    def test_force_new_opens_an_additional_memo(self):
        first = self._open('Weekly Grocery')
        self.assertEqual(first.status_code, status.HTTP_200_OK)

        second = self._open('Office Supplies', force_new=True)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)

        self.assertNotEqual(first.data['data']['id'], second.data['data']['id'])
        self.assertEqual(Card.objects.filter(user=self.customer, store=self.store).count(), 2)
        titles = set(
            Card.objects.filter(user=self.customer, store=self.store).values_list('title', flat=True)
        )
        self.assertEqual(titles, {'Weekly Grocery', 'Office Supplies'})

    def test_without_force_new_the_existing_memo_is_reused(self):
        first = self._open('Weekly Grocery')
        again = self._open('Weekly Grocery')
        self.assertEqual(first.data['data']['id'], again.data['data']['id'])
        self.assertEqual(Card.objects.filter(user=self.customer, store=self.store).count(), 1)

    def test_parallel_memos_hold_separate_items(self):
        a = self._open('Memo A').data['data']['id']
        b = self._open('Memo B', force_new=True).data['data']['id']

        self.client.post(
            f'/cards/{a}/add-item/', {'product_id': self.product.id, 'quantity': '2'}, format='json'
        )
        self.assertEqual(Card.objects.get(id=a).items.count(), 1)
        self.assertEqual(Card.objects.get(id=b).items.count(), 0)

    def test_for_store_lists_active_and_past_memos(self):
        self._open('Memo A')
        memo_b = self._open('Memo B', force_new=True).data['data']['id']
        self.client.post(
            f'/cards/{memo_b}/add-item/', {'product_id': self.product.id, 'quantity': '1'}, format='json'
        )
        self.client.post(
            f'/cards/{memo_b}/checkout/',
            {'fulfillment_type': 'walk_in', 'payment_method': 'cash_counter'},
            format='json'
        )

        res = self.client.get(f'/cards/for-store/?store_id={self.store.id}')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        active_titles = [c['title'] for c in res.data['data']['active']]
        past_titles = [c['title'] for c in res.data['data']['past']]
        self.assertEqual(active_titles, ['Memo A'])
        self.assertEqual(past_titles, ['Memo B'])

    def test_for_store_never_returns_another_stores_memos(self):
        self._open('Here')
        self._open('Elsewhere', store=self.other_store)

        res = self.client.get(f'/cards/for-store/?store_id={self.store.id}')
        titles = [c['title'] for c in res.data['data']['active']]
        self.assertEqual(titles, ['Here'])

    def test_for_store_never_returns_another_customers_memos(self):
        self._open('Mine')
        intruder = User.objects.create_user(
            email="intruder_multi@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )
        self.client.force_authenticate(user=intruder)
        res = self.client.get(f'/cards/for-store/?store_id={self.store.id}')
        self.assertEqual(res.data['data']['active'], [])
        self.assertEqual(res.data['data']['past'], [])

    def test_for_store_requires_store_id(self):
        res = self.client.get('/cards/for-store/')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
