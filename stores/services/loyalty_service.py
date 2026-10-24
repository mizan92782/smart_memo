from decimal import Decimal
from typing import Optional, Dict, Any, List
from django.db import transaction
from django.core.exceptions import PermissionDenied, ValidationError
from stores.models.store_mod import Store
from stores.models.loyalty_mod import (
    StoreLoyaltyProgram,
    CustomerStoreLoyalty,
    LoyaltyTransaction,
    LoyaltyProgramType,
    LoyaltyTransactionType
)
from stores.repositories.loyalty_repository import LoyaltyRepository


class LoyaltyService:
    """Business service orchestrating Store Loyalty, Visit Punch Cards, and Memo Redemptions."""

    @staticmethod
    def get_or_create_program(store: Store, vendor=None) -> StoreLoyaltyProgram:
        return LoyaltyRepository.get_or_create_program(store=store, vendor=vendor)

    @staticmethod
    def update_program(store: Store, vendor, data: Dict[str, Any]) -> StoreLoyaltyProgram:
        if store.vendor_id != vendor.id and not getattr(vendor, 'is_staff', False):
            raise PermissionDenied("You do not have permission to configure this store's loyalty program.")

        program = LoyaltyRepository.get_or_create_program(store=store, vendor=vendor)

        is_active = data.get('is_active')
        if is_active is not None:
            program.is_active = bool(is_active)

        program_type = data.get('program_type')
        if program_type in [LoyaltyProgramType.POINTS, LoyaltyProgramType.STAMPS]:
            program.program_type = program_type

        points_per_currency_unit = data.get('points_per_currency_unit')
        if points_per_currency_unit is not None:
            program.points_per_currency_unit = Decimal(str(points_per_currency_unit))

        currency_per_point_redemption = data.get('currency_per_point_redemption')
        if currency_per_point_redemption is not None:
            program.currency_per_point_redemption = Decimal(str(currency_per_point_redemption))

        min_points_to_redeem = data.get('min_points_to_redeem')
        if min_points_to_redeem is not None:
            program.min_points_to_redeem = int(min_points_to_redeem)

        stamps_for_reward = data.get('stamps_for_reward')
        if stamps_for_reward is not None:
            program.stamps_for_reward = int(stamps_for_reward)

        stamp_reward_discount_amount = data.get('stamp_reward_discount_amount')
        if stamp_reward_discount_amount is not None:
            program.stamp_reward_discount_amount = Decimal(str(stamp_reward_discount_amount))

        min_order_for_stamp = data.get('min_order_for_stamp')
        if min_order_for_stamp is not None:
            program.min_order_for_stamp = Decimal(str(min_order_for_stamp))

        program.save()
        return program

    @staticmethod
    def get_customer_store_loyalty_summary(customer, store: Store) -> Dict[str, Any]:
        """Provides a complete view of a customer's loyalty punch card and points at a given store."""
        program = LoyaltyRepository.get_program_by_store(store.id)
        loyalty = LoyaltyRepository.get_or_create_customer_loyalty(customer=customer, store=store)

        is_program_active = bool(program and program.is_active)
        prog_type = program.program_type if program else LoyaltyProgramType.POINTS

        can_redeem = False
        potential_discount = Decimal('0.00')

        if is_program_active and program:
            if prog_type == LoyaltyProgramType.POINTS:
                if loyalty.points_balance >= program.min_points_to_redeem:
                    can_redeem = True
                    potential_discount = Decimal(str(loyalty.points_balance)) * program.currency_per_point_redemption
            elif prog_type == LoyaltyProgramType.STAMPS:
                if loyalty.stamps_balance >= program.stamps_for_reward:
                    can_redeem = True
                    potential_discount = program.stamp_reward_discount_amount

        recent_txs = LoyaltyRepository.get_transactions_for_account(loyalty.id)[:10]

        return {
            'store_id': store.id,
            'store_name': store.name,
            'is_program_active': is_program_active,
            'program_type': prog_type,
            'points_balance': loyalty.points_balance,
            'stamps_balance': loyalty.stamps_balance,
            'stamps_for_reward': program.stamps_for_reward if program else 10,
            'stamps_needed': max(0, (program.stamps_for_reward - loyalty.stamps_balance)) if program else 10,
            'can_redeem': can_redeem,
            'potential_discount': str(potential_discount),
            'min_points_to_redeem': program.min_points_to_redeem if program else 50,
            'stamp_reward_discount_amount': str(program.stamp_reward_discount_amount if program else Decimal('5.00')),
            'total_points_earned': loyalty.total_points_earned,
            'total_stamps_earned': loyalty.total_stamps_earned,
            'total_rewards_redeemed': loyalty.total_rewards_redeemed,
            'recent_transactions': [
                {
                    'id': tx.id,
                    'type': tx.transaction_type,
                    'points_change': tx.points_change,
                    'stamps_change': tx.stamps_change,
                    'discount_applied': str(tx.discount_amount_applied),
                    'notes': tx.notes,
                    'created_at': tx.created_at.isoformat() if tx.created_at else None
                }
                for tx in recent_txs
            ]
        }

    @staticmethod
    def redeem_loyalty_on_card(
        card,
        customer,
        points_to_redeem: int = 0,
        redeem_stamps: bool = False
    ) -> Dict[str, Any]:
        """Validates and applies loyalty points or stamp rewards directly to an active shopping memo."""
        if card.user_id != customer.id:
            raise PermissionDenied("You do not own this shopping memo.")

        if not card.store_id:
            raise ValidationError("Shopping memo must be bound to a store to redeem loyalty rewards.")

        program = LoyaltyRepository.get_program_by_store(card.store_id)
        if not program or not program.is_active:
            raise ValidationError(f"Store '{card.store.name}' does not have an active loyalty program.")

        loyalty = LoyaltyRepository.get_or_create_customer_loyalty(customer=customer, store=card.store)

        # Baseline memo subtotal after coupon (if any)
        current_subtotal = card.total_price
        if current_subtotal <= Decimal('0.00'):
            raise ValidationError("Cannot redeem loyalty rewards on an empty shopping memo.")

        discount_before_loyalty = card.discount_amount
        max_possible_discount = max(Decimal('0.00'), current_subtotal - discount_before_loyalty)
        if max_possible_discount <= Decimal('0.00'):
            raise ValidationError("Order total is already discounted to zero.")

        if program.program_type == LoyaltyProgramType.POINTS:
            if redeem_stamps:
                raise ValidationError("This store uses a Points-based loyalty program, not visit punch stamps.")

            pts = int(points_to_redeem)
            if pts < program.min_points_to_redeem:
                raise ValidationError(
                    f"A minimum of {program.min_points_to_redeem} points is required for redemption."
                )
            if pts > loyalty.points_balance:
                raise ValidationError(
                    f"Insufficient loyalty points. You have {loyalty.points_balance} points available."
                )

            raw_discount = Decimal(str(pts)) * program.currency_per_point_redemption
            discount = min(raw_discount, max_possible_discount)

            card.loyalty_points_redeemed = pts
            card.loyalty_stamps_redeemed = 0
            card.loyalty_discount_amount = discount
            card.save(update_fields=['loyalty_points_redeemed', 'loyalty_stamps_redeemed', 'loyalty_discount_amount', 'updated_at'])

            return {
                'points_redeemed': pts,
                'stamps_redeemed': 0,
                'loyalty_discount_amount': str(discount),
                'estimated_total': str(card.estimated_total)
            }

        elif program.program_type == LoyaltyProgramType.STAMPS:
            if not redeem_stamps:
                raise ValidationError("This store uses a Visit Stamps Punch Card program. Set 'redeem_stamps': true.")

            if loyalty.stamps_balance < program.stamps_for_reward:
                raise ValidationError(
                    f"You have {loyalty.stamps_balance}/{program.stamps_for_reward} stamps. Complete your punch card to redeem!"
                )

            discount = min(program.stamp_reward_discount_amount, max_possible_discount)
            stamps_used = program.stamps_for_reward

            card.loyalty_points_redeemed = 0
            card.loyalty_stamps_redeemed = stamps_used
            card.loyalty_discount_amount = discount
            card.save(update_fields=['loyalty_points_redeemed', 'loyalty_stamps_redeemed', 'loyalty_discount_amount', 'updated_at'])

            return {
                'points_redeemed': 0,
                'stamps_redeemed': stamps_used,
                'loyalty_discount_amount': str(discount),
                'estimated_total': str(card.estimated_total)
            }

        raise ValidationError("Unsupported loyalty program configuration.")

    @staticmethod
    def remove_loyalty_from_card(card, customer) -> None:
        """Removes applied loyalty discount from draft shopping memo."""
        if card.user_id != customer.id:
            raise PermissionDenied("You do not own this shopping memo.")

        card.loyalty_points_redeemed = 0
        card.loyalty_stamps_redeemed = 0
        card.loyalty_discount_amount = Decimal('0.00')
        card.save(update_fields=['loyalty_points_redeemed', 'loyalty_stamps_redeemed', 'loyalty_discount_amount', 'updated_at'])

    @staticmethod
    def process_order_checkout_deduction(order, customer, card) -> None:
        """
        Executes inside an atomic database transaction.
        Deducts redeemed points/stamps and records an immutable LoyaltyTransaction.
        """
        pts = card.loyalty_points_redeemed
        stamps = card.loyalty_stamps_redeemed
        discount = card.loyalty_discount_amount

        if pts <= 0 and stamps <= 0:
            return

        loyalty = LoyaltyRepository.get_or_create_customer_loyalty(
            customer=customer,
            store=order.store,
            for_update=True
        )

        if pts > 0:
            if loyalty.points_balance < pts:
                raise ValidationError(f"Loyalty points balance changed. You only have {loyalty.points_balance} points.")
            loyalty.points_balance -= pts

        if stamps > 0:
            if loyalty.stamps_balance < stamps:
                raise ValidationError(f"Loyalty stamp balance changed. You only have {loyalty.stamps_balance} stamps.")
            loyalty.stamps_balance -= stamps

        loyalty.total_rewards_redeemed += 1
        loyalty.save(update_fields=['points_balance', 'stamps_balance', 'total_rewards_redeemed', 'updated_at'])

        # Record append-only transaction
        LoyaltyRepository.create_transaction(
            loyalty_account=loyalty,
            customer=customer,
            store=order.store,
            transaction_type=LoyaltyTransactionType.REDEEMED_MEMO,
            points_change=-pts if pts > 0 else 0,
            stamps_change=-stamps if stamps > 0 else 0,
            points_balance_after=loyalty.points_balance,
            stamps_balance_after=loyalty.stamps_balance,
            discount_amount_applied=discount,
            order=order,
            notes=f"Redeemed on Order {order.order_number}"
        )

        order.loyalty_points_redeemed = pts
        order.loyalty_stamps_earned = 0  # not earned yet
        order.loyalty_discount_amount = discount
        order.save(update_fields=['loyalty_points_redeemed', 'loyalty_discount_amount'])

    @staticmethod
    def refund_order_loyalty(order) -> None:
        """
        Refunds redeemed loyalty points or stamps back to the customer upon order cancellation.
        """
        pts = getattr(order, 'loyalty_points_redeemed', 0)
        # Note: if stamps were redeemed, discount was applied
        discount = getattr(order, 'loyalty_discount_amount', Decimal('0.00'))

        if pts <= 0 and discount <= Decimal('0.00'):
            return

        program = LoyaltyRepository.get_program_by_store(order.store_id)
        stamps_to_refund = 0
        if program and program.program_type == LoyaltyProgramType.STAMPS and pts == 0 and discount > Decimal('0.00'):
            stamps_to_refund = program.stamps_for_reward

        loyalty = LoyaltyRepository.get_or_create_customer_loyalty(
            customer=order.customer,
            store=order.store,
            for_update=True
        )

        if pts > 0:
            loyalty.points_balance += pts
        if stamps_to_refund > 0:
            loyalty.stamps_balance += stamps_to_refund

        if loyalty.total_rewards_redeemed > 0:
            loyalty.total_rewards_redeemed -= 1

        loyalty.save(update_fields=['points_balance', 'stamps_balance', 'total_rewards_redeemed', 'updated_at'])

        LoyaltyRepository.create_transaction(
            loyalty_account=loyalty,
            customer=order.customer,
            store=order.store,
            transaction_type=LoyaltyTransactionType.REFUND_CANCELLED,
            points_change=pts,
            stamps_change=stamps_to_refund,
            points_balance_after=loyalty.points_balance,
            stamps_balance_after=loyalty.stamps_balance,
            discount_amount_applied=Decimal('0.00'),
            order=order,
            notes=f"Refund from cancelled Order {order.order_number}"
        )

    @staticmethod
    def award_order_loyalty(order, sales_memo) -> Dict[str, Any]:
        """
        Awards new loyalty points or visit stamps upon successful order completion or in-store handover.
        """
        program = LoyaltyRepository.get_program_by_store(order.store_id)
        if not program or not program.is_active:
            return {'awarded': False, 'points': 0, 'stamps': 0}

        loyalty = LoyaltyRepository.get_or_create_customer_loyalty(
            customer=order.customer,
            store=order.store,
            for_update=True
        )

        awarded_pts = 0
        awarded_stamps = 0

        if program.program_type == LoyaltyProgramType.POINTS:
            # Earn points based on paid product subtotal
            eligible_amount = max(Decimal('0.00'), order.subtotal - order.discount_amount - order.loyalty_discount_amount)
            awarded_pts = int(eligible_amount * program.points_per_currency_unit)
            if awarded_pts > 0:
                loyalty.points_balance += awarded_pts
                loyalty.total_points_earned += awarded_pts
                loyalty.save(update_fields=['points_balance', 'total_points_earned', 'updated_at'])

                LoyaltyRepository.create_transaction(
                    loyalty_account=loyalty,
                    customer=order.customer,
                    store=order.store,
                    transaction_type=LoyaltyTransactionType.EARNED_PURCHASE,
                    points_change=awarded_pts,
                    stamps_change=0,
                    points_balance_after=loyalty.points_balance,
                    stamps_balance_after=loyalty.stamps_balance,
                    order=order,
                    sales_memo=sales_memo,
                    notes=f"Earned from completed Order {order.order_number}"
                )

                order.loyalty_points_earned = awarded_pts
                order.save(update_fields=['loyalty_points_earned'])

                if sales_memo:
                    sales_memo.loyalty_points_earned = awarded_pts
                    sales_memo.save(update_fields=['loyalty_points_earned'])

        elif program.program_type == LoyaltyProgramType.STAMPS:
            # Earn 1 stamp if order subtotal satisfies threshold
            if order.subtotal >= program.min_order_for_stamp:
                awarded_stamps = 1
                loyalty.stamps_balance += 1
                loyalty.total_stamps_earned += 1
                loyalty.save(update_fields=['stamps_balance', 'total_stamps_earned', 'updated_at'])

                LoyaltyRepository.create_transaction(
                    loyalty_account=loyalty,
                    customer=order.customer,
                    store=order.store,
                    transaction_type=LoyaltyTransactionType.EARNED_PURCHASE,
                    points_change=0,
                    stamps_change=1,
                    points_balance_after=loyalty.points_balance,
                    stamps_balance_after=loyalty.stamps_balance,
                    order=order,
                    sales_memo=sales_memo,
                    notes=f"Earned 1 visit stamp from completed Order {order.order_number}"
                )

                order.loyalty_stamps_earned = 1
                order.save(update_fields=['loyalty_stamps_earned'])

                if sales_memo:
                    sales_memo.loyalty_stamps_earned = 1
                    sales_memo.save(update_fields=['loyalty_stamps_earned'])

        return {
            'awarded': (awarded_pts > 0 or awarded_stamps > 0),
            'points': awarded_pts,
            'stamps': awarded_stamps
        }
