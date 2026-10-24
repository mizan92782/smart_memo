from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from users.models.user_mod import User
from stores.models.store_mod import Store
from products.models.product_mod import Product
from cards.repositories.card_repository import CardRepository
from cards.services.card_service import CardService
from inventory.services.inventory_service import InventoryService
from orders.models.order_mod import Order, OrderStatus, FulfillmentType
from orders.services.order_service import OrderService
from shared.enums.enums import UserRoleEnum


class WalkInQRAndReorderTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Vendor & Store
        self.vendor = User.objects.create_user(
            email="vendor_qr@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.store = Store.objects.create(
            vendor=self.vendor,
            name="Apex Mart",
            pickup_enabled=True,
            delivery_enabled=True
        )

        # Products
        self.product_1 = Product.objects.create(store=self.store, name="Mineral Water 500ml", price=25.00, stock=0)
        InventoryService.receive_stock(self.store, self.product_1, Decimal('100.000'))

        self.product_2 = Product.objects.create(store=self.store, name="Digestive Biscuits", price=60.00, stock=0)
        InventoryService.receive_stock(self.store, self.product_2, Decimal('50.000'))

        # Customers
        self.customer = User.objects.create_user(
            email="shopper_qr@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )
        self.other_customer = User.objects.create_user(
            email="shopper_other_qr@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )

    def _create_and_fulfill_order(self):
        card = CardRepository.create_card(user=self.customer, store=self.store)
        CardService.add_product_to_card(card.id, self.product_1.id, Decimal('2.000'))
        CardService.add_product_to_card(card.id, self.product_2.id, Decimal('1.000'))
        order = OrderService.submit_order_from_card(
            card=card,
            customer=self.customer,
            fulfillment_type=FulfillmentType.WALK_IN
        )
        OrderService.handover_order(order=order, actor=self.vendor, payment_collected=True)
        order.refresh_from_db()
        return order

    def test_walk_in_order_qr_code_generation(self):
        order = self._create_and_fulfill_order()
        self.assertTrue(bool(order.walk_in_code))

        self.client.force_authenticate(user=self.customer)

        # 1. Direct SVG QR code endpoint
        res_qr = self.client.get(f'/orders/{order.id}/qr-code/')
        self.assertEqual(res_qr.status_code, status.HTTP_200_OK)
        self.assertEqual(res_qr['Content-Type'], 'image/svg+xml')
        svg_content = res_qr.content.decode('utf-8')
        self.assertIn('<svg', svg_content)
        self.assertIn('</svg>', svg_content)

        # 2. Embedded data URI in OrderSerializer
        res_order = self.client.get(f'/orders/{order.id}/')
        self.assertEqual(res_order.status_code, status.HTTP_200_OK)
        order_data = res_order.json()
        self.assertIn('qr_code_data_uri', order_data)
        self.assertTrue(order_data['qr_code_data_uri'].startswith('data:image/svg+xml;utf8,'))

    def test_quick_reorder_clones_past_order_into_active_draft_memo(self):
        order = self._create_and_fulfill_order()

        self.client.force_authenticate(user=self.customer)

        # Execute 1-tap reorder
        res_reorder = self.client.post(f'/orders/{order.id}/reorder/', format='json')
        self.assertEqual(res_reorder.status_code, status.HTTP_201_CREATED)

        memo_data = res_reorder.json()['data']
        self.assertEqual(memo_data['store'], self.store.id)
        self.assertEqual(len(memo_data['items']), 2)
        self.assertEqual(memo_data['total_price'], '110.00')  # 2 * 25.00 + 1 * 60.00 = 110.00

        # Retrieve active memo via GET /cards/active/
        res_active = self.client.get(f'/cards/active/?store_id={self.store.id}')
        self.assertEqual(res_active.status_code, status.HTTP_200_OK)
        active_data = res_active.json()['data']
        self.assertEqual(len(active_data['items']), 2)

    def test_quick_reorder_tenant_isolation(self):
        order = self._create_and_fulfill_order()

        # Other customer tries to reorder
        self.client.force_authenticate(user=self.other_customer)
        res_idor = self.client.post(f'/orders/{order.id}/reorder/', format='json')
        self.assertIn(res_idor.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])
