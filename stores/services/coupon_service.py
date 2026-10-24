from decimal import Decimal
from typing import Optional, Tuple
from django.db.models import QuerySet
from stores.models.store_mod import Store
from stores.models.coupon_mod import Coupon, CouponUsage, DiscountType
from stores.repositories.coupon_repository import CouponRepository
from shared.enums.enums import UserRoleEnum


class CouponService:
    """Domain service managing coupon creation, validation, card application, and usage recording."""

    @staticmethod
    def create_coupon(store_id: int, actor, data: dict) -> Coupon:
        try:
            store = Store.objects.get(id=store_id)
        except Store.DoesNotExist:
            raise ValueError("Store not found.")

        # Strict tenant isolation
        is_staff = getattr(actor, 'role', '') in [UserRoleEnum.STAFF, UserRoleEnum.SUPERUSER] or actor.is_staff or actor.is_superuser
        if store.vendor != actor and not is_staff:
            raise PermissionError("You do not have permission to create coupons for this store.")

        code = str(data.get('code', '')).strip().upper()
        if not code:
            raise ValueError("Coupon code is required.")

        existing = CouponRepository.get_by_store_and_code(store_id, code)
        if existing:
            raise ValueError(f"A coupon with code '{code}' already exists for this store.")

        discount_type = data.get('discount_type', DiscountType.PERCENTAGE)
        if discount_type not in [DiscountType.PERCENTAGE, DiscountType.FIXED]:
            raise ValueError(f"Invalid discount_type: {discount_type}.")

        discount_value = Decimal(str(data.get('discount_value', '0.00')))
        if discount_value <= Decimal('0.00'):
            raise ValueError("Discount value must be greater than zero.")

        if discount_type == DiscountType.PERCENTAGE and discount_value > Decimal('100.00'):
            raise ValueError("Percentage discount cannot exceed 100%.")

        max_discount_amount = None
        if data.get('max_discount_amount'):
            max_discount_amount = Decimal(str(data.get('max_discount_amount')))
            if max_discount_amount <= Decimal('0.00'):
                raise ValueError("Maximum discount amount must be greater than zero.")

        min_order_amount = Decimal('0.00')
        if data.get('min_order_amount'):
            min_order_amount = Decimal(str(data.get('min_order_amount')))
            if min_order_amount < Decimal('0.00'):
                raise ValueError("Minimum order amount cannot be negative.")

        start_date = data.get('start_date')
        end_date = data.get('end_date')
        if start_date and end_date and start_date > end_date:
            raise ValueError("Coupon start date cannot be after end date.")

        max_uses = data.get('max_uses')
        if max_uses is not None and int(max_uses) <= 0:
            raise ValueError("Max uses must be greater than zero if specified.")

        max_uses_per_customer = int(data.get('max_uses_per_customer', 1))
        if max_uses_per_customer <= 0:
            raise ValueError("Max uses per customer must be at least 1.")

        is_active = bool(data.get('is_active', True))

        return CouponRepository.create_coupon(
            store=store,
            code=code,
            discount_type=discount_type,
            discount_value=discount_value,
            max_discount_amount=max_discount_amount,
            min_order_amount=min_order_amount,
            max_uses=int(max_uses) if max_uses else None,
            max_uses_per_customer=max_uses_per_customer,
            start_date=start_date,
            end_date=end_date,
            is_active=is_active
        )

    @staticmethod
    def update_coupon(coupon_id: int, actor, data: dict) -> Coupon:
        coupon = CouponRepository.get_by_id(coupon_id)
        if not coupon:
            raise ValueError("Coupon not found.")

        is_staff = getattr(actor, 'role', '') in [UserRoleEnum.STAFF, UserRoleEnum.SUPERUSER] or actor.is_staff or actor.is_superuser
        if coupon.store.vendor != actor and not is_staff:
            raise PermissionError("You do not have permission to modify this coupon.")

        fields_to_update = {}

        if 'code' in data:
            new_code = str(data['code']).strip().upper()
            if not new_code:
                raise ValueError("Coupon code cannot be blank.")
            existing = CouponRepository.get_by_store_and_code(coupon.store_id, new_code)
            if existing and existing.id != coupon.id:
                raise ValueError(f"A coupon with code '{new_code}' already exists for this store.")
            fields_to_update['code'] = new_code

        if 'discount_type' in data:
            dtype = data['discount_type']
            if dtype not in [DiscountType.PERCENTAGE, DiscountType.FIXED]:
                raise ValueError(f"Invalid discount_type: {dtype}.")
            fields_to_update['discount_type'] = dtype

        if 'discount_value' in data:
            dval = Decimal(str(data['discount_value']))
            if dval <= Decimal('0.00'):
                raise ValueError("Discount value must be greater than zero.")
            fields_to_update['discount_value'] = dval

        if 'max_discount_amount' in data:
            mval = data['max_discount_amount']
            fields_to_update['max_discount_amount'] = Decimal(str(mval)) if mval else None

        if 'min_order_amount' in data:
            min_val = Decimal(str(data['min_order_amount']))
            if min_val < Decimal('0.00'):
                raise ValueError("Minimum order amount cannot be negative.")
            fields_to_update['min_order_amount'] = min_val

        if 'max_uses' in data:
            mu = data['max_uses']
            fields_to_update['max_uses'] = int(mu) if mu else None

        if 'max_uses_per_customer' in data:
            fields_to_update['max_uses_per_customer'] = int(data['max_uses_per_customer'])

        if 'start_date' in data:
            fields_to_update['start_date'] = data['start_date']

        if 'end_date' in data:
            fields_to_update['end_date'] = data['end_date']

        if 'is_active' in data:
            fields_to_update['is_active'] = bool(data['is_active'])

        # Validate start/end dates
        start = fields_to_update.get('start_date', coupon.start_date)
        end = fields_to_update.get('end_date', coupon.end_date)
        if start and end and start > end:
            raise ValueError("Coupon start date cannot be after end date.")

        return CouponRepository.update_coupon(coupon, **fields_to_update)

    @staticmethod
    def delete_coupon(coupon_id: int, actor) -> None:
        coupon = CouponRepository.get_by_id(coupon_id)
        if not coupon:
            raise ValueError("Coupon not found.")

        is_staff = getattr(actor, 'role', '') in [UserRoleEnum.STAFF, UserRoleEnum.SUPERUSER] or actor.is_staff or actor.is_superuser
        if coupon.store.vendor != actor and not is_staff:
            raise PermissionError("You do not have permission to delete this coupon.")

        CouponRepository.delete_coupon(coupon)

    @staticmethod
    def get_store_coupons(store_id: int, actor) -> QuerySet[Coupon]:
        try:
            store = Store.objects.get(id=store_id)
        except Store.DoesNotExist:
            raise ValueError("Store not found.")

        is_staff = getattr(actor, 'role', '') in [UserRoleEnum.STAFF, UserRoleEnum.SUPERUSER] or actor.is_staff or actor.is_superuser
        if store.vendor != actor and not is_staff:
            raise PermissionError("You do not have permission to view coupons for this store.")

        return CouponRepository.get_by_store(store_id)

    @staticmethod
    def validate_and_apply_to_card(card, code: str, user) -> Tuple[Coupon, Decimal, Decimal]:
        """Validate coupon applicability and attach to draft memo card."""
        if not card.store:
            raise ValueError("Cannot apply a coupon to a memo card without items or a store.")

        coupon = CouponRepository.get_by_store_and_code(card.store_id, code)
        if not coupon:
            raise ValueError(f"Coupon '{code}' is not valid for {card.store.name}.")

        is_valid, reason = coupon.is_valid_for(user, card.total_price)
        if not is_valid:
            raise ValueError(reason)

        card.coupon = coupon
        card.save(update_fields=['coupon', 'updated_at'])

        discount = coupon.calculate_discount(card.total_price)
        estimated_total = max(Decimal('0.00'), card.total_price - discount)
        return coupon, discount, estimated_total

    @staticmethod
    def remove_from_card(card, user) -> None:
        """Remove currently attached coupon from draft memo card."""
        card.coupon = None
        card.save(update_fields=['coupon', 'updated_at'])

    @staticmethod
    def record_coupon_usage(coupon: Coupon, customer, order, discount_applied: Decimal) -> CouponUsage:
        """Record usage of a coupon upon order creation and increment usage counter."""
        return CouponRepository.record_usage(
            coupon=coupon,
            customer=customer,
            order=order,
            discount_applied=discount_applied
        )
