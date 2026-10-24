import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from shared.base.base_model import BaseModel
from stores.models.store_mod import Store
from products.models.product_mod import Product


class Supplier(BaseModel):
    """
    Store-scoped supplier directory.
    Vendors manage their own vendor-specific suppliers.
    """
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='suppliers'
    )
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=150, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")
    address = models.TextField(blank=True, default="")
    tax_id = models.CharField(max_length=100, blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Supplier'
        verbose_name_plural = 'Suppliers'
        constraints = [
            models.UniqueConstraint(
                fields=['store', 'name'],
                name='unique_store_supplier_name'
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.store.name})"


class PurchaseStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    SUBMITTED = 'submitted', 'Submitted'
    RECEIVED = 'received', 'Received'
    CANCELLED = 'cancelled', 'Cancelled'


class Purchase(BaseModel):
    """
    Purchase document for procuring stock from a supplier.
    Inventory is ONLY credited upon confirming receipt (status=RECEIVED).
    """
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='purchases'
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='purchases'
    )
    purchase_number = models.CharField(max_length=64, unique=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=PurchaseStatus.choices,
        default=PurchaseStatus.DRAFT
    )
    reference = models.CharField(max_length=100, blank=True, default="")
    order_date = models.DateField(auto_now_add=True)
    received_date = models.DateTimeField(null=True, blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    additional_charges = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    notes = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Purchase'
        verbose_name_plural = 'Purchases'

    def save(self, *args, **kwargs):
        if not self.purchase_number:
            self.purchase_number = f"PO-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.purchase_number} - {self.supplier.name} ({self.status})"


class PurchaseItem(BaseModel):
    """
    Line item for goods procured in a purchase order.
    """
    purchase = models.ForeignKey(
        Purchase,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='purchase_items'
    )
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = 'Purchase Item'
        verbose_name_plural = 'Purchase Items'

    def __str__(self):
        return f"{self.product.name} x {self.quantity} in {self.purchase.purchase_number}"
