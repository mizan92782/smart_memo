from decimal import Decimal
from typing import List, Dict, Any
from django.db import transaction
from django.utils import timezone
from purchases.models.purchase_mod import Supplier, Purchase, PurchaseItem, PurchaseStatus
from purchases.repositories.purchase_repository import PurchaseRepository
from inventory.services.inventory_service import InventoryService
from products.models.product_mod import Product
from stores.models.store_mod import Store


class PurchaseService:
    """
    Business service orchestrating purchase draft creation, approval,
    and receiving stock into inventory with strict idempotency and audit ledger entries.
    """

    @staticmethod
    @transaction.atomic
    def create_purchase(
        store: Store,
        supplier: Supplier,
        items_data: List[Dict[str, Any]],
        reference: str = "",
        additional_charges: Decimal = Decimal('0.00'),
        notes: str = "",
        actor=None
    ) -> Purchase:
        if supplier.store != store:
            raise ValueError("Supplier does not belong to the specified store.")

        if not items_data:
            raise ValueError("Purchase must include at least one item.")

        charges = Decimal(str(additional_charges)) if additional_charges else Decimal('0.00')
        if charges < Decimal('0.00'):
            raise ValueError("Additional charges cannot be negative.")

        purchase = Purchase.objects.create(
            store=store,
            supplier=supplier,
            status=PurchaseStatus.DRAFT,
            reference=reference,
            additional_charges=charges,
            notes=notes,
            created_by=actor
        )

        subtotal = Decimal('0.00')

        for item in items_data:
            product_id = item.get('product_id')
            quantity = Decimal(str(item.get('quantity', '0')))
            unit_cost = Decimal(str(item.get('unit_cost', '0')))

            if quantity <= Decimal('0.000'):
                raise ValueError(f"Quantity for product {product_id} must be strictly positive.")
            if unit_cost < Decimal('0.00'):
                raise ValueError(f"Unit cost for product {product_id} cannot be negative.")

            product = Product.objects.filter(pk=product_id, store=store, is_deleted=False).first()
            if not product:
                raise ValueError(f"Product {product_id} does not exist in store {store.name}.")

            line_total = (quantity * unit_cost).quantize(Decimal('0.01'))
            subtotal += line_total

            PurchaseItem.objects.create(
                purchase=purchase,
                product=product,
                quantity=quantity,
                unit_cost=unit_cost,
                line_total=line_total
            )

        purchase.subtotal = subtotal
        purchase.total_cost = (subtotal + charges).quantize(Decimal('0.01'))
        purchase.save(update_fields=['subtotal', 'total_cost'])

        return purchase

    @staticmethod
    def submit_purchase(purchase: Purchase, actor=None) -> Purchase:
        """Submit purchase for vendor approval before receipt."""
        if purchase.status != PurchaseStatus.DRAFT:
            raise ValueError(f"Cannot submit purchase in '{purchase.status}' state.")

        purchase.status = PurchaseStatus.SUBMITTED
        purchase.save(update_fields=['status', 'updated_at'])
        return purchase

    @staticmethod
    @transaction.atomic
    def receive_purchase(purchase_id: int, actor=None) -> Purchase:
        """
        Receive purchased stock into inventory.
        Validates state machine, updates stock balances, and logs ledger entries atomically.
        """
        purchase = (
            Purchase.objects
            .select_for_update()
            .filter(pk=purchase_id, is_deleted=False)
            .first()
        )
        if not purchase:
            raise ValueError("Purchase not found.")

        if purchase.status == PurchaseStatus.RECEIVED:
            raise ValueError("Purchase has already been received.")

        if purchase.status == PurchaseStatus.CANCELLED:
            raise ValueError("Cannot receive a cancelled purchase.")

        # Receive stock for each line item
        items = purchase.items.select_related('product').all()
        if not items:
            raise ValueError("Cannot receive a purchase with no line items.")

        for item in items:
            InventoryService.receive_stock(
                store=purchase.store,
                product=item.product,
                quantity=item.quantity,
                reference_id=purchase.purchase_number,
                actor=actor,
                notes=f"PO Receipt {purchase.purchase_number} - Supplier: {purchase.supplier.name}"
            )

        purchase.status = PurchaseStatus.RECEIVED
        purchase.received_date = timezone.now()
        purchase.save(update_fields=['status', 'received_date', 'updated_at'])

        return purchase

    @staticmethod
    @transaction.atomic
    def cancel_purchase(purchase_id: int, actor=None) -> Purchase:
        """Cancel a draft or submitted purchase order."""
        purchase = (
            Purchase.objects
            .select_for_update()
            .filter(pk=purchase_id, is_deleted=False)
            .first()
        )
        if not purchase:
            raise ValueError("Purchase not found.")

        if purchase.status == PurchaseStatus.RECEIVED:
            raise ValueError("Cannot cancel an already received purchase.")

        if purchase.status == PurchaseStatus.CANCELLED:
            raise ValueError("Purchase is already cancelled.")

        purchase.status = PurchaseStatus.CANCELLED
        purchase.save(update_fields=['status', 'updated_at'])
        return purchase
