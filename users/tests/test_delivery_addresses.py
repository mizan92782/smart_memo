from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework import status

from shared.enums.enums import UserRoleEnum
from stores.models.store_mod import Store
from products.models.product_mod import Product
from cards.models.card_mod import Card
from cards.services.card_service import CardService
from users.models.address_mod import CustomerAddress
from users.services.address_service import AddressService
from stores.services.store_service import StoreService
from inventory.services.inventory_service import InventoryService

User = get_user_model()


class DeliveryAddressesTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

        # Users
        self.customer_a = User.objects.create_user(
            email='customer_a_addr@example.com',
            password='Password123!',
            role=UserRoleEnum.CUSTOMER
        )
        self.customer_b = User.objects.create_user(
            email='customer_b_addr@example.com',
            password='Password123!',
            role=UserRoleEnum.CUSTOMER
        )
        self.vendor = User.objects.create_user(
            email='vendor_addr@example.com',
            password='Password123!',
            role=UserRoleEnum.VENDOR
        )

        # Store at coordinates (23.8103, 90.4125) [Gulshan, Dhaka]
        self.store = Store.objects.create(
            name="Gulshan Fresh Grocery",
            vendor=self.vendor,
            latitude=23.8103,
            longitude=90.4125,
            delivery_enabled=True,
            pickup_enabled=True,
            delivery_fee=Decimal("30.00"),
            min_order_amount=Decimal("50.00"),
            is_active=True,
            is_verified=True
        )

        self.product = Product.objects.create(
            store=self.store,
            name="Fresh Apples",
            price=Decimal("100.00"),
            stock=Decimal("50.000"),
            is_active=True
        )
        InventoryService.receive_stock(self.store, self.product, Decimal("50.000"))

    def tearDown(self):
        cache.clear()

    def test_create_customer_address(self):
        self.client.force_authenticate(user=self.customer_a)
        payload = {
            "label": "Home",
            "recipient_name": "Alice Wonderland",
            "phone_number": "+8801700000001",
            "address_line": "House 12, Road 5, Block B",
            "city": "Dhaka",
            "postal_code": "1212",
            "latitude": 23.8150,
            "longitude": 90.4150,
            "delivery_instructions": "Leave with security",
            "is_default": True
        }
        resp = self.client.post("/users/addresses/", payload)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.data["data"]
        self.assertEqual(data["label"], "Home")
        self.assertEqual(data["recipient_name"], "Alice Wonderland")
        self.assertTrue(data["is_default"])

    def test_first_address_automatically_default(self):
        self.client.force_authenticate(user=self.customer_a)
        resp = self.client.post("/users/addresses/", {
            "label": "Office",
            "phone_number": "+8801700000002",
            "address_line": "Level 4, Tech Park",
            "city": "Dhaka"
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data["data"]["is_default"])

    def test_set_default_address_unsets_previous_default(self):
        addr1 = CustomerAddress.objects.create(
            customer=self.customer_a,
            label="First",
            phone_number="+880100",
            address_line="Line 1",
            is_default=True
        )
        addr2 = CustomerAddress.objects.create(
            customer=self.customer_a,
            label="Second",
            phone_number="+880200",
            address_line="Line 2",
            is_default=False
        )

        self.client.force_authenticate(user=self.customer_a)
        resp = self.client.post(f"/users/addresses/{addr2.id}/set-default/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        addr1.refresh_from_db()
        addr2.refresh_from_db()
        self.assertFalse(addr1.is_default)
        self.assertTrue(addr2.is_default)

    def test_customer_address_isolation_idor_prevention(self):
        addr_b = CustomerAddress.objects.create(
            customer=self.customer_b,
            label="Private B Address",
            phone_number="+880999",
            address_line="Secret Location",
            is_default=True
        )

        # Customer A cannot view Customer B's address
        self.client.force_authenticate(user=self.customer_a)
        resp_get = self.client.get(f"/users/addresses/{addr_b.id}/")
        self.assertEqual(resp_get.status_code, status.HTTP_404_NOT_FOUND)

        # Customer A cannot update Customer B's address
        resp_patch = self.client.patch(f"/users/addresses/{addr_b.id}/", {"label": "Hacked Label"})
        self.assertEqual(resp_patch.status_code, status.HTTP_404_NOT_FOUND)

        # Customer A cannot delete Customer B's address
        resp_del = self.client.delete(f"/users/addresses/{addr_b.id}/")
        self.assertEqual(resp_del.status_code, status.HTTP_404_NOT_FOUND)

        addr_b.refresh_from_db()
        self.assertEqual(addr_b.label, "Private B Address")
        self.assertFalse(addr_b.is_deleted)

    def test_soft_delete_address(self):
        addr = CustomerAddress.objects.create(
            customer=self.customer_a,
            label="To Delete",
            phone_number="+880111",
            address_line="Delete Road"
        )
        self.client.force_authenticate(user=self.customer_a)
        resp = self.client.delete(f"/users/addresses/{addr.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        addr.refresh_from_db()
        self.assertTrue(addr.is_deleted)

        # List should not include deleted address
        resp_list = self.client.get("/users/addresses/")
        addresses = resp_list.data.get("data", resp_list.data.get("results", []))
        self.assertEqual(len(addresses), 0)

    def test_coordinate_validation(self):
        self.client.force_authenticate(user=self.customer_a)
        resp = self.client.post("/users/addresses/", {
            "label": "Invalid Coordinates",
            "phone_number": "+880111",
            "address_line": "Outer Space",
            "latitude": 95.0,  # Invalid: > 90
            "longitude": 90.0
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_calculate_delivery_fee_base_tier(self):
        # Coordinates very close (~0.5 km) to store (23.8103, 90.4125)
        resp = self.client.post(f"/stores/{self.store.id}/calculate-delivery-fee/", {
            "lat": 23.8120,
            "lng": 90.4140
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        quote = resp.data["data"]
        self.assertEqual(quote["delivery_fee"], "30.00")
        self.assertLess(quote["distance_km"], 2.0)
        self.assertTrue(quote["is_dynamic"])

    def test_calculate_delivery_fee_distance_tier(self):
        # Coordinates ~6.0 km away from store
        # Base fee (30.00) covers first 2.0 km
        # Remaining ~4.0 km charged at 15.00/km -> fee ~ 30 + 60 = 90.00
        resp = self.client.post(f"/stores/{self.store.id}/calculate-delivery-fee/", {
            "lat": 23.7500,
            "lng": 90.4125
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        quote = resp.data["data"]
        self.assertGreater(float(quote["delivery_fee"]), 30.00)
        self.assertGreater(quote["distance_km"], 2.0)

    def test_checkout_with_address_id_snapshots_and_charges_dynamic_fee(self):
        # Create saved address ~5 km away
        addr = CustomerAddress.objects.create(
            customer=self.customer_a,
            label="Home Sweet Home",
            recipient_name="Alice Smith",
            phone_number="+8801999999999",
            address_line="Flat 4B, Green Tower",
            city="Dhaka",
            latitude=23.7600,
            longitude=90.4125,
            delivery_instructions="Call before delivery",
            is_default=True
        )

        card = Card.objects.create(user=self.customer_a, store=self.store)
        CardService.add_product_to_card(
            card_id=card.id,
            product_id=self.product.id,
            quantity=Decimal("1.000"),
            actor=self.customer_a
        )

        self.client.force_authenticate(user=self.customer_a)
        resp = self.client.post(f"/cards/{card.id}/checkout/", {
            "fulfillment_type": "delivery",
            "address_id": addr.id
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        order_data = resp.data["data"]

        # Delivery address contains snapshot of address, recipient, phone, instructions
        self.assertIn("Alice Smith", order_data["delivery_address"])
        self.assertIn("Flat 4B, Green Tower", order_data["delivery_address"])
        self.assertIn("Call before delivery", order_data["delivery_address"])
        self.assertEqual(order_data["customer_phone_snapshot"], "+8801999999999")

        # Dynamic delivery fee applied
        self.assertGreater(Decimal(order_data["delivery_fee"]), Decimal("30.00"))
        # Total is subtotal (100) + dynamic delivery fee
        expected_total = Decimal("100.00") + Decimal(order_data["delivery_fee"])
        self.assertEqual(Decimal(order_data["total_amount"]), expected_total)

    def test_checkout_with_other_customer_address_fails(self):
        addr_b = CustomerAddress.objects.create(
            customer=self.customer_b,
            label="Bob's House",
            phone_number="+880222",
            address_line="Bob's Road"
        )
        card = Card.objects.create(user=self.customer_a, store=self.store)
        CardService.add_product_to_card(
            card_id=card.id,
            product_id=self.product.id,
            quantity=Decimal("1.000"),
            actor=self.customer_a
        )

        self.client.force_authenticate(user=self.customer_a)
        resp = self.client.post(f"/cards/{card.id}/checkout/", {
            "fulfillment_type": "delivery",
            "address_id": addr_b.id
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not found or does not belong to you", resp.data["message"])
