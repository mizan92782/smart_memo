from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from users.models.user_mod import User
from stores.models.store_mod import Store
from stores.models.loyalty_mod import (
    StoreLoyaltyProgram,
    CustomerStoreLoyalty,
    LoyaltyTransaction,
    LoyaltyProgramType,
    LoyaltyTransactionType
)
from categories.models.category_mod import Category
from products.models.product_mod import Product
from cards.models.card_mod import Card, CardItem, ShoppingMode
from orders.models.order_mod import Order, OrderStatus, FulfillmentType, SalesMemo
from shared.enums.enums import UserRoleEnum


class StoreLoyaltyTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Users
        self.vendor = User.objects.create_user(
            email='vendor@market.com',
            password='password123',
            role=UserRoleEnum.VENDOR
        )
        self.other_vendor = User.objects.create_user(
            email='other_vendor@market.com',
            password='password123',
            role=UserRoleEnum.VENDOR
        )
        self.customer = User.objects.create_user(
            email='customer@gmail.com',
            password='password123',
            role=UserRoleEnum.CUSTOMER
        )
        self.other_customer = User.objects.create_user(
            email='other_customer@gmail.com',
            password='password123',
            role=UserRoleEnum.CUSTOMER
        )

        # Stores
        self.store_a = Store.objects.create(
            name='Daily Fresh Supermarket',
            slug='daily-fresh-supermarket',
            vendor=self.vendor,
            is_active=True,
            is_verified=True,
            pickup_enabled=True,
            delivery_enabled=True,
            delivery_fee=Decimal('10.00'),
            latitude=Decimal('23.8103'),
            longitude=Decimal('90.4125')
        )
        self.store_b = Store.objects.create(
            name='Corner Bakery',
            slug='corner-bakery',
            vendor=self.other_vendor,
            is_active=True,
            is_verified=True,
            pickup_enabled=True,
            delivery_enabled=True,
            latitude=Decimal('23.8150'),
            longitude=Decimal('90.4150')
        )

        # Category and Products for Store A
        self.cat_a = Category.objects.create(name='Groceries', store=self.store_a)
        self.product_a1 = Product.objects.create(
            store=self.store_a,
            category=self.cat_a,
            name='Organic Milk 1L',
            sku='MILK-001',
            price=Decimal('25.00')
        )
        self.product_a2 = Product.objects.create(
            store=self.store_a,
            category=self.cat_a,
            name='Brown Bread 400g',
            sku='BREAD-001',
            price=Decimal('15.00')
        )

        # Inventory setup for Store A products
        from inventory.models.inventory_mod import StockBalance
        StockBalance.objects.create(store=self.store_a, product=self.product_a1, on_hand=Decimal('100.000'))
        StockBalance.objects.create(store=self.store_a, product=self.product_a2, on_hand=Decimal('100.000'))

    def test_vendor_can_configure_store_loyalty_program_and_rules(self):
        """Vendor can configure their store's loyalty program parameters."""
        self.client.force_authenticate(user=self.vendor)
        url = f"/stores/{self.store_a.id}/loyalty-program/"

        # Update program to POINTS with custom exchange rate
        payload = {
            'is_active': True,
            'program_type': 'points',
            'points_per_currency_unit': '2.00',
            'currency_per_point_redemption': '0.0500',
            'min_points_to_redeem': 100
        }
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data['data']['is_active'])
        self.assertEqual(res.data['data']['program_type'], 'points')
        self.assertEqual(res.data['data']['min_points_to_redeem'], 100)

        # Unauthorized vendor cannot update Store A's loyalty program
        self.client.force_authenticate(user=self.other_vendor)
        res_other = self.client.patch(url, payload, format='json')
        self.assertEqual(res_other.status_code, status.HTTP_403_FORBIDDEN)

        # Customer or public can view store loyalty program rules
        self.client.force_authenticate(user=self.customer)
        res_get = self.client.get(url)
        self.assertEqual(res_get.status_code, status.HTTP_200_OK)
        self.assertEqual(res_get.data['data']['store_name'], 'Daily Fresh Supermarket')

    def test_customer_view_store_loyalty_card_and_all_punch_cards(self):
        """Customer can check their store loyalty card and view all store cards they hold."""
        # Setup program on Store A
        program = StoreLoyaltyProgram.objects.create(
            store=self.store_a,
            vendor=self.vendor,
            is_active=True,
            program_type=LoyaltyProgramType.STAMPS,
            stamps_for_reward=8,
            stamp_reward_discount_amount=Decimal('8.00'),
            min_order_for_stamp=Decimal('15.00')
        )
        # Give customer 5 stamps
        CustomerStoreLoyalty.objects.create(
            customer=self.customer,
            store=self.store_a,
            vendor=self.vendor,
            stamps_balance=5,
            total_stamps_earned=5
        )

        self.client.force_authenticate(user=self.customer)
        # View specific store card
        res = self.client.get(f"/stores/{self.store_a.id}/loyalty/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data['data']
        self.assertEqual(data['stamps_balance'], 5)
        self.assertEqual(data['stamps_for_reward'], 8)
        self.assertEqual(data['stamps_needed'], 3)
        self.assertFalse(data['can_redeem'])

        # View all loyalty punch cards
        all_cards_res = self.client.get("/users/loyalty-cards/")
        self.assertEqual(all_cards_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(all_cards_res.data['data']), 1)
        self.assertEqual(all_cards_res.data['data'][0]['store_name'], 'Daily Fresh Supermarket')

    def test_customer_redeem_loyalty_points_on_draft_shopping_memo(self):
        """Customer can apply and remove loyalty points discount on an active draft shopping memo."""
        # Configure Points program
        StoreLoyaltyProgram.objects.create(
            store=self.store_a,
            vendor=self.vendor,
            is_active=True,
            program_type=LoyaltyProgramType.POINTS,
            points_per_currency_unit=Decimal('1.00'),
            currency_per_point_redemption=Decimal('0.0500'),  # 100 pts = $5.00
            min_points_to_redeem=50
        )
        # Customer has 200 points
        CustomerStoreLoyalty.objects.create(
            customer=self.customer,
            store=self.store_a,
            vendor=self.vendor,
            points_balance=200,
            total_points_earned=200
        )

        # Customer creates a shopping memo at Store A
        card = Card.objects.create(
            user=self.customer,
            store=self.store_a,
            vendor=self.vendor,
            shopping_mode=ShoppingMode.WALK_IN
        )
        # Add 2 Organic Milk ($50.00 total)
        CardItem.objects.create(
            card=card,
            product=self.product_a1,
            quantity=Decimal('2.000'),
            unit_price=Decimal('25.00')
        )
        self.assertEqual(card.total_price, Decimal('50.00'))

        self.client.force_authenticate(user=self.customer)

        # Redeem 100 points -> $5.00 discount
        res = self.client.post(
            f"/cards/{card.id}/redeem-loyalty/",
            {'points_to_redeem': 100},
            format='json'
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['data']['points_redeemed'], 100)
        self.assertEqual(Decimal(res.data['data']['loyalty_discount_amount']), Decimal('5.00'))
        self.assertEqual(Decimal(res.data['data']['estimated_total']), Decimal('45.00'))

        card.refresh_from_db()
        self.assertEqual(card.loyalty_points_redeemed, 100)
        self.assertEqual(card.loyalty_discount_amount, Decimal('5.00'))
        self.assertEqual(card.estimated_total, Decimal('45.00'))

        # Remove loyalty discount
        res_remove = self.client.post(f"/cards/{card.id}/remove-loyalty/")
        self.assertEqual(res_remove.status_code, status.HTTP_200_OK)
        card.refresh_from_db()
        self.assertEqual(card.loyalty_points_redeemed, 0)
        self.assertEqual(card.loyalty_discount_amount, Decimal('0.00'))
        self.assertEqual(card.estimated_total, Decimal('50.00'))

    def test_customer_checkout_deducts_points_and_cancellation_refunds(self):
        """Checkout atomically deducts loyalty points and order cancellation refunds them."""
        StoreLoyaltyProgram.objects.create(
            store=self.store_a,
            vendor=self.vendor,
            is_active=True,
            program_type=LoyaltyProgramType.POINTS,
            currency_per_point_redemption=Decimal('0.0500'),
            min_points_to_redeem=50
        )
        cust_loyalty = CustomerStoreLoyalty.objects.create(
            customer=self.customer,
            store=self.store_a,
            vendor=self.vendor,
            points_balance=150,
            total_points_earned=150
        )

        card = Card.objects.create(
            user=self.customer,
            store=self.store_a,
            vendor=self.vendor,
            shopping_mode=ShoppingMode.WALK_IN
        )
        CardItem.objects.create(
            card=card,
            product=self.product_a1,
            quantity=Decimal('2.000'),
            unit_price=Decimal('25.00')
        )

        self.client.force_authenticate(user=self.customer)
        # Apply 100 points ($5.00 discount)
        self.client.post(f"/cards/{card.id}/redeem-loyalty/", {'points_to_redeem': 100}, format='json')

        # Checkout
        res_checkout = self.client.post(
            f"/cards/{card.id}/checkout/",
            {'fulfillment_type': 'pickup'},
            format='json'
        )
        self.assertEqual(res_checkout.status_code, status.HTTP_201_CREATED)
        order_id = res_checkout.data['data']['id']
        order = Order.objects.get(id=order_id)

        # Invariant checks on Order
        self.assertEqual(order.loyalty_points_redeemed, 100)
        self.assertEqual(order.loyalty_discount_amount, Decimal('5.00'))
        self.assertEqual(order.total_amount, Decimal('45.00'))  # $50 - $5

        # Check that loyalty balance was deducted
        cust_loyalty.refresh_from_db()
        self.assertEqual(cust_loyalty.points_balance, 50)  # 150 - 100 = 50

        # Check LoyaltyTransaction ledger entry
        tx = LoyaltyTransaction.objects.filter(order=order, transaction_type=LoyaltyTransactionType.REDEEMED_MEMO).first()
        self.assertIsNotNone(tx)
        self.assertEqual(tx.points_change, -100)
        self.assertEqual(tx.points_balance_after, 50)

        # Cancel the order -> should refund the 100 points
        res_cancel = self.client.post(f"/orders/{order.id}/cancel/", {'reason': 'Customer changed mind'})
        self.assertEqual(res_cancel.status_code, status.HTTP_200_OK)

        cust_loyalty.refresh_from_db()
        self.assertEqual(cust_loyalty.points_balance, 150)  # 50 + 100 = 150

        # Check refund ledger transaction
        refund_tx = LoyaltyTransaction.objects.filter(order=order, transaction_type=LoyaltyTransactionType.REFUND_CANCELLED).first()
        self.assertIsNotNone(refund_tx)
        self.assertEqual(refund_tx.points_change, 100)
        self.assertEqual(refund_tx.points_balance_after, 150)

    def test_order_completion_automatically_awards_loyalty_points_and_stamps(self):
        """Completing an order (in-store handover or fulfillment) awards points or visit stamps to customer."""
        StoreLoyaltyProgram.objects.create(
            store=self.store_a,
            vendor=self.vendor,
            is_active=True,
            program_type=LoyaltyProgramType.POINTS,
            points_per_currency_unit=Decimal('2.00')  # 2 points per $1 spent
        )
        cust_loyalty = CustomerStoreLoyalty.objects.create(
            customer=self.customer,
            store=self.store_a,
            vendor=self.vendor,
            points_balance=0,
            total_points_earned=0
        )

        card = Card.objects.create(
            user=self.customer,
            store=self.store_a,
            vendor=self.vendor,
            shopping_mode=ShoppingMode.WALK_IN
        )
        CardItem.objects.create(
            card=card,
            product=self.product_a1,
            quantity=Decimal('2.000'),
            unit_price=Decimal('25.00')
        )
        self.client.force_authenticate(user=self.customer)
        res_checkout = self.client.post(
            f"/cards/{card.id}/checkout/",
            {'fulfillment_type': 'walk_in'},
            format='json'
        )
        order_id = res_checkout.data['data']['id']
        order = Order.objects.get(id=order_id)

        # Vendor hands over the order at the counter
        self.client.force_authenticate(user=self.vendor)
        res_handover = self.client.post(f"/orders/{order.id}/handover/", format='json')
        self.assertEqual(res_handover.status_code, status.HTTP_200_OK)

        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.COMPLETED)
        # Subtotal is $50.00 -> 2 pts per $1 = 100 points
        self.assertEqual(order.loyalty_points_earned, 100)

        # Check customer loyalty account updated
        cust_loyalty.refresh_from_db()
        self.assertEqual(cust_loyalty.points_balance, 100)
        self.assertEqual(cust_loyalty.total_points_earned, 100)

        # Check SalesMemo snapshots earned points
        memo = SalesMemo.objects.get(order=order)
        self.assertEqual(memo.loyalty_points_earned, 100)

        # Check thermal receipt contains earned points
        receipt_text = memo.format_thermal_receipt()
        self.assertIn("Points Earned:", receipt_text)
        self.assertIn("+100 pts", receipt_text)

    def test_store_loyalty_cross_store_isolation_and_idor_protection(self):
        """Loyalty points from Store A cannot be applied to Store B; other customers cannot tamper with memos."""
        # Store A program
        StoreLoyaltyProgram.objects.create(
            store=self.store_a,
            vendor=self.vendor,
            is_active=True,
            program_type=LoyaltyProgramType.POINTS,
            currency_per_point_redemption=Decimal('0.05')
        )
        # Customer has points in Store A
        CustomerStoreLoyalty.objects.create(
            customer=self.customer,
            store=self.store_a,
            vendor=self.vendor,
            points_balance=200
        )

        # Customer creates a card in Store B (which has NO loyalty program or different store)
        card_b = Card.objects.create(
            user=self.customer,
            store=self.store_b,
            vendor=self.other_vendor,
            shopping_mode=ShoppingMode.WALK_IN
        )
        # Create product in Store B
        cat_b = Category.objects.create(name='Bakery', store=self.store_b)
        prod_b = Product.objects.create(store=self.store_b, category=cat_b, name='Croissant', price=Decimal('10.00'))
        CardItem.objects.create(card=card_b, product=prod_b, quantity=Decimal('1.000'), unit_price=Decimal('10.00'))

        self.client.force_authenticate(user=self.customer)
        # Attempt to redeem loyalty on Store B's memo -> should be rejected because Store B has no active loyalty program
        res = self.client.post(f"/cards/{card_b.id}/redeem-loyalty/", {'points_to_redeem': 100}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("does not have an active loyalty program", res.data['message'])

        # Another customer cannot tamper with Customer A's card
        self.client.force_authenticate(user=self.other_customer)
        res_tamper = self.client.post(f"/cards/{card_b.id}/redeem-loyalty/", {'points_to_redeem': 100}, format='json')
        self.assertIn(res_tamper.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])
