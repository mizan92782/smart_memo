from decimal import Decimal
from typing import Optional
from django.db.models import QuerySet, F
from stores.models.coupon_mod import Coupon, CouponUsage


class CouponRepository:
    """Repository handling database operations for store promotional coupons and usages."""

    @staticmethod
    def create_coupon(
        store,
        code: str,
        discount_type: str,
        discount_value: Decimal,
        max_discount_amount: Optional[Decimal] = None,
        min_order_amount: Decimal = Decimal('0.00'),
        max_uses: Optional[int] = None,
        max_uses_per_customer: int = 1,
        start_date=None,
        end_date=None,
        is_active: bool = True
    ) -> Coupon:
        return Coupon.objects.create(
            store=store,
            code=code.strip().upper(),
            discount_type=discount_type,
            discount_value=discount_value,
            max_discount_amount=max_discount_amount,
            min_order_amount=min_order_amount,
            max_uses=max_uses,
            max_uses_per_customer=max_uses_per_customer,
            start_date=start_date,
            end_date=end_date,
            is_active=is_active
        )

    @staticmethod
    def get_by_id(coupon_id: int) -> Optional[Coupon]:
        try:
            return Coupon.objects.select_related('store').get(id=coupon_id)
        except Coupon.DoesNotExist:
            return None

    @staticmethod
    def get_by_store_and_code(store_id: int, code: str) -> Optional[Coupon]:
        if not code:
            return None
        return Coupon.objects.filter(
            store_id=store_id,
            code__iexact=code.strip()
        ).first()

    @staticmethod
    def get_by_store(store_id: int) -> QuerySet[Coupon]:
        return Coupon.objects.filter(store_id=store_id).order_by('-created_at')

    @staticmethod
    def update_coupon(coupon: Coupon, **fields) -> Coupon:
        update_fields = []
        for key, value in fields.items():
            if hasattr(coupon, key):
                if key == 'code' and isinstance(value, str):
                    value = value.strip().upper()
                setattr(coupon, key, value)
                update_fields.append(key)
        if update_fields:
            if 'updated_at' not in update_fields:
                update_fields.append('updated_at')
            coupon.save(update_fields=update_fields)
        return coupon

    @staticmethod
    def delete_coupon(coupon: Coupon) -> None:
        coupon.delete()

    @staticmethod
    def record_usage(coupon: Coupon, customer, order, discount_applied: Decimal) -> CouponUsage:
        usage = CouponUsage.objects.create(
            coupon=coupon,
            customer=customer,
            order=order,
            discount_applied=discount_applied
        )
        # Atomically increment coupon usage counter
        Coupon.objects.filter(id=coupon.id).update(used_count=F('used_count') + 1)
        coupon.refresh_from_db(fields=['used_count'])
        return usage

    @staticmethod
    def get_customer_usage_count(coupon_id: int, customer_id: int) -> int:
        return CouponUsage.objects.filter(coupon_id=coupon_id, customer_id=customer_id).count()

    @staticmethod
    def get_coupon_usages(coupon_id: int) -> QuerySet[CouponUsage]:
        return CouponUsage.objects.filter(coupon_id=coupon_id).select_related('customer', 'order').order_by('-created_at')
