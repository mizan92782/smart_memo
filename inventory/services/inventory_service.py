from decimal import Decimal
from django.db import transaction
from inventory.models.inventory_mod import StockBalance, StockLedgerEntry, StockMovementType
from inventory.repositories.inventory_repository import InventoryRepository
from stores.models.store_mod import Store
from products.models.product_mod import Product


class InventoryService:
    """
    Business operations for inventory balance updates, stock reservations,
    and ledger audit trail with pessimistic row-locking (select_for_update).
    """

    @staticmethod
    @transaction.atomic
    def receive_stock(
        store: Store,
        product: Product,
        quantity: Decimal,
        reference_id: str = "",
        actor=None,
        notes: str = ""
    ) -> StockBalance:
        """Receive newly purchased or produced stock into on-hand inventory."""
        if quantity <= 0:
            raise ValueError("Quantity to receive must be strictly positive.")

        # Ensure balance exists and acquire row lock
        InventoryRepository.get_or_create_balance(store, product)
        balance = StockBalance.objects.select_for_update().get(store=store, product=product)

        balance.on_hand += Decimal(str(quantity))
        balance.save(update_fields=['on_hand', 'updated_at'])

        # Synchronize read-model product.stock
        product.stock = balance.on_hand
        product.save(update_fields=['stock', 'updated_at'])

        InventoryRepository.log_ledger_entry(
            store=store,
            product=product,
            movement_type=StockMovementType.PURCHASE_RECEIVE,
            quantity=Decimal(str(quantity)),
            balance_after=balance.on_hand,
            reference_id=reference_id,
            actor=actor,
            notes=notes
        )
        return balance

    @staticmethod
    @transaction.atomic
    def reserve_stock(
        store: Store,
        product: Product,
        quantity: Decimal,
        reference_id: str = "",
        actor=None,
        notes: str = ""
    ) -> StockBalance:
        """Atomically reserve stock for an order. Fails if available stock < quantity."""
        qty = Decimal(str(quantity))
        if qty <= 0:
            raise ValueError("Quantity to reserve must be strictly positive.")

        InventoryRepository.get_or_create_balance(store, product)
        balance = StockBalance.objects.select_for_update().get(store=store, product=product)

        if balance.available < qty:
            raise ValueError(
                f"Insufficient stock for '{product.name}'. "
                f"Available: {balance.available}, Requested: {qty}"
            )

        balance.reserved += qty
        balance.save(update_fields=['reserved', 'updated_at'])

        InventoryRepository.log_ledger_entry(
            store=store,
            product=product,
            movement_type=StockMovementType.ORDER_RESERVE,
            quantity=qty,
            balance_after=balance.available,
            reference_id=reference_id,
            actor=actor,
            notes=notes
        )
        return balance

    @staticmethod
    @transaction.atomic
    def fulfill_stock(
        store: Store,
        product: Product,
        quantity: Decimal,
        reference_id: str = "",
        actor=None,
        notes: str = ""
    ) -> StockBalance:
        """Convert reserved stock into sold stock upon order delivery/completion."""
        qty = Decimal(str(quantity))
        if qty <= 0:
            raise ValueError("Quantity to fulfill must be strictly positive.")

        InventoryRepository.get_or_create_balance(store, product)
        balance = StockBalance.objects.select_for_update().get(store=store, product=product)

        balance.reserved = max(Decimal('0.000'), balance.reserved - qty)
        balance.on_hand = max(Decimal('0.000'), balance.on_hand - qty)
        balance.save(update_fields=['reserved', 'on_hand', 'updated_at'])

        product.stock = balance.on_hand
        product.save(update_fields=['stock', 'updated_at'])

        InventoryRepository.log_ledger_entry(
            store=store,
            product=product,
            movement_type=StockMovementType.ORDER_FULFILL,
            quantity=qty,
            balance_after=balance.on_hand,
            reference_id=reference_id,
            actor=actor,
            notes=notes
        )

        from notifications.services.notification_service import NotificationService
        NotificationService.notify_low_stock_if_needed(store, product, balance)

        return balance


    @staticmethod
    @transaction.atomic
    def release_reserved_stock(
        store: Store,
        product: Product,
        quantity: Decimal,
        reference_id: str = "",
        actor=None,
        notes: str = ""
    ) -> StockBalance:
        """Release reserved stock back to available pool upon order cancellation or rejection."""
        qty = Decimal(str(quantity))
        InventoryRepository.get_or_create_balance(store, product)
        balance = StockBalance.objects.select_for_update().get(store=store, product=product)

        balance.reserved = max(Decimal('0.000'), balance.reserved - qty)
        balance.save(update_fields=['reserved', 'updated_at'])

        InventoryRepository.log_ledger_entry(
            store=store,
            product=product,
            movement_type=StockMovementType.ORDER_CANCEL_RESTORE,
            quantity=qty,
            balance_after=balance.available,
            reference_id=reference_id,
            actor=actor,
            notes=notes
        )
        return balance

    @staticmethod
    @transaction.atomic
    def adjust_stock(
        store: Store,
        product: Product,
        quantity: Decimal,
        movement_type: str = StockMovementType.MANUAL_ADJUSTMENT,
        actor=None,
        notes: str = ""
    ) -> StockBalance:
        """Manual adjustment, damage write-off, or customer return."""
        qty = Decimal(str(quantity))
        InventoryRepository.get_or_create_balance(store, product)
        balance = StockBalance.objects.select_for_update().get(store=store, product=product)

        new_on_hand = balance.on_hand + qty
        if new_on_hand < balance.reserved:
            raise ValueError(
                f"Adjustment cannot reduce on-hand ({new_on_hand}) below reserved ({balance.reserved})."
            )

        balance.on_hand = new_on_hand
        balance.save(update_fields=['on_hand', 'updated_at'])

        product.stock = balance.on_hand
        product.save(update_fields=['stock', 'updated_at'])

        InventoryRepository.log_ledger_entry(
            store=store,
            product=product,
            movement_type=movement_type,
            quantity=qty,
            balance_after=balance.on_hand,
            reference_id="MANUAL",
            actor=actor,
            notes=notes
        )

        from notifications.services.notification_service import NotificationService
        NotificationService.notify_low_stock_if_needed(store, product, balance)

        from audit.services.audit_service import AuditService
        from audit.models.audit_mod import AuditAction
        AuditService.log(
            action=AuditAction.INVENTORY_ADJUSTED,
            target_model="StockBalance",
            target_id=str(balance.id),
            actor=actor,
            store=store,
            details={
                "product_id": str(product.id),
                "adjustment_qty": str(qty),
                "previous_on_hand": str(new_on_hand - qty),
                "new_on_hand": str(new_on_hand),
                "movement_type": movement_type,
                "notes": notes
            }
        )

        return balance

