from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from stores.models.store_mod import Store
from stores.models.review_mod import StoreReview
from stores.repositories.review_repository import ReviewRepository
from stores.repositories.store_repository import StoreRepository
from orders.models.order_mod import Order, OrderStatus
from shared.caching.cache_service import CacheService


class ReviewService:
    """
    Business service enforcing verified customer reviews, rating calculations,
    and vendor responses.
    """

    @staticmethod
    @transaction.atomic
    def create_review(
        customer,
        store_id: int,
        order_id: int,
        rating: int,
        comment: str = ""
    ) -> StoreReview:
        """
        Creates a verified customer review for a completed order.
        Strictly enforces that the customer placed and completed an order at the store.
        """
        store = StoreRepository.get_by_id(store_id)
        if not store:
            raise ValueError("Store not found.")

        try:
            rating_val = int(rating)
        except (ValueError, TypeError):
            raise ValueError("Rating must be an integer between 1 and 5.")

        if rating_val < 1 or rating_val > 5:
            raise ValueError("Rating must be between 1 and 5.")

        order = Order.objects.filter(id=order_id).select_related('customer', 'store').first()
        if not order:
            raise ValueError("Order not found.")

        if order.customer != customer and not getattr(customer, 'is_superuser', False):
            raise PermissionError("You can only review stores where you have placed an order.")

        if order.store_id != store.id:
            raise ValueError("Specified order was placed at a different store.")

        if order.status != OrderStatus.COMPLETED:
            raise ValueError(
                f"You can only review a store after your order has been completed (Current status: '{order.status}')."
            )

        existing_review = ReviewRepository.get_by_order(order.id)
        if existing_review:
            raise ValueError("You have already reviewed this completed order.")

        review = ReviewRepository.create_review(
            store=store,
            customer=customer,
            order=order,
            rating=rating_val,
            comment=comment.strip(),
            is_verified_purchase=True
        )

        # Recalculate average rating and review count
        ReviewRepository.recalculate_store_rating(store)

        # Invalidate store profile cache
        CacheService.invalidate_store_profile(store.id)

        return review

    @staticmethod
    def reply_to_review(
        actor,
        review_id: int,
        reply_text: str
    ) -> StoreReview:
        """Store vendor replies to customer review."""
        review = ReviewRepository.get_by_id(review_id)
        if not review:
            raise ValueError("Review not found.")

        if review.store.vendor != actor and not getattr(actor, 'is_superuser', False):
            raise PermissionError("Only the store vendor can reply to this review.")

        if not reply_text or not reply_text.strip():
            raise ValueError("Reply text cannot be empty.")

        review.vendor_reply = reply_text.strip()
        review.vendor_replied_at = timezone.now()
        review.save(update_fields=['vendor_reply', 'vendor_replied_at', 'updated_at'])
        return review

    @staticmethod
    @transaction.atomic
    def delete_review(actor, review_id: int) -> None:
        """Customer deletes their own review, or admin removes it."""
        review = ReviewRepository.get_by_id(review_id)
        if not review:
            raise ValueError("Review not found.")

        is_author = (review.customer == actor)
        is_staff_or_admin = (getattr(actor, 'is_staff', False) or getattr(actor, 'is_superuser', False))

        if not is_author and not is_staff_or_admin:
            raise PermissionError("You can only delete your own review.")

        store = review.store
        review.delete()

        # Recalculate store ratings
        ReviewRepository.recalculate_store_rating(store)
        CacheService.invalidate_store_profile(store.id)

    @staticmethod
    def get_store_reviews(store_id: int):
        """Returns visible customer reviews for a store."""
        return ReviewRepository.get_by_store(store_id=store_id)
