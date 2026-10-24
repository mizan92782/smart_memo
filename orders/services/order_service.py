from decimal import Decimal
from typing import Optional
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
        notes: str = "",
        address_id: int = None
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

        profile = getattr(customer, 'profile', None)
        phone = profile.phone_number if profile and hasattr(profile, 'phone_number') else ""

        if fulfillment_type == FulfillmentType.DELIVERY and address_id:
            from users.models.address_mod import CustomerAddress
            try:
                addr = CustomerAddress.objects.get(id=address_id, customer=customer, is_deleted=False)
                delivery_address = addr.formatted_snapshot()
                if addr.phone_number:
                    phone = addr.phone_number
                from stores.services.store_service import StoreService
                dynamic_fee, _ = StoreService.calculate_delivery_fee(
                    card.store, customer_lat=addr.latitude, customer_lng=addr.longitude
                )
                delivery_fee = dynamic_fee
            except CustomerAddress.DoesNotExist:
                raise ValueError("Saved address not found or does not belong to you.")
        elif fulfillment_type == FulfillmentType.DELIVERY:
            delivery_fee = card.store.delivery_fee if card.store.delivery_fee is not None else Decimal('0.00')
        else:
            delivery_fee = Decimal('0.00')

        # Coupon validation and authoritative discount calculation
        applied_coupon = None
        coupon_code = ""
        discount_amount = Decimal('0.00')

        if card.coupon:
            if card.coupon.store_id != card.store_id:
                raise ValueError(f"Coupon '{card.coupon.code}' is not valid for this store.")
            is_valid, reason = card.coupon.is_valid_for(customer, subtotal)
            if not is_valid:
                raise ValueError(f"Coupon '{card.coupon.code}' is no longer valid: {reason}")
            discount_amount = card.coupon.calculate_discount(subtotal)
            coupon_code = card.coupon.code
            applied_coupon = card.coupon

        # Loyalty reward discount
        loyalty_discount_amount = card.loyalty_discount_amount if card.loyalty_discount_amount else Decimal('0.00')

        total_amount = max(Decimal('0.00'), subtotal - discount_amount - loyalty_discount_amount) + delivery_fee

        order = OrderRepository.create_order(
            customer=customer,
            vendor=card.store.vendor if card.store else None,
            store=card.store,
            status=OrderStatus.SUBMITTED,
            fulfillment_type=fulfillment_type,
            delivery_address=delivery_address,
            delivery_fee=delivery_fee,
            subtotal=subtotal,
            coupon_code=coupon_code,
            discount_amount=discount_amount,
            loyalty_discount_amount=loyalty_discount_amount,
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

        if applied_coupon:
            from stores.services.coupon_service import CouponService
            CouponService.record_coupon_usage(
                coupon=applied_coupon,
                customer=customer,
                order=order,
                discount_applied=discount_amount
            )
            card.coupon = None

        if card.loyalty_points_redeemed > 0 or card.loyalty_stamps_redeemed > 0:
            from stores.services.loyalty_service import LoyaltyService
            LoyaltyService.process_order_checkout_deduction(order=order, customer=customer, card=card)
            card.loyalty_points_redeemed = 0
            card.loyalty_stamps_redeemed = 0
            card.loyalty_discount_amount = Decimal('0.00')

        card.is_completed = True
        card.save(update_fields=['is_completed', 'coupon', 'loyalty_points_redeemed', 'loyalty_stamps_redeemed', 'loyalty_discount_amount', 'updated_at'])

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
    def assign_delivery_driver(
        order: Order,
        actor,
        driver_name: str,
        driver_phone: str,
        vehicle_type: str = "",
        tracking_notes: str = "",
        estimated_delivery_time=None,
        auto_dispatch: bool = False
    ) -> Order:
        """
        Assign a designated delivery driver to a home delivery order.
        Enforces tenant isolation, delivery fulfillment type, and active status invariants.
        """
        from shared.enums.enums import UserRoleEnum
        is_staff = getattr(actor, 'role', '') in [UserRoleEnum.STAFF, UserRoleEnum.SUPERUSER] or actor.is_staff or actor.is_superuser
        if order.store.vendor != actor and not is_staff:
            raise PermissionError("You do not have permission to assign a delivery driver to this order.")

        if order.fulfillment_type != FulfillmentType.DELIVERY:
            raise ValueError("Delivery drivers can only be assigned to home delivery orders, not in-store pickup orders.")

        if order.status in [OrderStatus.COMPLETED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
            raise ValueError(f"Cannot assign delivery driver to an order with status '{order.status}'.")

        driver_name = str(driver_name).strip()
        driver_phone = str(driver_phone).strip()
        if not driver_name:
            raise ValueError("Driver name is required.")
        if not driver_phone:
            raise ValueError("Driver phone number is required.")

        order.delivery_person_name = driver_name
        order.delivery_person_phone = driver_phone
        order.delivery_vehicle_type = vehicle_type.strip() if vehicle_type else ""
        order.delivery_tracking_notes = tracking_notes.strip() if tracking_notes else ""
        order.delivery_assigned_at = timezone.now()
        if estimated_delivery_time:
            order.estimated_delivery_time = estimated_delivery_time

        fields_to_update = [
            'delivery_person_name',
            'delivery_person_phone',
            'delivery_vehicle_type',
            'delivery_tracking_notes',
            'delivery_assigned_at',
            'estimated_delivery_time',
            'updated_at'
        ]

        if auto_dispatch and order.status in [OrderStatus.ACCEPTED, OrderStatus.PREPARING, OrderStatus.SUBMITTED]:
            order.status = OrderStatus.OUT_FOR_DELIVERY
            order.dispatched_at = timezone.now()
            fields_to_update.extend(['status', 'dispatched_at'])

        order.save(update_fields=fields_to_update)

        from notifications.services.notification_service import NotificationService
        NotificationService.notify_delivery_assigned(order)

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
        if order.fulfillment_type == FulfillmentType.WALK_IN:
            valid_statuses.append(OrderStatus.SUBMITTED)

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

        memo = OrderRepository.create_sales_memo(
            order=order,
            customer=order.customer,
            vendor=order.vendor or (order.store.vendor if order.store else None),
            store_name_snapshot=order.store.name,
            customer_email_snapshot=order.customer.email,
            items_snapshot=items_snapshot,
            subtotal=order.subtotal,
            coupon_code=order.coupon_code,
            discount_amount=order.discount_amount,
            loyalty_discount_amount=order.loyalty_discount_amount,
            delivery_fee=order.delivery_fee,
            total_amount=order.total_amount,
            amount_paid=order.total_amount if payment_collected else Decimal('0.00')
        )

        # Award loyalty points or visit stamps upon order completion
        from stores.services.loyalty_service import LoyaltyService
        LoyaltyService.award_order_loyalty(order=order, sales_memo=memo)

        from notifications.services.notification_service import NotificationService
        NotificationService.notify_order_status_change(order, OrderStatus.COMPLETED)

        return order

    @staticmethod
    @transaction.atomic
    def handover_order(order: Order, actor, payment_collected: bool = True, notes: str = "") -> Order:
        """
        Store owner completes an in-store walk-in or pickup order by handing over the collected items directly to the customer.
        Atomically fulfills reserved stock, marks payment collected, issues SalesMemo, and notifies customer.
        """
        from shared.enums.enums import UserRoleEnum
        is_staff = getattr(actor, 'role', '') in [UserRoleEnum.STAFF, UserRoleEnum.SUPERUSER] or actor.is_staff or actor.is_superuser
        if order.store.vendor != actor and not is_staff:
            raise PermissionError("You do not have permission to hand over this order.")

        if order.status in [OrderStatus.COMPLETED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
            raise ValueError(f"Cannot hand over order in terminal status '{order.status}'.")

        return OrderService.fulfill_order(order=order, actor=actor, payment_collected=payment_collected)

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

        if getattr(order, 'loyalty_points_redeemed', 0) > 0 or getattr(order, 'loyalty_discount_amount', Decimal('0.00')) > Decimal('0.00'):
            from stores.services.loyalty_service import LoyaltyService
            LoyaltyService.refund_order_loyalty(order)

        from notifications.services.notification_service import NotificationService
        NotificationService.notify_order_status_change(order, order.status)

        from audit.services.audit_service import AuditService
        from audit.models.audit_mod import AuditAction
        AuditService.log(
            action=AuditAction.ORDER_CANCELLED,
            target_model="Order",
            target_id=str(order.id),
            actor=actor,
            store=order.store,
            details={
                "order_number": order.order_number,
                "reason": reason,
                "new_status": order.status
            }
        )

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

        from audit.services.audit_service import AuditService
        from audit.models.audit_mod import AuditAction
        AuditService.log(
            action=AuditAction.ORDER_PAYMENT_COLLECTED,
            target_model="Order",
            target_id=str(order.id),
            actor=collector,
            store=order.store,
            details={
                "order_number": order.order_number,
                "amount": str(order.total_amount),
            }
        )

        return order

    @staticmethod
    def counter_lookup(code: str, actor, store_id: Optional[int] = None) -> Order:
        """
        Look up a customer order at the physical store counter via 6-digit walk-in code.
        Enforces vendor tenant isolation: vendor can only access orders for their own store.
        """
        if not code or not code.strip():
            raise ValueError("Walk-in verification code is required.")

        normalized_code = code.strip()
        order = OrderRepository.get_by_walk_in_code(normalized_code)
        if not order:
            raise Order.DoesNotExist("No order found with the provided counter walk-in code.")

        from shared.enums.enums import UserRoleEnum
        is_staff = getattr(actor, 'role', '') in [UserRoleEnum.STAFF, UserRoleEnum.SUPERUSER] or actor.is_staff or actor.is_superuser
        if order.store.vendor != actor and not is_staff:
            raise PermissionError("You do not have permission to access counter orders for this store.")

        if store_id is not None and order.store_id != store_id:
            raise ValueError("The provided order code does not belong to the selected store.")

        return order

    @staticmethod
    def list_sales_memos(actor, filters: Optional[dict] = None, as_vendor: bool = False):
        """
        List sales memos with strict tenant isolation.
        - Customers view their own memos.
        - Vendors view memos for their stores (when as_vendor=True or actor has vendor role).
        - Staff / superusers can inspect all memos.
        """
        filters = filters or {}
        from shared.enums.enums import UserRoleEnum
        is_staff = getattr(actor, 'role', '') in [UserRoleEnum.STAFF, UserRoleEnum.SUPERUSER] or actor.is_staff or actor.is_superuser

        customer_id = None
        vendor_id = None

        if not is_staff:
            if as_vendor or getattr(actor, 'role', '') == UserRoleEnum.VENDOR:
                vendor_id = actor.id
            else:
                customer_id = actor.id

        return OrderRepository.get_sales_memos(
            customer_id=customer_id,
            vendor_id=vendor_id,
            store_id=filters.get('store_id'),
            from_date=filters.get('from_date'),
            to_date=filters.get('to_date'),
            search=filters.get('search')
        )

    @staticmethod
    def get_customer_spending_summary(customer):
        """
        Calculates multi-store spending analytics for a customer.
        """
        return OrderRepository.get_customer_spending_summary(customer.id)

    @staticmethod
    def reorder_to_card(order: Order, customer) -> Card:
        """
        One-tap reorder: clones items from a past completed order into an active draft shopping memo.
        Revalidates current active status of products and loads current authoritative prices.
        """
        if order.customer != customer and not getattr(customer, 'is_superuser', False):
            raise PermissionError("You can only reorder from your own past orders.")

        from cards.services.card_service import CardService
        from cards.repositories.card_repository import CardRepository

        card = CardService.get_or_create_active_memo(
            user=customer,
            store=order.store,
            shopping_mode=order.fulfillment_type if order.fulfillment_type == FulfillmentType.WALK_IN else 'remote'
        )

        added_count = 0
        for item in order.items.select_related('product').all():
            if item.product and not item.product.is_deleted and item.product.is_active:
                CardRepository.add_item_to_card(
                    card=card,
                    product=item.product,
                    quantity=item.quantity
                )
                added_count += 1

        if added_count == 0:
            raise ValueError("None of the products from this order are currently active in the store catalog.")

        return card


