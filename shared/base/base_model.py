"""
Shared Base Models — Abstract base classes for all project models.
All app models should inherit from BaseModel or TimestampedModel.
"""
from django.db import models


class TimestampedModel(models.Model):
    """
    Abstract base model providing created_at and updated_at timestamps.
    Inherit this for any model that needs audit timestamps.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """
    Abstract base model providing soft-delete capability.
    Records are marked deleted rather than physically removed.
    """
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=['is_deleted', 'deleted_at'])


class BaseModel(TimestampedModel, SoftDeleteModel):
    """
    Full-featured base model combining timestamps + soft delete.
    Use this for most app models.
    """
    class Meta:
        abstract = True
