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

    @staticmethod
    @transaction.atomic
    def generate_low_stock_purchase_orders(
        store: Store,
        default_supplier: Supplier = None,
        include_open_order_guard: bool = True,
        actor=None
    ) -> Dict[str, Any]:
        """
        Scan store inventory for low-stock products, automatically resolve suppliers and unit costs,
        and generate grouped draft purchase orders with anti-duplicate open order protection.
        """
        import uuid
        from collections import defaultdict
        from inventory.models.inventory_mod import StockBalance
        from audit.services.audit_service import AuditService
        from audit.models.audit_mod import AuditAction
        from notifications.models.notification_mod import NotificationType
        from notifications.services.notification_service import NotificationService

        # Fetch all stock balances for this store
        balances = (
            StockBalance.objects
            .filter(store=store)
            .select_related('product', 'product__primary_supplier')
        )

        low_stock_balances = [b for b in balances if b.is_low_stock]
        supplier_items_map = defaultdict(list)
        skipped_existing_orders = []
        unassigned_products = []

        for b in low_stock_balances:
            product = b.product
            if not product or product.is_deleted or not product.is_active:
                continue

            # Open Order Guard: avoid creating duplicate POs if active PO exists for this product
            if include_open_order_guard:
                has_open_po = PurchaseItem.objects.filter(
                    purchase__store=store,
                    purchase__status__in=[PurchaseStatus.DRAFT, PurchaseStatus.SUBMITTED],
                    product=product
                ).exists()
                if has_open_po:
                    skipped_existing_orders.append({
                        "product_id": product.id,
                        "product_name": product.name,
                        "available": str(b.available),
                        "reason": "Product already has a pending draft or submitted purchase order."
                    })
                    continue

            # Resolve Supplier
            supplier = None
            if product.primary_supplier and product.primary_supplier.store_id == store.id and product.primary_supplier.is_active:
                supplier = product.primary_supplier
            else:
                # Check most recent historical supplier
                last_receipt = (
                    PurchaseItem.objects
                    .filter(purchase__store=store, purchase__status=PurchaseStatus.RECEIVED, product=product)
                    .select_related('purchase__supplier')
                    .order_by('-created_at')
                    .first()
                )
                if last_receipt and last_receipt.purchase.supplier and last_receipt.purchase.supplier.is_active:
                    supplier = last_receipt.purchase.supplier
                elif default_supplier and default_supplier.store_id == store.id and default_supplier.is_active:
                    supplier = default_supplier

            if not supplier:
                unassigned_products.append({
                    "product_id": product.id,
                    "product_name": product.name,
                    "available": str(b.available),
                    "threshold": str(b.low_stock_threshold)
                })
                continue

            # Determine replenishment quantity
            needed = max(
                b.target_stock_level - b.available,
                b.reorder_quantity or product.reorder_quantity or Decimal('20.000')
            )
            reorder_qty = max(Decimal('1.000'), needed).quantize(Decimal('0.001'))

            # Determine procurement unit cost
            if product.cost_price > Decimal('0.00'):
                unit_cost = product.cost_price
            else:
                last_item = (
                    PurchaseItem.objects
                    .filter(product=product)
                    .order_by('-created_at')
                    .first()
                )
                if last_item and last_item.unit_cost > Decimal('0.00'):
                    unit_cost = last_item.unit_cost
                else:
                    unit_cost = (product.price * Decimal('0.70')).quantize(Decimal('0.01'))

            supplier_items_map[supplier].append({
                "product_id": product.id,
                "quantity": reorder_qty,
                "unit_cost": unit_cost
            })

        created_pos = []
        for supplier, items_data in supplier_items_map.items():
            po_ref = f"AUTO-REORDER-{uuid.uuid4().hex[:8].upper()}"
            purchase = PurchaseService.create_purchase(
                store=store,
                supplier=supplier,
                items_data=items_data,
                reference=po_ref,
                notes="Automated reorder triggered due to low stock threshold.",
                actor=actor
            )

            AuditService.log(
                action=AuditAction.PURCHASE_ORDER_AUTO_GENERATED,
                target_model="Purchase",
                target_id=str(purchase.id),
                actor=actor,
                store=store,
                details={
                    "purchase_number": purchase.purchase_number,
                    "supplier_id": str(supplier.id),
                    "supplier_name": supplier.name,
                    "items_count": len(items_data),
                    "total_cost": str(purchase.total_cost),
                    "reference": po_ref
                }
            )
            created_pos.append(purchase)

        # Dispatch alert notification to store vendor
        if created_pos:
            total_items = sum(len(items) for items in supplier_items_map.values())
            NotificationService.create_notification(
                recipient=store.vendor,
                store=store,
                title=f"Automated Purchase Orders Generated ({len(created_pos)} POs)",
                message=(
                    f"Generated {len(created_pos)} draft purchase order(s) for store '{store.name}' "
                    f"covering {total_items} low-stock product(s). Review and submit when ready."
                ),
                notification_type=NotificationType.PURCHASE_ORDER_GENERATED,
                metadata={
                    "store_id": store.id,
                    "pos": [p.purchase_number for p in created_pos],
                    "total_orders": len(created_pos),
                    "total_items": total_items
                }
            )

        from purchases.serializers.purchase_ser import PurchaseSerializer
        return {
            "store_id": store.id,
            "store_name": store.name,
            "created_orders_count": len(created_pos),
            "orders": PurchaseSerializer(created_pos, many=True).data,
            "skipped_open_orders_count": len(skipped_existing_orders),
            "skipped_existing_orders": skipped_existing_orders,
            "unassigned_products_count": len(unassigned_products),
            "unassigned_products": unassigned_products
        }
