from decimal import Decimal
from typing import Optional
from django.db.models import QuerySet, Avg, Count
from stores.models.review_mod import StoreReview
from stores.models.store_mod import Store


class ReviewRepository:
    """Handles database queries and updates for Store Reviews."""

    @staticmethod
    def create_review(
        store: Store,
        customer,
        order,
        rating: int,
        comment: str = "",
        is_verified_purchase: bool = True
    ) -> StoreReview:
        return StoreReview.objects.create(
            store=store,
            customer=customer,
            order=order,
            rating=rating,
            comment=comment,
            is_verified_purchase=is_verified_purchase
        )

    @staticmethod
    def get_by_id(review_id: int) -> Optional[StoreReview]:
        return StoreReview.objects.filter(
            id=review_id
        ).select_related('store', 'customer', 'order').first()

    @staticmethod
    def get_by_order(order_id: int) -> Optional[StoreReview]:
        return StoreReview.objects.filter(order_id=order_id).first()

    @staticmethod
    def get_by_store(store_id: int, only_visible: bool = True) -> QuerySet[StoreReview]:
        qs = StoreReview.objects.filter(store_id=store_id)
        if only_visible:
            qs = qs.filter(is_visible=True)
        return qs.select_related('customer', 'order').order_by('-created_at')

    @staticmethod
    def recalculate_store_rating(store: Store) -> tuple[Decimal, int]:
        """Calculates average rating and review count from visible reviews and updates Store."""
        stats = StoreReview.objects.filter(store=store, is_visible=True).aggregate(
            avg_rating=Avg('rating'),
            review_count=Count('id')
        )
        avg = stats['avg_rating']
        count = stats['review_count'] or 0

        avg_decimal = Decimal(str(round(avg, 2))) if avg is not None else Decimal('0.00')
        store.average_rating = avg_decimal
        store.total_reviews = count
        store.save(update_fields=['average_rating', 'total_reviews', 'updated_at'])
        return avg_decimal, count
