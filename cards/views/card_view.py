"""
cards/views/card_view.py — Views for Card App
"""
from decimal import Decimal
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from cards.models.card_mod import Card
from cards.serializers.card_ser import CardSerializer
from cards.services.card_service import CardService
from cards.repositories.card_repository import CardRepository
from shared.responses.responses import custome_success_response, custome_error_response


class CardViewSet(viewsets.ModelViewSet):
    """ViewSet for Card (Draft Memo) CRUD, item operations, and checkout."""
    serializer_class = CardSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return Card.objects.none()
        store_id = self.request.query_params.get('store_id')
        is_completed = self.request.query_params.get('is_completed')
        is_comp_val = None
        if is_completed is not None:
            is_comp_val = is_completed.lower() in ['true', '1']
        is_saved = self.request.query_params.get('is_saved_for_later')
        is_saved_val = None
        if is_saved is not None:
            is_saved_val = is_saved.lower() in ['true', '1']
        as_vendor = self.request.query_params.get('as_vendor', '').lower() in ['true', '1']
        if as_vendor and hasattr(user, 'role') and user.role == 'vendor':
            return CardRepository.get_by_vendor(user.id, store_id=store_id, is_completed=is_comp_val, is_saved_for_later=is_saved_val)
        return CardRepository.get_by_user(user.id, store_id=store_id, is_completed=is_comp_val, is_saved_for_later=is_saved_val)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        card = self.get_object()
        data = CardSerializer(card).data
        sort_by = request.query_params.get('sort_by')
        if sort_by == 'aisle':
            from cards.serializers.card_ser import CardItemSerializer
            sorted_items = CardService.get_card_items_sorted(card, sort_by='aisle')
            data['items'] = CardItemSerializer(sorted_items, many=True).data
        return custome_success_response(
            message="Shopping memo retrieved.",
            data=data
        )

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Retrieve or initialize the active draft memo for the customer, optionally scoped to a store."""
        store_id = request.query_params.get('store_id')
        shopping_mode = request.query_params.get('shopping_mode', 'remote')
        try:
            card = CardService.get_or_create_active_memo(
                user=request.user,
                store_id=store_id,
                shopping_mode=shopping_mode
            )
            data = CardSerializer(card).data
            sort_by = request.query_params.get('sort_by')
            if sort_by == 'aisle':
                from cards.serializers.card_ser import CardItemSerializer
                sorted_items = CardService.get_card_items_sorted(card, sort_by='aisle')
                data['items'] = CardItemSerializer(sorted_items, many=True).data
            return custome_success_response(
                message="Active draft shopping memo retrieved.",
                data=data
            )
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='add-item')
    def add_item(self, request, pk=None):
        """Add product to draft memo enforcing single-store rule and availability."""
        card = self.get_object()
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity', 1)
        if not product_id:
            return custome_error_response("product_id is required.", status_code=status.HTTP_400_BAD_REQUEST)
        try:
            item = CardService.add_product_to_card(
                card_id=card.id,
                product_id=product_id,
                quantity=quantity,
                actor=request.user
            )
            return custome_success_response(
                message="Item added to card successfully.",
                data={
                    'item_id': item.id,
                    'quantity': str(item.quantity),
                    'unit_price': str(item.unit_price),
                    'subtotal': str(item.subtotal)
                },
                status_code=status.HTTP_201_CREATED
            )
        except (ValueError, PermissionError) as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='scan-add')
    def scan_add(self, request, pk=None):
        """In-store shelf scanning: lookup by barcode or SKU and add directly to draft memo."""
        card = self.get_object()
        code = request.data.get('code') or request.data.get('barcode') or request.data.get('sku')
        quantity = request.data.get('quantity', Decimal('1'))

        if not code or not str(code).strip():
            return custome_error_response("code parameter (barcode or SKU) is required.", status_code=status.HTTP_400_BAD_REQUEST)

        try:
            item = CardService.scan_add_product(
                card_id=card.id,
                code=code,
                quantity=quantity,
                actor=request.user
            )
            return custome_success_response(
                message=f"'{item.product.name}' scanned and added to shopping memo.",
                data={
                    'item_id': item.id,
                    'product_id': item.product_id,
                    'product_name': item.product.name,
                    'quantity': str(item.quantity),
                    'unit_price': str(item.unit_price),
                    'subtotal': str(item.subtotal)
                },
                status_code=status.HTTP_201_CREATED
            )
        except PermissionError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_403_FORBIDDEN)
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='update-item')
    def update_item(self, request, pk=None):
        """Update an item quantity within the draft memo."""
        card = self.get_object()
        item_id = request.data.get('item_id')
        quantity = request.data.get('quantity')
        if not item_id or quantity is None:
            return custome_error_response("item_id and quantity are required.", status_code=status.HTTP_400_BAD_REQUEST)
        try:
            item = CardService.update_item_quantity(
                card_id=card.id,
                item_id=item_id,
                quantity=quantity,
                actor=request.user
            )
            return custome_success_response(
                message="Item quantity updated.",
                data={
                    'item_id': item.id,
                    'quantity': str(item.quantity),
                    'unit_price': str(item.unit_price),
                    'subtotal': str(item.subtotal)
                }
            )
        except (ValueError, PermissionError) as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='remove-item')
    def remove_item(self, request, pk=None):
        """Remove an item from draft memo. Resets store if memo becomes empty."""
        card = self.get_object()
        item_id = request.data.get('item_id')
        if not item_id:
            return custome_error_response("item_id is required.", status_code=status.HTTP_400_BAD_REQUEST)
        try:
            CardService.remove_item_from_card(
                card_id=card.id,
                item_id=item_id,
                actor=request.user
            )
            return custome_success_response(
                message="Item removed from shopping memo."
            )
        except (ValueError, PermissionError) as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def clear(self, request, pk=None):
        """Remove all items from draft shopping memo and reset store binding."""
        card = self.get_object()
        try:
            CardService.clear_card(card_id=card.id, actor=request.user)
            return custome_success_response(
                message="Shopping memo cleared."
            )
        except (ValueError, PermissionError) as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='apply-coupon')
    def apply_coupon(self, request, pk=None):
        """Apply promotional discount coupon to the draft shopping memo."""
        card = self.get_object()
        code = request.data.get('code')
        if not code:
            return custome_error_response("Coupon code is required.", status_code=status.HTTP_400_BAD_REQUEST)
        try:
            from stores.services.coupon_service import CouponService
            coupon, discount, estimated_total = CouponService.validate_and_apply_to_card(
                card=card,
                code=code,
                user=request.user
            )
            return custome_success_response(
                message=f"Coupon '{coupon.code}' applied successfully.",
                data={
                    'coupon_code': coupon.code,
                    'discount_type': coupon.discount_type,
                    'discount_value': f"{coupon.discount_value:.2f}",
                    'discount_amount': f"{discount:.2f}",
                    'subtotal': f"{card.total_price:.2f}",
                    'estimated_total': f"{estimated_total:.2f}"
                }
            )
        except (ValueError, PermissionError) as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='remove-coupon')
    def remove_coupon(self, request, pk=None):
        """Remove coupon from the draft shopping memo."""
        card = self.get_object()
        from stores.services.coupon_service import CouponService
        CouponService.remove_from_card(card=card, user=request.user)
        return custome_success_response(
            message="Coupon removed from shopping memo.",
            data={
                'subtotal': f"{card.total_price:.2f}",
                'discount_amount': '0.00',
                'estimated_total': f"{card.total_price:.2f}"
            }
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def checkout(self, request, pk=None):
        card = CardRepository.get_by_id(pk)
        if not card:
            return custome_error_response("Card not found.", status_code=status.HTTP_404_NOT_FOUND)

        if card.user and card.user != request.user and not request.user.is_superuser:
            return custome_error_response("You can only check out your own shopping memo.", status_code=status.HTTP_403_FORBIDDEN)

        if card.is_completed:
            return custome_error_response("This shopping memo has already been checked out.", status_code=status.HTTP_400_BAD_REQUEST)

        fulfillment_type = request.data.get('fulfillment_type', 'pickup')
        delivery_address = request.data.get('delivery_address', '')
        address_id = request.data.get('address_id')
        notes = request.data.get('notes', '')
        idempotency_key = request.data.get('idempotency_key')

        if fulfillment_type == 'delivery' and not delivery_address and not address_id:
            from users.repositories.address_repository import AddressRepository
            default_addr = AddressRepository.get_default_address(request.user)
            if default_addr:
                address_id = default_addr.id
            else:
                profile = getattr(request.user, 'profile', None)
                delivery_address = profile.address if profile and profile.address else ""
                if not delivery_address:
                    return custome_error_response("delivery_address is required for home delivery (or provide an address_id).", status_code=status.HTTP_400_BAD_REQUEST)

        from orders.serializers.order_ser import OrderSerializer

        try:
            order = CardService.checkout_card(
                card=card,
                customer=request.user,
                fulfillment_type=fulfillment_type,
                delivery_address=delivery_address,
                idempotency_key=idempotency_key,
                notes=notes,
                address_id=address_id
            )
            return custome_success_response(
                message="Order placed successfully from shopping memo.",
                data=OrderSerializer(order).data,
                status_code=status.HTTP_201_CREATED
            )

        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return custome_error_response(f"Checkout failed: {str(exc)}", status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def saved(self, request):
        """Retrieve all saved 'buy next time' planning memos for the customer."""
        store_id = request.query_params.get('store_id')
        cards = CardRepository.get_saved_cards_for_user(user_id=request.user.id, store_id=store_id)
        page = self.paginate_queryset(cards)
        if page is not None:
            serializer = CardSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = CardSerializer(cards, many=True)
        return custome_success_response(
            message="Saved planning memos retrieved.",
            data=serializer.data
        )

    @action(detail=False, methods=['post'], url_path='create-saved')
    def create_saved(self, request):
        """Create a new saved planning memo for a store."""
        store_id = request.data.get('store_id')
        title = request.data.get('title', 'My Saved Memo')
        planned_visit_date = request.data.get('planned_visit_date')
        notes = request.data.get('notes', '')
        shopping_mode = request.data.get('shopping_mode', 'walk_in')
        try:
            card = CardService.create_saved_memo(
                user=request.user,
                store_id=store_id,
                title=title,
                planned_visit_date=planned_visit_date,
                notes=notes,
                shopping_mode=shopping_mode
            )
            return custome_success_response(
                message="Saved planning memo created.",
                data=CardSerializer(card).data,
                status_code=status.HTTP_201_CREATED
            )
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='save-for-later')
    def save_for_later(self, request, pk=None):
        """Save an active memo for later planning (future store visit)."""
        card = self.get_object()
        title = request.data.get('title')
        planned_visit_date = request.data.get('planned_visit_date')
        try:
            saved_card = CardService.save_memo_for_later(
                card=card,
                actor=request.user,
                title=title,
                planned_visit_date=planned_visit_date
            )
            return custome_success_response(
                message="Shopping memo saved for future visit.",
                data=CardSerializer(saved_card).data
            )
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)
        except PermissionError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_403_FORBIDDEN)

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a saved planning memo as the current active shopping cart for that store."""
        card = self.get_object()
        strategy = request.data.get('strategy', 'swap')
        try:
            active_card = CardService.activate_saved_memo(card=card, actor=request.user, strategy=strategy)
            return custome_success_response(
                message="Planning memo activated as active shopping memo.",
                data=CardSerializer(active_card).data
            )
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)
        except PermissionError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_403_FORBIDDEN)

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Duplicate a memo and all its items into a new saved or active memo."""
        card = self.get_object()
        new_title = request.data.get('title')
        as_saved = request.data.get('as_saved', True)
        if isinstance(as_saved, str):
            as_saved = as_saved.lower() in ['true', '1']
        try:
            cloned = CardService.duplicate_memo(
                card=card,
                actor=request.user,
                new_title=new_title,
                as_saved=as_saved
            )
            return custome_success_response(
                message="Shopping memo duplicated successfully.",
                data=CardSerializer(cloned).data,
                status_code=status.HTTP_201_CREATED
            )
        except PermissionError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_403_FORBIDDEN)

    @action(detail=True, methods=['post'], url_path='toggle-item-picked')
    def toggle_item_picked(self, request, pk=None):
        """Toggle or mark in-store physical basket picking status of a memo line item."""
        card = self.get_object()
        item_id = request.data.get('item_id')
        is_picked = request.data.get('is_picked')
        if not item_id:
            return custome_error_response("item_id is required.", status_code=status.HTTP_400_BAD_REQUEST)
        try:
            item = CardService.toggle_item_picked(
                card=card,
                item_id=int(item_id),
                is_picked=is_picked,
                actor=request.user
            )
            card.refresh_from_db()
            from cards.serializers.card_ser import CardItemSerializer
            return custome_success_response(
                message=f"Item '{item.product.name}' marked as {'picked' if item.is_picked else 'unpicked'}.",
                data={
                    'item': CardItemSerializer(item).data,
                    'total_items_count': card.total_items_count,
                    'picked_items_count': card.picked_items_count,
                    'is_fully_picked': card.is_fully_picked,
                    'picking_progress_percent': card.picking_progress_percent
                }
            )
        except (ValueError, PermissionError) as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='batch-pick')
    def batch_pick(self, request, pk=None):
        """Batch update physical basket picking status for multiple items in this memo."""
        card = self.get_object()
        item_ids = request.data.get('item_ids')
        is_picked = request.data.get('is_picked', True)
        if not isinstance(item_ids, list):
            return custome_error_response("item_ids list is required.", status_code=status.HTTP_400_BAD_REQUEST)
        try:
            card = CardService.batch_pick_items(
                card=card,
                item_ids=item_ids,
                is_picked=is_picked,
                actor=request.user
            )
            return custome_success_response(
                message=f"{len(item_ids)} item(s) updated in shopping basket.",
                data=CardSerializer(card).data
            )
        except (ValueError, PermissionError) as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch', 'post'], url_path='set-budget')
    def set_budget(self, request, pk=None):
        """Set or update the spending budget ceiling for this shopping memo."""
        card = self.get_object()
        budget_limit = request.data.get('budget_limit')
        try:
            card = CardService.set_budget_limit(
                card=card,
                budget_limit=budget_limit,
                actor=request.user
            )
            return custome_success_response(
                message=f"Shopping budget limit updated to {card.budget_limit}." if card.budget_limit else "Shopping budget limit cleared.",
                data=CardSerializer(card).data
            )
        except (ValueError, PermissionError) as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='compare-store')
    def compare_store(self, request, pk=None):
        """Compare this memo's products, pricing, and stock availability against another store."""
        card = self.get_object()
        target_store_id = request.data.get('target_store_id')
        if not target_store_id:
            return custome_error_response("target_store_id is required.", status_code=status.HTTP_400_BAD_REQUEST)

        try:
            report = CardService.compare_with_store(
                card=card,
                target_store_id=int(target_store_id),
                actor=request.user
            )
            # Remove internal reference before returning
            report.pop('_internal_matched_items', None)
            return custome_success_response(
                message=f"Store comparison generated against '{report['target_store']['name']}'.",
                data=report
            )
        except (ValueError, PermissionError) as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='transfer-store')
    def transfer_store(self, request, pk=None):
        """Transfer or clone this shopping memo to another store with local catalog re-binding."""
        card = self.get_object()
        target_store_id = request.data.get('target_store_id')
        if not target_store_id:
            return custome_error_response("target_store_id is required.", status_code=status.HTTP_400_BAD_REQUEST)

        clone = request.data.get('clone', False)
        if isinstance(clone, str):
            clone = clone.lower() in ['true', '1']

        omit_missing = request.data.get('omit_missing', True)
        if isinstance(omit_missing, str):
            omit_missing = omit_missing.lower() in ['true', '1']

        try:
            result_card = CardService.transfer_to_store(
                card=card,
                target_store_id=int(target_store_id),
                actor=request.user,
                clone=clone,
                omit_missing=omit_missing
            )
            action_desc = "cloned to" if clone else "transferred to"
            return custome_success_response(
                message=f"Shopping memo {action_desc} '{result_card.store.name}' successfully.",
                data=CardSerializer(result_card).data,
                status_code=status.HTTP_201_CREATED if clone else status.HTTP_200_OK
            )
        except (ValueError, PermissionError) as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)



