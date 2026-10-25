"""
cards/views/template_view.py — ViewSet for Store Routine Shopping Templates & One-Tap Memo Hydration.
"""
from decimal import Decimal
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError as DjangoValidationError, PermissionDenied
from rest_framework.exceptions import ValidationError as DRFValidationError

from cards.models.template_mod import StoreMemoTemplate
from cards.repositories.template_repository import TemplateRepository
from cards.serializers.template_ser import (
    StoreMemoTemplateSerializer,
    StoreMemoTemplateItemSerializer,
    TemplateItemInputSerializer,
    LoadTemplateToMemoSerializer
)
from cards.serializers.card_ser import CardSerializer
from cards.services.template_service import TemplateService
from shared.responses.responses import custome_success_response, custome_error_response


class StoreMemoTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Store-Scoped Shopping Routine Templates.
    Allows customers to save and manage routine baskets (e.g. Weekly Groceries, Monthly Household Refill)
    and hydrate active draft memos in one tap with real-time stock and price evaluation.
    """
    serializer_class = StoreMemoTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return StoreMemoTemplate.objects.none()

        store_id = self.request.query_params.get('store_id')
        is_fav = self.request.query_params.get('is_favorite')
        is_fav_val = None
        if is_fav is not None:
            is_fav_val = is_fav.lower() in ['true', '1']

        as_vendor = self.request.query_params.get('as_vendor', '').lower() in ['true', '1']
        if as_vendor and hasattr(user, 'role') and user.role == 'vendor':
            return TemplateRepository.get_by_vendor(user.id, store_id=store_id)

        return TemplateRepository.get_by_user(user.id, store_id=store_id, is_favorite=is_fav_val)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return custome_success_response(
            message="Routine shopping templates retrieved.",
            data=serializer.data
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return custome_success_response(
            message="Routine template retrieved.",
            data=serializer.data
        )

    def create(self, request, *args, **kwargs):
        store_id = request.data.get('store_id') or request.data.get('store')
        if not store_id:
            return custome_error_response("store_id is required to create a store routine template.", status_code=status.HTTP_400_BAD_REQUEST)

        name = request.data.get('name', '')
        description = request.data.get('description', '')
        shopping_mode = request.data.get('shopping_mode', 'remote')
        is_favorite = request.data.get('is_favorite', False)
        if isinstance(is_favorite, str):
            is_favorite = is_favorite.lower() in ['true', '1']

        try:
            template = TemplateService.create_template(
                user=request.user,
                store_id=int(store_id),
                name=name,
                description=description,
                shopping_mode=shopping_mode,
                is_favorite=is_favorite
            )
            return custome_success_response(
                message=f"Routine template '{template.name}' created.",
                data=StoreMemoTemplateSerializer(template).data,
                status_code=status.HTTP_201_CREATED
            )
        except (DjangoValidationError, DRFValidationError, ValueError) as exc:
            msg = exc.messages[0] if hasattr(exc, 'messages') else str(exc)
            return custome_error_response(msg, status_code=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        template = self.get_object()
        data = request.data
        allowed_fields = ['name', 'description', 'shopping_mode', 'is_favorite']
        update_fields = {}
        for f in allowed_fields:
            if f in data:
                val = data[f]
                if f == 'is_favorite' and isinstance(val, str):
                    val = val.lower() in ['true', '1']
                update_fields[f] = val

        try:
            updated = TemplateService.update_template(template, request.user, **update_fields)
            return custome_success_response(
                message="Routine template updated.",
                data=StoreMemoTemplateSerializer(updated).data
            )
        except (DjangoValidationError, PermissionDenied, ValueError) as exc:
            msg = exc.messages[0] if hasattr(exc, 'messages') else str(exc)
            return custome_error_response(msg, status_code=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        template = self.get_object()
        try:
            TemplateService.delete_template(template, request.user)
            return custome_success_response(
                message="Routine template deleted successfully.",
                data=None,
                status_code=status.HTTP_200_OK
            )
        except (PermissionDenied, DjangoValidationError) as exc:
            msg = exc.messages[0] if hasattr(exc, 'messages') else str(exc)
            return custome_error_response(msg, status_code=status.HTTP_403_FORBIDDEN)

    @action(detail=True, methods=['post'], url_path='add-item')
    def add_item(self, request, pk=None):
        """Add or update a line item in this routine template."""
        template = self.get_object()
        ser = TemplateItemInputSerializer(data=request.data)
        if not ser.is_valid():
            return custome_error_response("Invalid input", errors=ser.errors, status_code=status.HTTP_400_BAD_REQUEST)

        try:
            TemplateService.add_item_to_template(
                template=template,
                user=request.user,
                product_id=ser.validated_data['product_id'],
                quantity=Decimal(str(ser.validated_data.get('quantity', 1))),
                notes=ser.validated_data.get('notes', '')
            )
            template.refresh_from_db()
            return custome_success_response(
                message="Item added to routine template.",
                data=StoreMemoTemplateSerializer(template).data,
                status_code=status.HTTP_200_OK
            )
        except (DjangoValidationError, PermissionDenied, ValueError) as exc:
            msg = exc.messages[0] if hasattr(exc, 'messages') else str(exc)
            return custome_error_response(msg, status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='items')
    def items_endpoint(self, request, pk=None):
        return self.add_item(request, pk=pk)

    @action(detail=True, methods=['post'], url_path='remove-item')
    def remove_item(self, request, pk=None):
        """Remove a line item from this routine template by item_id."""
        template = self.get_object()
        item_id = request.data.get('item_id')
        if not item_id:
            return custome_error_response("item_id is required in request body.", status_code=status.HTTP_400_BAD_REQUEST)

        try:
            TemplateService.remove_item_from_template(template, request.user, int(item_id))
            template.refresh_from_db()
            return custome_success_response(
                message="Item removed from routine template.",
                data=StoreMemoTemplateSerializer(template).data
            )
        except (DjangoValidationError, PermissionDenied, ValueError) as exc:
            msg = exc.messages[0] if hasattr(exc, 'messages') else str(exc)
            return custome_error_response(msg, status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete', 'post'], url_path=r'items/(?P<item_id>[^/.]+)')
    def item_by_id(self, request, pk=None, item_id=None):
        """Remove item using RESTful /templates/{id}/items/{item_id}/ endpoint."""
        template = self.get_object()
        try:
            TemplateService.remove_item_from_template(template, request.user, int(item_id))
            template.refresh_from_db()
            return custome_success_response(
                message="Item removed from routine template.",
                data=StoreMemoTemplateSerializer(template).data
            )
        except (DjangoValidationError, PermissionDenied, ValueError) as exc:
            msg = exc.messages[0] if hasattr(exc, 'messages') else str(exc)
            return custome_error_response(msg, status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='load-to-memo')
    def load_to_memo(self, request, pk=None):
        """
        One-Tap Memo Hydration:
        Loads this routine template into the user's active draft memo for the store.
        Re-validates real-time catalog pricing and available stock.
        """
        template = self.get_object()
        ser = LoadTemplateToMemoSerializer(data=request.data)
        if not ser.is_valid():
            return custome_error_response("Invalid input", errors=ser.errors, status_code=status.HTTP_400_BAD_REQUEST)

        mode = ser.validated_data.get('mode', 'replace')
        shopping_mode = ser.validated_data.get('shopping_mode')

        try:
            result = TemplateService.load_template_to_memo(
                template=template,
                user=request.user,
                mode=mode,
                shopping_mode=shopping_mode
            )
            card = result['card']
            return custome_success_response(
                message=f"Routine template loaded into active memo ({result['loaded_items_count']} loaded, {result['omitted_items_count']} omitted).",
                data={
                    'card': CardSerializer(card).data,
                    'loaded_items_count': result['loaded_items_count'],
                    'omitted_items_count': result['omitted_items_count'],
                    'loaded_items': result['loaded_items'],
                    'omitted_items': result['omitted_items']
                }
            )
        except (DjangoValidationError, PermissionDenied, ValueError) as exc:
            msg = exc.messages[0] if hasattr(exc, 'messages') else str(exc)
            return custome_error_response(msg, status_code=status.HTTP_400_BAD_REQUEST)
