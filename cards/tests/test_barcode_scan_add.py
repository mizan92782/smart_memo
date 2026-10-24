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
from shared.enums.enums import UserRoleEnum


class BarcodeShelfScanTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Vendor & Store A
        self.vendor_a = User.objects.create_user(
            email="vendor_scan@test.com", password="Password123!", role=UserRoleEnum.VENDOR
        )
        self.store_a = Store.objects.create(
            vendor=self.vendor_a,
            name="Supermarket Central",
            pickup_enabled=True,
            delivery_enabled=True
        )

        # Store B (Competing)
        self.store_b = Store.objects.create(
            vendor=self.vendor_a,
            name="Pharmacy Express",
            pickup_enabled=True
        )

        # Products in Store A
        self.product_cereal = Product.objects.create(
            store=self.store_a,
            name="Oat Krunch Cereal 500g",
            sku="SKU-OAT-500",
            barcode="8901030383719",
            price=320.00,
            stock=0
        )
        InventoryService.receive_stock(self.store_a, self.product_cereal, Decimal('20.000'))

        self.product_juice = Product.objects.create(
            store=self.store_a,
            name="Orange Juice 1L",
            sku="SKU-ORANGE-1L",
            barcode="",  # No explicit barcode, uses SKU as code
            price=150.00,
            stock=0
        )
        InventoryService.receive_stock(self.store_a, self.product_juice, Decimal('30.000'))

        # Product in Store B
        self.product_store_b = Product.objects.create(
            store=self.store_b,
            name="Bandages 20pk",
            sku="SKU-BAND-20",
            barcode="7890123456789",
            price=90.00,
            stock=0
        )
        InventoryService.receive_stock(self.store_b, self.product_store_b, Decimal('50.000'))

        # Customers
        self.customer = User.objects.create_user(
            email="shopper_scanner@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )
        self.other_customer = User.objects.create_user(
            email="shopper_other@test.com", password="Password123!", role=UserRoleEnum.CUSTOMER
        )

    def test_barcode_lookup_endpoint(self):
        self.client.force_authenticate(user=self.customer)

        # 1. Exact barcode lookup in Store A
        res_barcode = self.client.get(f'/products/api/barcode-lookup/?store_id={self.store_a.id}&code=8901030383719')
        self.assertEqual(res_barcode.status_code, status.HTTP_200_OK)
        self.assertEqual(res_barcode.json()['data']['id'], self.product_cereal.id)

        # 2. SKU fallback lookup in Store A
        res_sku = self.client.get(f'/products/api/barcode-lookup/?store_id={self.store_a.id}&code=SKU-ORANGE-1L')
        self.assertEqual(res_sku.status_code, status.HTTP_200_OK)
        self.assertEqual(res_sku.json()['data']['id'], self.product_juice.id)

        # 3. Barcode from Store B looked up in Store A returns 404 (store isolation)
        res_wrong_store = self.client.get(f'/products/api/barcode-lookup/?store_id={self.store_a.id}&code=7890123456789')
        self.assertEqual(res_wrong_store.status_code, status.HTTP_404_NOT_FOUND)

        # 4. Missing parameters
        res_missing = self.client.get('/products/api/barcode-lookup/')
        self.assertEqual(res_missing.status_code, status.HTTP_400_BAD_REQUEST)

    def test_in_store_scan_add_to_memo(self):
        self.client.force_authenticate(user=self.customer)

        # Customer enters Store A with a walk-in memo
        card = CardService.get_or_create_active_memo(
            user=self.customer,
            store=self.store_a,
            shopping_mode='walk_in'
        )

        # Customer scans cereal barcode
        res_scan1 = self.client.post(
            f'/cards/{card.id}/scan-add/',
            {'code': '8901030383719', 'quantity': '1.000'},
            format='json'
        )
        self.assertEqual(res_scan1.status_code, status.HTTP_201_CREATED)
        data1 = res_scan1.json()['data']
        self.assertEqual(data1['product_name'], self.product_cereal.name)
        self.assertEqual(data1['quantity'], '1.000')
        self.assertEqual(data1['subtotal'], '320.00')

        # Customer scans same cereal barcode again -> quantity increments to 2.000
        res_scan2 = self.client.post(
            f'/cards/{card.id}/scan-add/',
            {'code': '8901030383719', 'quantity': '1.000'},
            format='json'
        )
        self.assertEqual(res_scan2.status_code, status.HTTP_201_CREATED)
        data2 = res_scan2.json()['data']
        self.assertEqual(data2['quantity'], '2.000')
        self.assertEqual(data2['subtotal'], '640.00')

        # Customer scans juice by SKU
        res_scan3 = self.client.post(
            f'/cards/{card.id}/scan-add/',
            {'code': 'SKU-ORANGE-1L', 'quantity': '2.000'},
            format='json'
        )
        self.assertEqual(res_scan3.status_code, status.HTTP_201_CREATED)
        data3 = res_scan3.json()['data']
        self.assertEqual(data3['quantity'], '2.000')
        self.assertEqual(data3['subtotal'], '300.00')

        card.refresh_from_db()
        self.assertEqual(card.items.count(), 2)
        self.assertEqual(card.total_price, Decimal('940.00'))

    def test_scan_add_nonexistent_or_other_store_barcode_fails(self):
        self.client.force_authenticate(user=self.customer)

        card = CardService.get_or_create_active_memo(user=self.customer, store=self.store_a)

        # Nonexistent barcode
        res_invalid = self.client.post(f'/cards/{card.id}/scan-add/', {'code': '0000000000'}, format='json')
        self.assertEqual(res_invalid.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("No product with barcode or SKU", res_invalid.json()['message'])

        # Store B barcode scanned while in Store A
        res_cross_store = self.client.post(f'/cards/{card.id}/scan-add/', {'code': '7890123456789'}, format='json')
        self.assertEqual(res_cross_store.status_code, status.HTTP_400_BAD_REQUEST)

    def test_scan_add_tenant_isolation(self):
        # Customer A's card
        card_a = CardService.get_or_create_active_memo(user=self.customer, store=self.store_a)

        # Customer B tries to scan into Customer A's card
        self.client.force_authenticate(user=self.other_customer)
        res_idor = self.client.post(f'/cards/{card_a.id}/scan-add/', {'code': '8901030383719'}, format='json')
        self.assertEqual(res_idor.status_code, status.HTTP_404_NOT_FOUND)
