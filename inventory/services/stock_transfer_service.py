from decimal import Decimal
from typing import List, Dict, Any, Optional
from django.db import transaction
from django.utils import timezone
from stores.models.store_mod import Store
from products.models.product_mod import Product
from categories.models.category_mod import Category
from inventory.models.inventory_mod import StockBalance, StockLedgerEntry, StockMovementType
from inventory.models.transfer_mod import StockTransfer, StockTransferItem, TransferStatus
from inventory.repositories.transfer_repository import TransferRepository
from shared.caching.cache_service import CacheService
from audit.services.audit_service import AuditService
from audit.models.audit_mod import AuditAction
from notifications.services.notification_service import NotificationService
from notifications.models.notification_mod import NotificationType


class StockTransferService:
    """
    Manages inter-store inventory transfer lifecycle:
    Draft -> Dispatch (pessimistic deduct & transit) -> Receive (pessimistic credit & destination sync) / Cancel.
    """

    @staticmethod
    @transaction.atomic
    def create_transfer(
        vendor,
        source_store_id: int,
        destination_store_id: int,
        items_data: List[Dict[str, Any]],
        tracking_notes: str = "",
        driver_name: str = "",
        driver_phone: str = "",
        vehicle_type: str = ""
    ) -> StockTransfer:
        """
        Creates a new draft inter-store stock transfer.
        Enforces tenant scoping: vendor must own both source and destination stores.
        """
        if int(source_store_id) == int(destination_store_id):
            raise ValueError("Source store and destination store cannot be the same.")

        source_store = Store.objects.filter(pk=source_store_id, is_deleted=False).first()
        destination_store = Store.objects.filter(pk=destination_store_id, is_deleted=False).first()

        if not source_store or not destination_store:
            raise ValueError("Source or destination store not found.")

        is_staff = getattr(vendor, 'is_staff', False) or getattr(vendor, 'is_superuser', False)
        if not is_staff:
            if source_store.vendor_id != vendor.id or destination_store.vendor_id != vendor.id:
                raise PermissionError("You can only transfer stock between stores you own.")

        if not source_store.is_active or not destination_store.is_active:
            raise ValueError("Both source and destination stores must be active.")

        if not items_data:
            raise ValueError("At least one product item must be specified for transfer.")

        validated_items = []
        for entry in items_data:
            product_id = entry.get('product_id')
            raw_qty = entry.get('quantity')
            if not product_id or raw_qty is None:
                raise ValueError("Each item must include 'product_id' and 'quantity'.")

            qty = Decimal(str(raw_qty))
            if qty <= Decimal('0.000'):
                raise ValueError("Transfer quantity must be strictly greater than zero.")

            product = Product.objects.filter(pk=product_id, store=source_store, is_deleted=False).first()
            if not product:
                raise ValueError(f"Product #{product_id} does not belong to source store '{source_store.name}'.")

            balance = StockBalance.objects.filter(store=source_store, product=product).first()
            available = balance.available if balance else Decimal('0.000')
            if available < qty:
                raise ValueError(
                    f"Insufficient stock for '{product.name}' in {source_store.name}. "
                    f"Available: {available}, Requested: {qty}"
                )

            validated_items.append({
                'product': product,
                'product_name_snapshot': product.name,
                'quantity': qty
            })

        transfer = TransferRepository.create_transfer(
            vendor=vendor,
            source_store=source_store,
            destination_store=destination_store,
            status=TransferStatus.DRAFT,
            tracking_notes=tracking_notes,
            driver_name=driver_name,
            driver_phone=driver_phone,
            vehicle_type=vehicle_type
        )

        for v in validated_items:
            TransferRepository.create_transfer_item(
                transfer=transfer,
                source_product=v['product'],
                product_name_snapshot=v['product_name_snapshot'],
                quantity=v['quantity']
            )

        return transfer

    @staticmethod
    @transaction.atomic
    def dispatch_transfer(transfer: StockTransfer, actor) -> StockTransfer:
        """
        Dispatches transfer into transit:
        Deducts stock from source store on-hand with row locking and logs TRANSFER_OUT.
        """
        if transfer.status != TransferStatus.DRAFT:
            raise ValueError(f"Cannot dispatch transfer in '{transfer.status}' status. Must be DRAFT.")

        is_staff = getattr(actor, 'is_staff', False) or getattr(actor, 'is_superuser', False)
        if not is_staff and transfer.vendor_id != actor.id:
            raise PermissionError("You do not own this stock transfer.")

        for item in transfer.items.select_related('source_product').all():
            product = item.source_product
            balance = StockBalance.objects.select_for_update().get(store=transfer.source_store, product=product)

            if balance.available < item.quantity:
                raise ValueError(
                    f"Stock insufficient at dispatch for '{product.name}'. "
                    f"Available: {balance.available}, Requested: {item.quantity}"
                )

            balance.on_hand -= item.quantity
            balance.save(update_fields=['on_hand', 'updated_at'])

            product.stock = balance.on_hand
            product.save(update_fields=['stock', 'updated_at'])

            StockLedgerEntry.objects.create(
                store=transfer.source_store,
                product=product,
                movement_type=StockMovementType.TRANSFER_OUT,
                quantity=item.quantity,
                balance_after=balance.on_hand,
                reference_id=transfer.transfer_number,
                actor=actor,
                notes=f"Stock transfer dispatched to {transfer.destination_store.name}"
            )

            NotificationService.notify_low_stock_if_needed(transfer.source_store, product, balance)

        CacheService.invalidate_catalog(transfer.source_store_id)

        transfer.status = TransferStatus.IN_TRANSIT
        transfer.dispatched_at = timezone.now()
        transfer.save(update_fields=['status', 'dispatched_at', 'updated_at'])

        AuditService.log(
            action=AuditAction.STOCK_TRANSFER_DISPATCHED,
            target_model="StockTransfer",
            target_id=str(transfer.id),
            actor=actor,
            store=transfer.source_store,
            details={
                "transfer_number": transfer.transfer_number,
                "destination_store": transfer.destination_store.name,
                "total_items": transfer.items.count(),
                "total_quantity": str(transfer.total_quantity)
            }
        )

        NotificationService.create_notification(
            recipient=transfer.vendor,
            store=transfer.destination_store,
            title="Stock Transfer Dispatched",
            message=(
                f"Transfer {transfer.transfer_number} with {transfer.items.count()} items "
                f"dispatched from {transfer.source_store.name} to {transfer.destination_store.name}."
            ),
            notification_type=NotificationType.STOCK_TRANSFER_DISPATCHED,
            metadata={"transfer_number": transfer.transfer_number}
        )

        return transfer

    @staticmethod
    @transaction.atomic
    def receive_transfer(
        transfer: StockTransfer,
        actor,
        items_received: Optional[List[Dict[str, Any]]] = None
    ) -> StockTransfer:
        """
        Receives transit stock at destination store:
        Resolves or creates matching product in destination store, credits stock with row locking,
        and logs TRANSFER_IN.
        """
        if transfer.status != TransferStatus.IN_TRANSIT:
            raise ValueError(f"Cannot receive transfer in '{transfer.status}' status. Must be IN_TRANSIT.")

        is_staff = getattr(actor, 'is_staff', False) or getattr(actor, 'is_superuser', False)
        if not is_staff and transfer.vendor_id != actor.id:
            raise PermissionError("You do not own this stock transfer.")

        received_qty_map = {}
        if items_received:
            for r in items_received:
                item_id = r.get('transfer_item_id')
                qty = r.get('received_quantity')
                if item_id is not None and qty is not None:
                    received_qty_map[int(item_id)] = Decimal(str(qty))

        for item in transfer.items.select_related('source_product').all():
            src_prod = item.source_product
            rcvd_qty = received_qty_map.get(item.id, item.quantity)
            if rcvd_qty < Decimal('0.000'):
                raise ValueError(f"Received quantity cannot be negative for '{src_prod.name}'.")

            # Match product in destination store by barcode -> SKU -> name
            dest_prod = None
            if getattr(src_prod, 'barcode', ''):
                dest_prod = Product.objects.filter(store=transfer.destination_store, barcode=src_prod.barcode, is_deleted=False).first()
            if not dest_prod and src_prod.sku:
                dest_prod = Product.objects.filter(store=transfer.destination_store, sku=src_prod.sku, is_deleted=False).first()
            if not dest_prod:
                dest_prod = Product.objects.filter(store=transfer.destination_store, name__iexact=src_prod.name, is_deleted=False).first()

            # If product does not exist in destination store, auto-provision it
            if not dest_prod:
                # Find or create corresponding category in destination store
                dest_cat = None
                if src_prod.category:
                    dest_cat = Category.objects.filter(store=transfer.destination_store, name__iexact=src_prod.category.name, is_deleted=False).first()
                    if not dest_cat:
                        dest_cat = Category.objects.create(
                            store=transfer.destination_store,
                            name=src_prod.category.name
                        )


                dest_prod = Product.objects.create(
                    store=transfer.destination_store,
                    category=dest_cat,
                    name=src_prod.name,
                    sku=src_prod.sku,
                    barcode=getattr(src_prod, 'barcode', ''),
                    price=src_prod.price,
                    measure=src_prod.measure,
                    unit=src_prod.unit,
                    currency=src_prod.currency,
                    stock=Decimal('0.000'),
                    is_active=src_prod.is_active,
                    aisle=getattr(src_prod, 'aisle', ''),
                    shelf_location=getattr(src_prod, 'shelf_location', '')
                )


            # Atomically credit destination store stock balance
            dest_balance, _ = StockBalance.objects.select_for_update().get_or_create(
                store=transfer.destination_store,
                product=dest_prod,
                defaults={'on_hand': Decimal('0.000'), 'reserved': Decimal('0.000')}
            )
            dest_balance.on_hand += rcvd_qty
            dest_balance.save(update_fields=['on_hand', 'updated_at'])

            dest_prod.stock = dest_balance.on_hand
            dest_prod.save(update_fields=['stock', 'updated_at'])

            StockLedgerEntry.objects.create(
                store=transfer.destination_store,
                product=dest_prod,
                movement_type=StockMovementType.TRANSFER_IN,
                quantity=rcvd_qty,
                balance_after=dest_balance.on_hand,
                reference_id=transfer.transfer_number,
                actor=actor,
                notes=f"Stock transfer received from {transfer.source_store.name}"
            )

            item.destination_product = dest_prod
            item.received_quantity = rcvd_qty
            item.save(update_fields=['destination_product', 'received_quantity', 'updated_at'])

        CacheService.invalidate_catalog(transfer.destination_store_id)

        transfer.status = TransferStatus.RECEIVED
        transfer.received_at = timezone.now()
        transfer.received_by = actor
        transfer.save(update_fields=['status', 'received_at', 'received_by', 'updated_at'])

        AuditService.log(
            action=AuditAction.STOCK_TRANSFER_RECEIVED,
            target_model="StockTransfer",
            target_id=str(transfer.id),
            actor=actor,
            store=transfer.destination_store,
            details={
                "transfer_number": transfer.transfer_number,
                "source_store": transfer.source_store.name,
                "total_items": transfer.items.count(),
            }
        )

        NotificationService.create_notification(
            recipient=transfer.vendor,
            store=transfer.destination_store,
            title="Stock Transfer Received",
            message=f"Transfer {transfer.transfer_number} received into {transfer.destination_store.name}.",
            notification_type=NotificationType.STOCK_TRANSFER_RECEIVED,
            metadata={"transfer_number": transfer.transfer_number}
        )

        return transfer

    @staticmethod
    @transaction.atomic
    def cancel_transfer(transfer: StockTransfer, actor, reason: str = "") -> StockTransfer:
        """
        Cancels transfer:
        If already IN_TRANSIT, atomically restores stock back to source store with TRANSFER_CANCEL_RESTORE.
        """
        if transfer.status not in [TransferStatus.DRAFT, TransferStatus.IN_TRANSIT]:
            raise ValueError(f"Cannot cancel transfer in '{transfer.status}' status.")

        is_staff = getattr(actor, 'is_staff', False) or getattr(actor, 'is_superuser', False)
        if not is_staff and transfer.vendor_id != actor.id:
            raise PermissionError("You do not own this stock transfer.")

        if transfer.status == TransferStatus.IN_TRANSIT:
            for item in transfer.items.select_related('source_product').all():
                product = item.source_product
                balance = StockBalance.objects.select_for_update().get(store=transfer.source_store, product=product)

                balance.on_hand += item.quantity
                balance.save(update_fields=['on_hand', 'updated_at'])

                product.stock = balance.on_hand
                product.save(update_fields=['stock', 'updated_at'])

                StockLedgerEntry.objects.create(
                    store=transfer.source_store,
                    product=product,
                    movement_type=StockMovementType.TRANSFER_CANCEL_RESTORE,
                    quantity=item.quantity,
                    balance_after=balance.on_hand,
                    reference_id=transfer.transfer_number,
                    actor=actor,
                    notes=f"Stock transfer cancelled and restored. Reason: {reason}"
                )

            CacheService.invalidate_catalog(transfer.source_store_id)

        transfer.status = TransferStatus.CANCELLED
        transfer.tracking_notes = f"{transfer.tracking_notes}\n[Cancelled]: {reason}".strip()
        transfer.save(update_fields=['status', 'tracking_notes', 'updated_at'])

        AuditService.log(
            action=AuditAction.STOCK_TRANSFER_CANCELLED,
            target_model="StockTransfer",
            target_id=str(transfer.id),
            actor=actor,
            store=transfer.source_store,
            details={
                "transfer_number": transfer.transfer_number,
                "reason": reason
            }
        )

        return transfer
