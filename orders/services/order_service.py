from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from orders.models.order_mod import Order, OrderItem, SalesMemo, OrderStatus, PaymentStatus, PaymentMethod, FulfillmentType
from orders.repositories.order_repository import OrderRepository
from inventory.services.inventory_service import InventoryService
from cards.models.card_mod import Card


class OrderService:
    """
    Encapsulates the finite state machine and atomic inventory transitions for orders.
    """

    @staticmethod
    @transaction.atomic
    def submit_order_from_card(
        card: Card,
        customer,
        fulfillment_type: str = FulfillmentType.PICKUP,
        delivery_address: str = "",
        idempotency_key: str = None,
        notes: str = ""
    ) -> Order:
        """
        Creates an Order from a customer's draft Card and atomically reserves stock.
        Protects against network retries via idempotency key.
        """
        if idempotency_key:
            existing = OrderRepository.get_by_idempotency_key(idempotency_key)
            if existing:
                return existing

        items = list(card.items.select_related('product').all())
        if not items:
            raise ValueError("Cannot place an order with an empty shopping memo.")

        if not card.store:
            raise ValueError("Shopping memo does not belong to any store.")

        if not card.store.is_active or not getattr(card.store, 'is_verified', True):
            raise ValueError(f"Store '{card.store.name}' is inactive or pending administrative verification.")

        # Store fulfillment policy validation
        if fulfillment_type == FulfillmentType.PICKUP and not card.store.pickup_enabled:
            raise ValueError(f"Store '{card.store.name}' does not support in-store pickup.")
        if fulfillment_type == FulfillmentType.DELIVERY and not card.store.delivery_enabled:
            raise ValueError(f"Store '{card.store.name}' does not support home delivery.")

        # Authoritative catalog price and product availability revalidation
        for item in items:
            if not item.product or item.product.is_deleted or not item.product.is_active:
                prod_name = item.product.name if item.product else "Selected item"
                raise ValueError(f"Product '{prod_name}' is no longer available in catalog.")

            fresh_price = item.product.effective_price
            if item.unit_price != fresh_price:
                item.unit_price = fresh_price
                item.save(update_fields=['unit_price', 'updated_at'])

        subtotal = sum(item.subtotal for item in items)

        # Minimum order amount check
        if fulfillment_type == FulfillmentType.DELIVERY and card.store.min_order_amount > Decimal('0.00'):
            if subtotal < card.store.min_order_amount:
                raise ValueError(
                    f"Minimum order amount for delivery from '{card.store.name}' is {card.store.min_order_amount}. "
                    f"Current subtotal: {subtotal}."
                )

        delivery_fee = card.store.delivery_fee if fulfillment_type == FulfillmentType.DELIVERY else Decimal('0.00')
        total_amount = subtotal + delivery_fee

        profile = getattr(customer, 'profile', None)
        phone = profile.phone_number if profile and hasattr(profile, 'phone_number') else ""

        order = OrderRepository.create_order(
            customer=customer,
            store=card.store,
            status=OrderStatus.SUBMITTED,
            fulfillment_type=fulfillment_type,
            delivery_address=delivery_address,
            delivery_fee=delivery_fee,
            subtotal=subtotal,
            total_amount=total_amount,
            payment_method=PaymentMethod.COD,
            payment_status=PaymentStatus.PENDING,
            idempotency_key=idempotency_key,
            notes=notes,
            customer_phone_snapshot=phone
        )


        for item in items:
            OrderRepository.create_order_item(
                order=order,
                product=item.product,
                product_name_snapshot=item.product.name,
                unit_price_snapshot=item.unit_price,
                quantity=item.quantity,
                line_total=item.subtotal
            )

            # Atomically reserve inventory with row locking
            InventoryService.reserve_stock(
                store=card.store,
                product=item.product,
                quantity=item.quantity,
                reference_id=order.order_number,
                actor=customer,
                notes=f"Order reservation for {order.order_number}"
            )

        card.is_completed = True
        card.save(update_fields=['is_completed', 'updated_at'])

        # Dispatch async order and low-stock notifications
        from notifications.services.notification_service import NotificationService
        NotificationService.notify_order_submitted(order)
        for item in items:
            balance = getattr(item.product, 'stock_balance', None)
            if balance:
                balance.refresh_from_db()
                NotificationService.notify_low_stock_if_needed(card.store, item.product, balance)

        return order

    @staticmethod
    def accept_order(order: Order, actor) -> Order:
        """Vendor accepts the submitted order."""
        if order.status != OrderStatus.SUBMITTED:
            raise ValueError(f"Cannot accept order in status '{order.status}'.")

        order.status = OrderStatus.ACCEPTED
        order.accepted_at = timezone.now()
        order.save(update_fields=['status', 'accepted_at', 'updated_at'])

        from notifications.services.notification_service import NotificationService
        NotificationService.notify_order_status_change(order, OrderStatus.ACCEPTED)

        return order

    @staticmethod
    def start_preparing(order: Order, actor) -> Order:
        """Vendor moves order into preparation."""
        valid_statuses = [OrderStatus.ACCEPTED, OrderStatus.SUBMITTED]
        if order.status not in valid_statuses:
            raise ValueError(f"Cannot start preparing order from status '{order.status}'.")

        order.status = OrderStatus.PREPARING
        order.preparing_at = timezone.now()
        fields_to_update = ['status', 'preparing_at', 'updated_at']
        if not order.accepted_at:
            order.accepted_at = timezone.now()
            fields_to_update.append('accepted_at')

        order.save(update_fields=fields_to_update)

        from notifications.services.notification_service import NotificationService
        NotificationService.notify_order_status_change(order, OrderStatus.PREPARING)

        return order

    @staticmethod
    def dispatch_order(order: Order, actor) -> Order:
        """
        Vendor marks order as ready for customer pickup or dispatched for home delivery.
        """
        valid_statuses = [OrderStatus.PREPARING, OrderStatus.ACCEPTED]
        if order.status not in valid_statuses:
            raise ValueError(f"Cannot dispatch/ready order from status '{order.status}'.")

        if order.fulfillment_type == FulfillmentType.PICKUP:
            order.status = OrderStatus.READY_FOR_PICKUP
        else:
            order.status = OrderStatus.OUT_FOR_DELIVERY

        order.dispatched_at = timezone.now()
        order.save(update_fields=['status', 'dispatched_at', 'updated_at'])

        from notifications.services.notification_service import NotificationService
        NotificationService.notify_order_status_change(order, order.status)

        return order

    @staticmethod
    @transaction.atomic
    def fulfill_order(order: Order, actor, payment_collected: bool = True) -> Order:
        """
        Complete order fulfillment:
        - Deducts reserved stock from inventory.
        - Marks payment collected.
        - Generates immutable SalesMemo receipt.
        """
        valid_statuses = [
            OrderStatus.ACCEPTED,
            OrderStatus.PREPARING,
            OrderStatus.READY_FOR_PICKUP,
            OrderStatus.OUT_FOR_DELIVERY
        ]
        if order.status not in valid_statuses:
            raise ValueError(f"Cannot fulfill order from status '{order.status}'.")

        for item in order.items.select_related('product').all():
            if item.product:
                InventoryService.fulfill_stock(
                    store=order.store,
                    product=item.product,
                    quantity=item.quantity,
                    reference_id=order.order_number,
                    actor=actor,
                    notes=f"Fulfillment for {order.order_number}"
                )

        order.status = OrderStatus.COMPLETED
        order.completed_at = timezone.now()
        fields_to_update = ['status', 'completed_at', 'updated_at']
        if payment_collected:
            order.payment_status = PaymentStatus.COLLECTED
            order.paid_at = timezone.now()
            order.payment_collected_by = actor
            fields_to_update.extend(['payment_status', 'paid_at', 'payment_collected_by'])
        order.save(update_fields=fields_to_update)

        # Generate finalized sales memo
        items_snapshot = [
            {
                "product_name": item.product_name_snapshot,
                "quantity": str(item.quantity),
                "unit_price": str(item.unit_price_snapshot),
                "line_total": str(item.line_total)
            }
            for item in order.items.all()
        ]

        OrderRepository.create_sales_memo(
            order=order,
            store_name_snapshot=order.store.name,
            customer_email_snapshot=order.customer.email,
            items_snapshot=items_snapshot,
            subtotal=order.subtotal,
            delivery_fee=order.delivery_fee,
            total_amount=order.total_amount,
            amount_paid=order.total_amount if payment_collected else Decimal('0.00')
        )

        from notifications.services.notification_service import NotificationService
        NotificationService.notify_order_status_change(order, OrderStatus.COMPLETED)

        return order

    @staticmethod
    @transaction.atomic
    def cancel_order(order: Order, actor, reason: str = "") -> Order:
        """Cancel or reject order and release reserved inventory back to available stock."""
        if order.status == OrderStatus.COMPLETED:
            raise ValueError("Cannot cancel an already completed order.")
        if order.status in [OrderStatus.CANCELLED, OrderStatus.REJECTED]:
            return order

        # Customer cancellation restrictions
        if actor == order.customer and not getattr(actor, 'is_superuser', False):
            if order.status not in [OrderStatus.SUBMITTED, OrderStatus.ACCEPTED]:
                raise ValueError(
                    f"Customers cannot cancel an order once preparation or fulfillment has started "
                    f"(current status: '{order.status}'). Please contact the store."
                )

        for item in order.items.select_related('product').all():
            if item.product:
                InventoryService.release_reserved_stock(
                    store=order.store,
                    product=item.product,
                    quantity=item.quantity,
                    reference_id=order.order_number,
                    actor=actor,
                    notes=f"Released upon order cancellation: {reason}"
                )

        order.status = OrderStatus.CANCELLED if actor == order.customer else OrderStatus.REJECTED
        order.cancelled_at = timezone.now()
        order.save(update_fields=['status', 'cancelled_at', 'updated_at'])

        from notifications.services.notification_service import NotificationService
        NotificationService.notify_order_status_change(order, order.status)

        return order

    @staticmethod
    @transaction.atomic
    def collect_payment(order: Order, collector) -> Order:
        """
        Record collection of COD or in-person delivery payment.
        Decoupled from order delivery completion.
        """
        if order.payment_status == PaymentStatus.COLLECTED:
            return order

        order.payment_status = PaymentStatus.COLLECTED
        order.paid_at = timezone.now()
        order.payment_collected_by = collector
        order.save(update_fields=['payment_status', 'paid_at', 'payment_collected_by', 'updated_at'])

        if hasattr(order, 'sales_memo'):
            order.sales_memo.amount_paid = order.total_amount
            order.sales_memo.save(update_fields=['amount_paid', 'updated_at'])

        return order


