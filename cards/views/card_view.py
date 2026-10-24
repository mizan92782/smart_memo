"""
cards/views/card_view.py — Views for Card App
"""
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
        as_vendor = self.request.query_params.get('as_vendor', '').lower() in ['true', '1']
        if as_vendor and hasattr(user, 'role') and user.role == 'vendor':
            return CardRepository.get_by_vendor(user.id, store_id=store_id, is_completed=is_comp_val)
        return CardRepository.get_by_user(user.id, store_id=store_id, is_completed=is_comp_val)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        card = self.get_object()
        return custome_success_response(
            message="Shopping memo retrieved.",
            data=CardSerializer(card).data
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
            return custome_success_response(
                message="Active draft shopping memo retrieved.",
                data=CardSerializer(card).data
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

