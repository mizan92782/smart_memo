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
    """ViewSet for Card (Memo/Cart) CRUD and item operations."""
    serializer_class = CardSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return CardRepository.get_by_user(self.request.user.id)
        return Card.objects.all()

    @action(detail=True, methods=['post'])
    def add_item(self, request, pk=None):
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity', 1)
        if not product_id:
            return custome_error_response("product_id is required.")
        try:
            item = CardService.add_product_to_card(card_id=pk, product_id=product_id, quantity=quantity)
            return custome_success_response(
                message="Item added to card successfully.",
                data={'item_id': item.id, 'quantity': item.quantity},
                status_code=status.HTTP_201_CREATED
            )
        except Exception as exc:
            return custome_error_response(str(exc))

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
        notes = request.data.get('notes', '')
        idempotency_key = request.data.get('idempotency_key')

        if fulfillment_type == 'delivery' and not delivery_address:
            profile = getattr(request.user, 'profile', None)
            delivery_address = profile.address if profile and profile.address else ""
            if not delivery_address:
                return custome_error_response("delivery_address is required for home delivery.", status_code=status.HTTP_400_BAD_REQUEST)

        from orders.serializers.order_ser import OrderSerializer

        try:
            order = CardService.checkout_card(
                card=card,
                customer=request.user,
                fulfillment_type=fulfillment_type,
                delivery_address=delivery_address,
                idempotency_key=idempotency_key,
                notes=notes
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

