from decimal import Decimal
from typing import Optional, List
from django.db.models import QuerySet
from stores.models.loyalty_mod import (
    StoreLoyaltyProgram,
    CustomerStoreLoyalty,
    LoyaltyTransaction,
    LoyaltyProgramType,
    LoyaltyTransactionType
)


class LoyaltyRepository:
    """Repository handling static database operations for Store Loyalty and Customer Stamp Cards."""

    @staticmethod
    def get_or_create_program(store, vendor=None) -> StoreLoyaltyProgram:
        program, _ = StoreLoyaltyProgram.objects.get_or_create(
            store=store,
            defaults={'vendor': vendor or getattr(store, 'vendor', None)}
        )
        return program

    @staticmethod
    def get_program_by_store(store_id: int) -> Optional[StoreLoyaltyProgram]:
        try:
            return StoreLoyaltyProgram.objects.select_related('store', 'vendor').get(store_id=store_id)
        except StoreLoyaltyProgram.DoesNotExist:
            return None

    @staticmethod
    def update_program(program: StoreLoyaltyProgram, **fields) -> StoreLoyaltyProgram:
        update_fields = []
        for key, value in fields.items():
            if hasattr(program, key) and value is not None:
                setattr(program, key, value)
                update_fields.append(key)
        if update_fields:
            if 'updated_at' not in update_fields:
                update_fields.append('updated_at')
            program.save(update_fields=update_fields)
        return program

    @staticmethod
    def get_or_create_customer_loyalty(customer, store, vendor=None, for_update: bool = False) -> CustomerStoreLoyalty:
        v = vendor or (store.vendor if hasattr(store, 'vendor') else None)
        if for_update:
            # Try to get with lock, otherwise create
            try:
                return CustomerStoreLoyalty.objects.select_for_update().get(customer=customer, store=store)
            except CustomerStoreLoyalty.DoesNotExist:
                return CustomerStoreLoyalty.objects.create(
                    customer=customer,
                    store=store,
                    vendor=v
                )
        loyalty, _ = CustomerStoreLoyalty.objects.get_or_create(
            customer=customer,
            store=store,
            defaults={'vendor': v}
        )
        return loyalty

    @staticmethod
    def get_customer_loyalty(customer_id: int, store_id: int, for_update: bool = False) -> Optional[CustomerStoreLoyalty]:
        qs = CustomerStoreLoyalty.objects.select_related('customer', 'store', 'vendor')
        if for_update:
            qs = qs.select_for_update()
        try:
            return qs.get(customer_id=customer_id, store_id=store_id)
        except CustomerStoreLoyalty.DoesNotExist:
            return None

    @staticmethod
    def get_all_customer_loyalties(customer_id: int) -> QuerySet[CustomerStoreLoyalty]:
        return CustomerStoreLoyalty.objects.filter(
            customer_id=customer_id
        ).select_related('store', 'store__vendor').order_by('-points_balance', '-stamps_balance')

    @staticmethod
    def get_store_loyal_customers(store_id: int, limit: int = 50) -> QuerySet[CustomerStoreLoyalty]:
        return CustomerStoreLoyalty.objects.filter(
            store_id=store_id
        ).select_related('customer').order_by('-points_balance', '-total_points_earned')[:limit]

    @staticmethod
    def create_transaction(
        loyalty_account: CustomerStoreLoyalty,
        customer,
        store,
        transaction_type: str,
        points_change: int,
        stamps_change: int,
        points_balance_after: int,
        stamps_balance_after: int,
        discount_amount_applied: Decimal = Decimal('0.00'),
        order=None,
        sales_memo=None,
        notes: str = ''
    ) -> LoyaltyTransaction:
        vendor = getattr(store, 'vendor', None) or loyalty_account.vendor
        return LoyaltyTransaction.objects.create(
            loyalty_account=loyalty_account,
            customer=customer,
            store=store,
            vendor=vendor,
            order=order,
            sales_memo=sales_memo,
            transaction_type=transaction_type,
            points_change=points_change,
            stamps_change=stamps_change,
            points_balance_after=points_balance_after,
            stamps_balance_after=stamps_balance_after,
            discount_amount_applied=discount_amount_applied,
            notes=notes
        )

    @staticmethod
    def get_transactions_for_account(loyalty_account_id: int) -> QuerySet[LoyaltyTransaction]:
        return LoyaltyTransaction.objects.filter(
            loyalty_account_id=loyalty_account_id
        ).select_related('order', 'sales_memo').order_by('-created_at')
