from django.db.models import Prefetch
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from orders.models.order_mod import Order, SalesMemo
from orders.serializers.order_ser import OrderSerializer, OrderSubmitSerializer, SalesMemoSerializer
from orders.services.order_service import OrderService
from cards.models.card_mod import Card
from shared.responses.responses import custome_success_response, custome_error_response


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for customer order submission, lifecycle tracking, and vendor fulfillment.
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return Order.objects.none()
        memo_prefetch = Prefetch(
            'sales_memo',
            queryset=SalesMemo.objects.select_related('customer', 'vendor', 'order')
        )
        if hasattr(user, 'role') and user.role == 'vendor':
            return (
                Order.objects
                .filter(vendor=user, is_deleted=False)
                .select_related('customer', 'vendor', 'store')
                .prefetch_related('items', memo_prefetch)
            )
        return (
            Order.objects
            .filter(customer=user, is_deleted=False)
            .select_related('customer', 'vendor', 'store')
            .prefetch_related('items', memo_prefetch)
        )

    @action(detail=False, methods=['post'])
    def submit(self, request):
        """Submit a draft memo (Card) into an order with atomic stock reservations."""
        serializer = OrderSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        card_id = serializer.validated_data['card_id']
        card = Card.objects.filter(pk=card_id, is_completed=False).first()
        if not card:
            return custome_error_response("Shopping memo not found or already completed.", status_code=status.HTTP_404_NOT_FOUND)

        if card.user != request.user and not request.user.is_superuser:
            return custome_error_response("You do not own this shopping memo.", status_code=status.HTTP_403_FORBIDDEN)

        try:
            order = OrderService.submit_order_from_card(
                card=card,
                customer=request.user,
                fulfillment_type=serializer.validated_data['fulfillment_type'],
                delivery_address=serializer.validated_data.get('delivery_address', ''),
                idempotency_key=serializer.validated_data.get('idempotency_key'),
                notes=serializer.validated_data.get('notes', '')
            )
            return custome_success_response(
                message="Order placed successfully. Inventory has been reserved.",
                data=OrderSerializer(order).data,
                status_code=status.HTTP_201_CREATED
            )
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Vendor accepts the submitted order."""
        order = self.get_object()
        if order.store.vendor != request.user and not request.user.is_superuser:
            return custome_error_response("You do not own the store for this order.", status_code=status.HTTP_403_FORBIDDEN)

        try:
            order = OrderService.accept_order(order=order, actor=request.user)
            return custome_success_response(
                message="Order accepted.",
                data=OrderSerializer(order).data
            )
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def prepare(self, request, pk=None):
        """Vendor moves order into preparation."""
        order = self.get_object()
        if order.store.vendor != request.user and not request.user.is_superuser:
            return custome_error_response("You do not own the store for this order.", status_code=status.HTTP_403_FORBIDDEN)

        try:
            order = OrderService.start_preparing(order=order, actor=request.user)
            return custome_success_response(
                message="Order is now in preparation.",
                data=OrderSerializer(order).data
            )
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='dispatch')
    def dispatch_order(self, request, pk=None):
        """Vendor marks order as ready for pickup or dispatched for delivery."""
        order = self.get_object()
        if order.store.vendor != request.user and not request.user.is_superuser:
            return custome_error_response("You do not own the store for this order.", status_code=status.HTTP_403_FORBIDDEN)

        try:
            order = OrderService.dispatch_order(order=order, actor=request.user)
            msg = "Order ready for customer pickup." if order.status == 'ready_for_pickup' else "Order dispatched for home delivery."
            return custome_success_response(
                message=msg,
                data=OrderSerializer(order).data
            )
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='assign-delivery')
    def assign_delivery(self, request, pk=None):
        """Vendor assigns a delivery driver to a home delivery order."""
        order = self.get_object()
        from orders.serializers.order_ser import DeliveryAssignmentSerializer
        serializer = DeliveryAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            order = OrderService.assign_delivery_driver(
                order=order,
                actor=request.user,
                driver_name=serializer.validated_data['driver_name'],
                driver_phone=serializer.validated_data['driver_phone'],
                vehicle_type=serializer.validated_data.get('vehicle_type', ''),
                tracking_notes=serializer.validated_data.get('tracking_notes', ''),
                estimated_delivery_time=serializer.validated_data.get('estimated_delivery_time'),
                auto_dispatch=serializer.validated_data.get('auto_dispatch', False)
            )
            return custome_success_response(
                message=f"Delivery driver '{order.delivery_person_name}' assigned to order #{order.order_number}.",
                data=OrderSerializer(order).data
            )
        except PermissionError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_403_FORBIDDEN)
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def fulfill(self, request, pk=None):
        """Vendor marks order as fulfilled/completed and collects payment."""
        order = self.get_object()
        if order.store.vendor != request.user and not request.user.is_superuser:
            return custome_error_response("You do not own the store for this order.", status_code=status.HTTP_403_FORBIDDEN)

        payment_collected = request.data.get('payment_collected', True)
        try:
            order = OrderService.fulfill_order(
                order=order,
                actor=request.user,
                payment_collected=payment_collected
            )
            return custome_success_response(
                message="Order fulfilled and sales memo issued.",
                data=OrderSerializer(order).data
            )
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='handover')
    def handover(self, request, pk=None):
        """Vendor hands over collected products to the customer in-store and collects payment."""
        order = self.get_object()
        if order.store.vendor != request.user and not request.user.is_superuser:
            return custome_error_response("You do not own the store for this order.", status_code=status.HTTP_403_FORBIDDEN)

        payment_collected = request.data.get('payment_collected', True)
        try:
            order = OrderService.handover_order(
                order=order,
                actor=request.user,
                payment_collected=payment_collected
            )
            return custome_success_response(
                message="Order handed over to customer successfully and sales memo issued.",
                data=OrderSerializer(order).data
            )
        except PermissionError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_403_FORBIDDEN)
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel order and release reserved stock."""
        order = self.get_object()
        is_owner = (order.customer == request.user)
        is_store_vendor = (order.store.vendor == request.user)

        if not (is_owner or is_store_vendor or request.user.is_superuser):
            return custome_error_response("You cannot cancel this order.", status_code=status.HTTP_403_FORBIDDEN)

        reason = request.data.get('reason', 'Cancelled by user')
        try:
            order = OrderService.cancel_order(order=order, actor=request.user, reason=reason)
            return custome_success_response(
                message="Order cancelled and reserved stock restored.",
                data=OrderSerializer(order).data
            )
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def sales_memo(self, request, pk=None):
        """Retrieve the immutable sales receipt for completed order."""
        order = self.get_object()
        if not hasattr(order, 'sales_memo'):
            return custome_error_response("Sales memo not generated yet.", status_code=status.HTTP_404_NOT_FOUND)
        fmt = (request.query_params.get('receipt_format') or request.query_params.get('format_type') or '').lower()
        if fmt in ['text', 'thermal']:
            from django.http import HttpResponse
            return HttpResponse(order.sales_memo.format_thermal_receipt(), content_type='text/plain; charset=utf-8')
        return custome_success_response(
            message="Sales memo retrieved.",
            data=SalesMemoSerializer(order.sales_memo).data
        )

    @action(detail=True, methods=['get'], url_path='thermal-receipt')
    def thermal_receipt(self, request, pk=None):
        """Retrieve plain text thermal receipt slip for printing."""
        order = self.get_object()
        if not hasattr(order, 'sales_memo'):
            return custome_error_response("Sales memo not generated yet.", status_code=status.HTTP_404_NOT_FOUND)
        from django.http import HttpResponse
        return HttpResponse(order.sales_memo.format_thermal_receipt(), content_type='text/plain; charset=utf-8')

    @action(detail=True, methods=['post'], url_path='collect-payment')
    def collect_payment(self, request, pk=None):
        """Record payment collection for this order."""
        order = self.get_object()
        if order.store.vendor != request.user and not request.user.is_superuser:
            return custome_error_response("You do not own the store for this order.", status_code=status.HTTP_403_FORBIDDEN)

        try:
            order = OrderService.collect_payment(order=order, collector=request.user)
            return custome_success_response(
                message="Payment marked as collected.",
                data=OrderSerializer(order).data
            )
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='counter-lookup')
    def counter_lookup(self, request):
        """Look up a customer order at the physical store counter via 6-digit walk-in code."""
        code = request.data.get('code') or request.data.get('walk_in_code')
        store_id = request.data.get('store_id')
        try:
            order = OrderService.counter_lookup(code=code, actor=request.user, store_id=store_id)
            return custome_success_response(
                message="Counter walk-in order retrieved.",
                data=OrderSerializer(order).data
            )
        except Order.DoesNotExist:
            return custome_error_response("No order found with the provided counter walk-in code.", status_code=status.HTTP_404_NOT_FOUND)
        except PermissionError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_403_FORBIDDEN)
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='sales-memos')
    def list_sales_memos(self, request):
        """
        Digital Sales Memo History / Receipt Wallet.
        Enables customers to view all completed digital sales memos across all stores.
        Enables vendors to query sales memos for their store(s) with ?as_vendor=true.
        """
        as_vendor = request.query_params.get('as_vendor', '').lower() in ['true', '1']
        filters = {
            'store_id': request.query_params.get('store_id'),
            'from_date': request.query_params.get('from_date'),
            'to_date': request.query_params.get('to_date'),
            'search': request.query_params.get('search')
        }
        qs = OrderService.list_sales_memos(actor=request.user, filters=filters, as_vendor=as_vendor)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = SalesMemoSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = SalesMemoSerializer(qs, many=True)
        return custome_success_response("Sales memos retrieved.", data=serializer.data)

    @action(detail=False, methods=['get'], url_path='customer-spending')
    def customer_spending(self, request):
        """
        Customer spending analytics and multi-store visit breakdown.
        """
        stats = OrderService.get_customer_spending_summary(request.user)
        return custome_success_response(
            message="Customer multi-store spending analytics retrieved.",
            data=stats
        )

    @action(detail=True, methods=['get'], url_path='qr-code')
    def qr_code(self, request, pk=None):
        """Retrieve vector SVG QR code for in-store walk-in verification and counter POS scanning."""
        order = self.get_object()
        from django.http import HttpResponse
        svg = order.generate_qr_code_svg()
        return HttpResponse(svg, content_type='image/svg+xml')

    @action(detail=True, methods=['post'], url_path='reorder')
    def reorder(self, request, pk=None):
        """One-tap reorder: clones items from a past order into an active draft shopping memo."""
        order = self.get_object()
        if order.customer != request.user and not request.user.is_superuser:
            return custome_error_response("You can only reorder your own past orders.", status_code=status.HTTP_403_FORBIDDEN)

        try:
            from cards.serializers.card_ser import CardSerializer
            card = OrderService.reorder_to_card(order=order, customer=request.user)
            return custome_success_response(
                message=f"Shopping memo for '{order.store.name}' populated from order {order.order_number}.",
                data=CardSerializer(card).data,
                status_code=status.HTTP_201_CREATED
            )
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

