from decimal import Decimal
from typing import List, Dict, Any, Optional
from django.db import transaction, models
from django.utils import timezone
from orders.models.order_mod import Order, OrderItem, OrderStatus, PaymentStatus
from orders.models.return_mod import OrderReturn, OrderReturnItem, ReturnStatus, ReturnReason
from orders.repositories.return_repository import ReturnRepository
from inventory.models.inventory_mod import StockBalance, StockLedgerEntry, StockMovementType
from shared.caching.cache_service import CacheService
from audit.services.audit_service import AuditService
from audit.models.audit_mod import AuditAction
from notifications.services.notification_service import NotificationService
from notifications.models.notification_mod import NotificationType


class OrderReturnService:
    """
    Manages order item returns, stock restock/damage write-off,
    proportional refund calculations, loyalty reversals, and credit notes.
    """

    @staticmethod
    @transaction.atomic
    def request_return(
        order: Order,
        customer,
        items_data: List[Dict[str, Any]],
        reason: str = ReturnReason.DAMAGED_DEFECTIVE,
        reason_notes: str = ""
    ) -> OrderReturn:
        """
        Customer initiates a return request for one or more items from a completed order.
        """
        if order.status != OrderStatus.COMPLETED:
            raise ValueError(f"Cannot request a return for order in '{order.status}' status. Only COMPLETED orders can be returned.")

        if order.customer_id != customer.id and not getattr(customer, 'is_staff', False):
            raise ValueError("You can only request returns for your own orders.")

        if not items_data:
            raise ValueError("At least one order item must be specified for return.")

        # Compute proportional discount ratio for fair financial refund
        effective_rate = Decimal('1.00')
        if order.subtotal > Decimal('0.00'):
            deductions = order.discount_amount + getattr(order, 'loyalty_discount_amount', Decimal('0.00'))
            effective_rate = max(Decimal('0.00'), (order.subtotal - deductions) / order.subtotal)

        total_refund = Decimal('0.00')
        valid_return_items = []

        for item_entry in items_data:
            order_item_id = item_entry.get('order_item_id')
            raw_qty = item_entry.get('quantity')
            if not order_item_id or raw_qty is None:
                raise ValueError("Each return item must contain 'order_item_id' and 'quantity'.")

            qty = Decimal(str(raw_qty))
            if qty <= Decimal('0.000'):
                raise ValueError("Return quantity must be strictly greater than zero.")

            try:
                order_item = order.items.get(pk=order_item_id)
            except OrderItem.DoesNotExist:
                raise ValueError(f"Order item #{order_item_id} does not belong to order {order.order_number}.")

            # Check previously requested / approved / completed returns for this item
            prior_returned = OrderReturnItem.objects.filter(
                order_item=order_item,
                order_return__status__in=[ReturnStatus.REQUESTED, ReturnStatus.APPROVED, ReturnStatus.COMPLETED],
                order_return__is_deleted=False
            ).aggregate(total=models.Sum('quantity'))['total'] or Decimal('0.000')

            remaining_qty = order_item.quantity - prior_returned
            if qty > remaining_qty:
                raise ValueError(
                    f"Requested return quantity {qty} exceeds available refundable quantity {remaining_qty} "
                    f"for item '{order_item.product_name_snapshot}'."
                )

            # Proportional unit price and subtotal
            unit_price = round(order_item.unit_price_snapshot * effective_rate, 2)
            item_subtotal = round(unit_price * qty, 2)
            total_refund += item_subtotal

            valid_return_items.append({
                'order_item': order_item,
                'product': order_item.product,
                'product_name_snapshot': order_item.product_name_snapshot,
                'quantity': qty,
                'unit_price': unit_price,
                'refund_subtotal': item_subtotal,
            })

        order_return = ReturnRepository.create_return(
            order=order,
            store=order.store,
            customer=customer,
            vendor=order.vendor or (order.store.vendor if order.store else None),
            status=ReturnStatus.REQUESTED,
            reason=reason,
            reason_notes=reason_notes,
            total_refund_amount=total_refund,
            restock_inventory=True
        )

        for v in valid_return_items:
            ReturnRepository.create_return_item(
                order_return=order_return,
                order_item=v['order_item'],
                product=v['product'],
                product_name_snapshot=v['product_name_snapshot'],
                quantity=v['quantity'],
                unit_price=v['unit_price'],
                refund_subtotal=v['refund_subtotal']
            )

        # Notify vendor about incoming return request
        if order.vendor:
            NotificationService.create_notification(
                recipient=order.vendor,
                store=order.store,
                title="New Customer Return Request",
                message=f"Customer {customer.email} submitted return {order_return.return_number} for order {order.order_number}.",
                notification_type=NotificationType.ORDER_RETURN_REQUESTED,
                metadata={
                    "return_number": order_return.return_number,
                    "order_number": order.order_number,
                    "refund_amount": str(total_refund),
                }
            )

        AuditService.log(
            action=AuditAction.ORDER_RETURN_REQUESTED,
            target_model="OrderReturn",
            target_id=str(order_return.id),
            actor=customer,
            store=order.store,
            details={
                "return_number": order_return.return_number,
                "order_number": order.order_number,
                "total_refund": str(total_refund),
                "reason": reason,
                "items_count": len(valid_return_items)
            }
        )

        return order_return

    @staticmethod
    @transaction.atomic
    def process_return(
        order_return: OrderReturn,
        actor,
        decision: str,
        restock_inventory: bool = True,
        rejection_reason: str = ""
    ) -> OrderReturn:
        """
        Store vendor (or staff) approves or rejects an order return request.
        If approved:
          - Automatically restocks inventory if restock_inventory=True with row locking.
          - Reverses earned loyalty points/stamps proportionally.
          - Updates order payment status if fully refunded.
          - Emits audit log and customer notification.
        """
        if order_return.status != ReturnStatus.REQUESTED:
            raise ValueError(f"Return request {order_return.return_number} is already in '{order_return.status}' status.")

        is_owner_vendor = (
            order_return.vendor_id == actor.id or
            (order_return.store and order_return.store.vendor_id == actor.id)
        )
        is_staff = getattr(actor, 'is_staff', False) or getattr(actor, 'is_superuser', False)
        if not (is_owner_vendor or is_staff):
            raise PermissionError("Only the store vendor or staff can process return requests.")

        decision = decision.strip().lower()
        if decision not in ['approved', 'rejected']:
            raise ValueError("Decision must be either 'approved' or 'rejected'.")

        if decision == 'rejected':
            if not rejection_reason.strip():
                raise ValueError("Rejection reason is required when rejecting a return request.")

            order_return.status = ReturnStatus.REJECTED
            order_return.rejection_reason = rejection_reason.strip()
            order_return.processed_by = actor
            order_return.processed_at = timezone.now()
            order_return.save(update_fields=['status', 'rejection_reason', 'processed_by', 'processed_at', 'updated_at'])

            NotificationService.create_notification(
                recipient=order_return.customer,
                store=order_return.store,
                title="Return Request Rejected",
                message=f"Your return request {order_return.return_number} was rejected by {order_return.store.name}: {rejection_reason}",
                notification_type=NotificationType.ORDER_RETURN_PROCESSED,
                metadata={
                    "return_number": order_return.return_number,
                    "order_number": order_return.order.order_number,
                    "decision": "rejected",
                }
            )

            AuditService.log(
                action=AuditAction.ORDER_RETURN_PROCESSED,
                target_model="OrderReturn",
                target_id=str(order_return.id),
                actor=actor,
                store=order_return.store,
                details={
                    "return_number": order_return.return_number,
                    "decision": "rejected",
                    "reason": rejection_reason
                }
            )
            return order_return

        # APPROVAL WORKFLOW
        order_return.restock_inventory = restock_inventory
        items = list(order_return.items.select_related('product', 'order_item').all())
        items_snapshot = []

        for item in items:
            items_snapshot.append({
                'product_id': item.product_id,
                'product_name': item.product_name_snapshot,
                'quantity': str(item.quantity),
                'unit_price': str(item.unit_price),
                'refund_subtotal': str(item.refund_subtotal),
            })

            if item.product and order_return.store:
                if restock_inventory:
                    # Concurrency-safe stock restoration
                    balance, _ = StockBalance.objects.select_for_update().get_or_create(
                        store=order_return.store,
                        product=item.product,
                        defaults={'on_hand': Decimal('0.000'), 'reserved': Decimal('0.000')}
                    )
                    balance.on_hand += item.quantity
                    balance.save(update_fields=['on_hand', 'updated_at'])

                    item.product.stock = balance.on_hand
                    item.product.save(update_fields=['stock', 'updated_at'])

                    StockLedgerEntry.objects.create(
                        store=order_return.store,
                        product=item.product,
                        movement_type=StockMovementType.RETURN,
                        quantity=item.quantity,
                        balance_after=balance.on_hand,
                        reference_id=order_return.return_number,
                        actor=actor,
                        notes=f"Customer return restock: {order_return.get_reason_display()}"
                    )
                else:
                    # Write-off as damage / spoil / disposal
                    balance = StockBalance.objects.filter(store=order_return.store, product=item.product).first()
                    on_hand = balance.on_hand if balance else Decimal('0.000')
                    StockLedgerEntry.objects.create(
                        store=order_return.store,
                        product=item.product,
                        movement_type=StockMovementType.DAMAGE_LOSS,
                        quantity=Decimal('0.000'),
                        balance_after=on_hand,
                        reference_id=order_return.return_number,
                        actor=actor,
                        notes=f"Defective return not restocked (damaged/disposed): {order_return.get_reason_display()}"
                    )

        # Invalidate store catalog cache if inventory updated
        if order_return.store_id and restock_inventory:
            CacheService.invalidate_catalog(order_return.store_id)

        # Proportional Loyalty Points & Stamp Reversals
        order = order_return.order
        points_to_revert = 0
        stamps_to_revert = 0

        if order.total_amount > Decimal('0.00') and order.loyalty_points_earned > 0:
            refund_ratio = min(Decimal('1.00'), order_return.total_refund_amount / order.total_amount)
            points_to_revert = int(order.loyalty_points_earned * refund_ratio)

        if order.loyalty_stamps_earned > 0 and order_return.total_refund_amount >= order.total_amount:
            stamps_to_revert = order.loyalty_stamps_earned

        if (points_to_revert > 0 or stamps_to_revert > 0) and order_return.store:
            from stores.models.loyalty_mod import CustomerStoreLoyalty, LoyaltyTransaction, LoyaltyTransactionType
            cust_loyalty = CustomerStoreLoyalty.objects.filter(
                store=order_return.store,
                customer=order_return.customer
            ).first()
            if cust_loyalty:
                if points_to_revert > 0:
                    cust_loyalty.points_balance = max(0, cust_loyalty.points_balance - points_to_revert)
                    LoyaltyTransaction.objects.create(
                        loyalty_account=cust_loyalty,
                        customer=order_return.customer,
                        store=order_return.store,
                        vendor=order_return.vendor,
                        order=order,
                        transaction_type=LoyaltyTransactionType.RETURN_REVERSAL,
                        points_change=-points_to_revert,
                        stamps_change=0,
                        points_balance_after=cust_loyalty.points_balance,
                        stamps_balance_after=cust_loyalty.stamps_balance,
                        notes=f"Loyalty reversal for return {order_return.return_number}"
                    )
                if stamps_to_revert > 0:
                    cust_loyalty.stamps_balance = max(0, cust_loyalty.stamps_balance - stamps_to_revert)
                    LoyaltyTransaction.objects.create(
                        loyalty_account=cust_loyalty,
                        customer=order_return.customer,
                        store=order_return.store,
                        vendor=order_return.vendor,
                        order=order,
                        transaction_type=LoyaltyTransactionType.RETURN_REVERSAL,
                        points_change=0,
                        stamps_change=-stamps_to_revert,
                        points_balance_after=cust_loyalty.points_balance,
                        stamps_balance_after=cust_loyalty.stamps_balance,
                        notes=f"Stamp reversal for full return {order_return.return_number}"
                    )
                cust_loyalty.save(update_fields=['points_balance', 'stamps_balance', 'updated_at'])


        order_return.loyalty_points_deducted = points_to_revert
        order_return.loyalty_stamps_deducted = stamps_to_revert
        order_return.items_snapshot = items_snapshot
        order_return.status = ReturnStatus.COMPLETED
        order_return.processed_by = actor
        order_return.processed_at = timezone.now()
        order_return.save(update_fields=[
            'status', 'restock_inventory', 'items_snapshot', 'processed_by',
            'processed_at', 'loyalty_points_deducted', 'loyalty_stamps_deducted', 'updated_at'
        ])

        # Check if entire order is fully refunded
        total_order_returned = OrderReturnItem.objects.filter(
            order_return__order=order,
            order_return__status=ReturnStatus.COMPLETED,
            order_return__is_deleted=False
        ).aggregate(total=models.Sum('refund_subtotal'))['total'] or Decimal('0.00')

        if total_order_returned >= (order.total_amount - order.delivery_fee):
            order.payment_status = PaymentStatus.REFUNDED
            order.save(update_fields=['payment_status', 'updated_at'])

        # Notify Customer
        NotificationService.create_notification(
            recipient=order_return.customer,
            store=order_return.store,
            title="Return Approved & Refund Processed",
            message=f"Your return {order_return.return_number} has been approved for a refund of {order_return.total_refund_amount}.",
            notification_type=NotificationType.ORDER_RETURN_PROCESSED,
            metadata={
                "return_number": order_return.return_number,
                "order_number": order.order_number,
                "refund_amount": str(order_return.total_refund_amount),
                "decision": "approved",
            }
        )

        AuditService.log(
            action=AuditAction.ORDER_RETURN_PROCESSED,
            target_model="OrderReturn",
            target_id=str(order_return.id),
            actor=actor,
            store=order_return.store,
            details={
                "return_number": order_return.return_number,
                "order_number": order.order_number,
                "refund_amount": str(order_return.total_refund_amount),
                "restocked": restock_inventory,
                "loyalty_points_deducted": points_to_revert
            }
        )

        return order_return
