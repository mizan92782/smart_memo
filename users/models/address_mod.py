from django.db import models
from django.conf import settings
from shared.base.base_model import BaseModel


class CustomerAddress(BaseModel):
    """
    Saved customer delivery addresses with recipient information,
    instructions, and GPS coordinates for distance-based delivery calculations.
    """
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_addresses',
        db_index=True
    )
    label = models.CharField(max_length=50, default="Home", help_text="e.g. Home, Office, Parents")
    recipient_name = models.CharField(max_length=150, blank=True, default='')
    phone_number = models.CharField(max_length=30)
    address_line = models.TextField(help_text="Street, building, apartment, house number")
    city = models.CharField(max_length=100, default="Dhaka")
    postal_code = models.CharField(max_length=20, blank=True, default='')
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    delivery_instructions = models.TextField(blank=True, default='', help_text="e.g. Leave with security, ring bell")
    is_default = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ['-is_default', '-created_at']
        verbose_name = 'Customer Address'
        verbose_name_plural = 'Customer Addresses'

    def __str__(self):
        return f"{self.label} ({self.customer.email}) - {self.address_line[:30]}"

    def formatted_snapshot(self) -> str:
        parts = [f"Recipient: {self.recipient_name or self.customer.email}"]
        if self.phone_number:
            parts.append(f"Phone: {self.phone_number}")
        parts.append(f"Address: {self.address_line}, {self.city} {self.postal_code}".strip())
        if self.delivery_instructions:
            parts.append(f"Instructions: {self.delivery_instructions}")
        return "\n".join(parts)
