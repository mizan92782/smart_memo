from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from users.models.user_mod import User
from shared.enums.enums import UserRoleEnum
from stores.models.store_mod import Store
from stores.models.coupon_mod import Coupon, CouponUsage, DiscountType
from products.models.product_mod import Product
from categories.models.category_mod import Category
from cards.models.card_mod import Card, CardItem
from cards.services.card_service import CardService
from inventory.services.inventory_service import InventoryService


class CouponFeatureTests(APITestCase):
    def setUp(self):
        # Users
        self.vendor = User.objects.create_user(
            email='vendor_coupons@example.com',
            password='Password123!',
            role=UserRoleEnum.VENDOR
        )
        self.vendor_b = User.objects.create_user(
            email='vendor_b_coupons@example.com',
            password='Password123!',
            role=UserRoleEnum.VENDOR
        )
        self.customer = User.objects.create_user(
            email='customer_coupons@example.com',
            password='Password123!',
            role=UserRoleEnum.CUSTOMER
        )

        # Stores
        self.store = Store.objects.create(
            vendor=self.vendor,
            name="Coupon Store",
            address="123 Promo Street",
            is_active=True,
            is_verified=True,
            pickup_enabled=True,
            delivery_enabled=True,
            delivery_fee=Decimal('20.00'),
            min_order_amount=Decimal('0.00')
        )
        self.store_b = Store.objects.create(
            vendor=self.vendor_b,
            name="Store B",
            address="456 Other Street",
            is_active=True,
            is_verified=True,
            pickup_enabled=True,
            delivery_enabled=True,
            delivery_fee=Decimal('15.00')
        )

        # Category and Products
        self.category = Category.objects.create(store=self.store, name="Electronics")
        self.product = Product.objects.create(
            store=self.store,
            category=self.category,
            name="Wireless Headphones",
            price=Decimal('100.00'),
            sku="WH-100",
            stock=Decimal('50.000'),
            is_active=True
        )
        InventoryService.receive_stock(self.store, self.product, Decimal('50.000'))

    def test_vendor_create_percentage_coupon_with_cap(self):
        """Vendor successfully creates percentage coupon with a discount cap."""
        self.client.force_authenticate(user=self.vendor)
        payload = {
            "code": "save20",
            "discount_type": "percentage",
            "discount_value": "20.00",
            "max_discount_amount": "50.00",
            "min_order_amount": "50.00",
            "max_uses": 100,
            "max_uses_per_customer": 2
        }
        url = f"/stores/{self.store.id}/coupons/"
        resp = self.client.post(url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data['success'])
        self.assertEqual(resp.data['data']['code'], 'SAVE20')
        self.assertEqual(resp.data['data']['discount_type'], 'percentage')
        self.assertEqual(resp.data['data']['discount_value'], '20.00')
        self.assertEqual(resp.data['data']['max_discount_amount'], '50.00')

    def test_vendor_create_fixed_amount_coupon(self):
        """Vendor creates a flat fixed amount coupon."""
        self.client.force_authenticate(user=self.vendor)
        payload = {
            "code": "FLAT30",
            "discount_type": "fixed",
            "discount_value": "30.00",
            "min_order_amount": "100.00"
        }
        resp = self.client.post(f"/stores/{self.store.id}/coupons/", payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['data']['discount_value'], '30.00')

    def test_coupon_validation_errors(self):
        """Validation prevents invalid percentage, negative values, and date mismatches."""
        self.client.force_authenticate(user=self.vendor)
        url = f"/stores/{self.store.id}/coupons/"

        # Percentage > 100
        resp = self.client.post(url, {
            "code": "OVER100",
            "discount_type": "percentage",
            "discount_value": "150.00"
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

        # Start date after end date
        now = timezone.now()
        resp = self.client.post(url, {
            "code": "DATERANGE",
            "discount_type": "fixed",
            "discount_value": "10.00",
            "start_date": (now + timedelta(days=5)).isoformat(),
            "end_date": (now + timedelta(days=1)).isoformat()
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cross_tenant_coupon_management_blocked(self):
        """Vendor B cannot manage or view Vendor A's store coupons."""
        coupon = Coupon.objects.create(
            store=self.store,
            code="EXCLUSIVE",
            discount_type=DiscountType.FIXED,
            discount_value=Decimal('15.00')
        )

        self.client.force_authenticate(user=self.vendor_b)
        # Attempt to view list
        resp = self.client.get(f"/stores/{self.store.id}/coupons/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        # Attempt to update
        resp = self.client.patch(f"/stores/coupons/{coupon.id}/", {"discount_value": "99.00"}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        # Attempt to delete
        resp = self.client.delete(f"/stores/coupons/{coupon.id}/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_apply_coupon_to_card_and_calculate_discount(self):
        """Customer applies percentage coupon to draft memo; discount and total are calculated."""
        coupon = Coupon.objects.create(
            store=self.store,
            code="SAVE10",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal('10.00'),
            max_discount_amount=Decimal('50.00')
        )

        card = Card.objects.create(user=self.customer, store=self.store)
        CardItem.objects.create(
            card=card,
            product=self.product,
            quantity=Decimal('2.00'),
            unit_price=Decimal('100.00')
        )  # Subtotal = 200.00

        self.client.force_authenticate(user=self.customer)
        resp = self.client.post(f"/cards/{card.id}/apply-coupon/", {"code": "save10"}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['success'])
        # 10% of 200.00 = 20.00
        self.assertEqual(resp.data['data']['coupon_code'], 'SAVE10')
        self.assertEqual(resp.data['data']['discount_amount'], '20.00')
        self.assertEqual(resp.data['data']['estimated_total'], '180.00')

        # Retrieve card to verify serialization
        card_resp = self.client.get(f"/cards/{card.id}/")
        self.assertEqual(card_resp.data['data']['coupon_code'], 'SAVE10')
        self.assertEqual(card_resp.data['data']['discount_amount'], '20.00')
        self.assertEqual(card_resp.data['data']['estimated_total'], '180.00')

    def test_apply_coupon_fails_if_min_order_amount_not_met(self):
        """Coupon is rejected if card subtotal does not reach min_order_amount."""
        Coupon.objects.create(
            store=self.store,
            code="BIGSPEND",
            discount_type=DiscountType.FIXED,
            discount_value=Decimal('50.00'),
            min_order_amount=Decimal('500.00')
        )

        card = Card.objects.create(user=self.customer, store=self.store)
        CardItem.objects.create(
            card=card,
            product=self.product,
            quantity=Decimal('1.00'),
            unit_price=Decimal('100.00')
        )  # Subtotal = 100.00 < 500.00

        self.client.force_authenticate(user=self.customer)
        resp = self.client.post(f"/cards/{card.id}/apply-coupon/", {"code": "BIGSPEND"}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Minimum order amount", resp.data['message'])

    def test_apply_coupon_fails_if_expired(self):
        """Coupon is rejected if past end_date."""
        Coupon.objects.create(
            store=self.store,
            code="EXPIRED",
            discount_type=DiscountType.FIXED,
            discount_value=Decimal('10.00'),
            end_date=timezone.now() - timedelta(days=2)
        )

        card = Card.objects.create(user=self.customer, store=self.store)
        CardItem.objects.create(
            card=card,
            product=self.product,
            quantity=Decimal('1.00'),
            unit_price=Decimal('100.00')
        )

        self.client.force_authenticate(user=self.customer)
        resp = self.client.post(f"/cards/{card.id}/apply-coupon/", {"code": "EXPIRED"}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("expired", resp.data['message'])

    def test_apply_coupon_fails_for_cross_store(self):
        """Cannot apply Store B's coupon to a Store A card."""
        Coupon.objects.create(
            store=self.store_b,
            code="STOREB10",
            discount_type=DiscountType.FIXED,
            discount_value=Decimal('10.00')
        )

        card = Card.objects.create(user=self.customer, store=self.store)
        CardItem.objects.create(
            card=card,
            product=self.product,
            quantity=Decimal('1.00'),
            unit_price=Decimal('100.00')
        )

        self.client.force_authenticate(user=self.customer)
        resp = self.client.post(f"/cards/{card.id}/apply-coupon/", {"code": "STOREB10"}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not valid for", resp.data['message'])

    def test_remove_coupon_resets_card_totals(self):
        """Customer removes coupon, restoring original total."""
        coupon = Coupon.objects.create(
            store=self.store,
            code="DISCOUNT",
            discount_type=DiscountType.FIXED,
            discount_value=Decimal('25.00')
        )

        card = Card.objects.create(user=self.customer, store=self.store, coupon=coupon)
        CardItem.objects.create(
            card=card,
            product=self.product,
            quantity=Decimal('1.00'),
            unit_price=Decimal('100.00')
        )

        self.client.force_authenticate(user=self.customer)
        resp = self.client.post(f"/cards/{card.id}/remove-coupon/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['data']['discount_amount'], '0.00')
        self.assertEqual(resp.data['data']['estimated_total'], '100.00')

        card.refresh_from_db()
        self.assertIsNone(card.coupon)

    def test_checkout_with_coupon_snapshots_discount_and_records_usage(self):
        """Order checkout authoritatively applies discount, creates Order & CouponUsage, and increments usage count."""
        coupon = Coupon.objects.create(
            store=self.store,
            code="SUPER20",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal('20.00'),
            max_uses=10,
            max_uses_per_customer=1
        )

        card = Card.objects.create(user=self.customer, store=self.store, coupon=coupon)
        CardItem.objects.create(
            card=card,
            product=self.product,
            quantity=Decimal('2.00'),
            unit_price=Decimal('100.00')
        )  # Subtotal = 200.00, 20% discount = 40.00. Pickup delivery_fee = 0.00. Total = 160.00.

        self.client.force_authenticate(user=self.customer)
        resp = self.client.post(f"/cards/{card.id}/checkout/", {
            "fulfillment_type": "pickup"
        }, format='json')

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        order_data = resp.data['data']
        self.assertEqual(order_data['coupon_code'], 'SUPER20')
        self.assertEqual(Decimal(str(order_data['discount_amount'])), Decimal('40.00'))
        self.assertEqual(Decimal(str(order_data['subtotal'])), Decimal('200.00'))
        self.assertEqual(Decimal(str(order_data['total_amount'])), Decimal('160.00'))

        # Verify coupon usage was recorded
        coupon.refresh_from_db()
        self.assertEqual(coupon.used_count, 1)
        self.assertTrue(CouponUsage.objects.filter(coupon=coupon, customer=self.customer).exists())

        # Verify second checkout attempt with same 1-use-per-customer coupon is rejected
        card2 = Card.objects.create(user=self.customer, store=self.store)
        CardItem.objects.create(
            card=card2,
            product=self.product,
            quantity=Decimal('1.00'),
            unit_price=Decimal('100.00')
        )
        resp2 = self.client.post(f"/cards/{card2.id}/apply-coupon/", {"code": "SUPER20"}, format='json')
        self.assertEqual(resp2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("maximum allowed times", resp2.data['message'])
