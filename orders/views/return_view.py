from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from orders.models.order_mod import Order
from orders.models.return_mod import OrderReturn
from orders.serializers.return_ser import (
    OrderReturnSerializer,
    OrderReturnRequestSerializer,
    OrderReturnProcessSerializer
)
from orders.services.order_return_service import OrderReturnService
from shared.responses.responses import custome_success_response, custome_error_response


class OrderReturnViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for managing customer return requests, vendor review/approval,
    inventory restocking, and thermal credit notes.
    """
    serializer_class = OrderReturnSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return OrderReturn.objects.none()

        base_qs = (
            OrderReturn.objects
            .filter(is_deleted=False)
            .select_related('order', 'store', 'customer', 'vendor', 'processed_by')
            .prefetch_related('items__product', 'items__order_item')
        )

        # Staff can inspect platform-wide returns
        if getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False):
            store_id = self.request.query_params.get('store_id')
            if store_id:
                base_qs = base_qs.filter(store_id=store_id)
            return base_qs

        # Vendor view: scoped to stores owned by vendor, plus any returns where vendor is customer
        if hasattr(user, 'role') and user.role == 'vendor':
            vendor_stores = user.stores.values_list('id', flat=True)
            store_id = self.request.query_params.get('store_id')
            if store_id:
                if int(store_id) not in vendor_stores:
                    return OrderReturn.objects.none()
                return base_qs.filter(store_id=store_id)
            from django.db.models import Q
            return base_qs.filter(Q(store_id__in=vendor_stores) | Q(customer=user))

        # Customer view: only their own returns
        return base_qs.filter(customer=user)


    @action(detail=False, methods=['post'], url_path='request')
    def request_return(self, request):
        """Customer submits an item return request for a completed order."""
        serializer = OrderReturnRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order_id = serializer.validated_data['order_id']
        order = Order.objects.filter(pk=order_id, is_deleted=False).first()
        if not order:
            return custome_error_response("Order not found.", status_code=status.HTTP_404_NOT_FOUND)

        if order.customer_id != request.user.id and not request.user.is_superuser:
            return custome_error_response("You do not own this order.", status_code=status.HTTP_403_FORBIDDEN)

        try:
            order_return = OrderReturnService.request_return(
                order=order,
                customer=request.user,
                items_data=serializer.validated_data['items'],
                reason=serializer.validated_data.get('reason'),
                reason_notes=serializer.validated_data.get('reason_notes', '')
            )
            data = OrderReturnSerializer(order_return).data
            return custome_success_response(
                data=data,
                message=f"Return request {order_return.return_number} submitted successfully.",
                status_code=status.HTTP_201_CREATED
            )
        except (ValueError, PermissionError) as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='process')
    def process_return(self, request, pk=None):
        """Store vendor approves or rejects a return request, managing stock restock & refunds."""
        order_return = OrderReturn.objects.filter(pk=pk, is_deleted=False).select_related('store', 'order', 'customer').first()
        if not order_return:
            return custome_error_response("Return request not found.", status_code=status.HTTP_404_NOT_FOUND)

        serializer = OrderReturnProcessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            processed = OrderReturnService.process_return(
                order_return=order_return,
                actor=request.user,
                decision=serializer.validated_data['decision'],
                restock_inventory=serializer.validated_data.get('restock_inventory', True),
                rejection_reason=serializer.validated_data.get('rejection_reason', '')
            )
            data = OrderReturnSerializer(processed).data
            return custome_success_response(
                data=data,
                message=f"Return request {processed.return_number} has been {processed.status}."
            )
        except PermissionError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_403_FORBIDDEN)
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], url_path='credit-note')
    def credit_note(self, request, pk=None):
        """Retrieve 40-column monospace printable thermal credit note / return receipt."""
        order_return = self.get_object()
        raw_slip = order_return.format_credit_note_thermal()

        fmt = (request.query_params.get('receipt_format') or request.query_params.get('format_type') or '').lower()
        if fmt in ['text', 'thermal'] or 'text/plain' in request.headers.get('Accept', ''):
            return HttpResponse(raw_slip, content_type='text/plain; charset=utf-8')

        return custome_success_response(
            message="Credit note generated successfully.",
            data={
                "return_number": order_return.return_number,
                "order_number": order_return.order.order_number,
                "store_name": order_return.store.name,
                "total_refund_amount": str(order_return.total_refund_amount),
                "status": order_return.status,
                "credit_note_slip": raw_slip
            }
        )

