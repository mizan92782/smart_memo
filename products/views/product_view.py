from django.views.generic import ListView
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from products.models.product_mod import Product
from categories.models.category_mod import Category
from stores.models.store_mod import Store
from products.repositories.product_repository import ProductRepository
from products.serializers.product_ser import ProductSerializer
from shared.permissions.permissions import IsStoreOwner, IsVendor
from shared.responses.responses import custome_success_response, custome_error_response
from shared.caching.cache_service import CacheService


class ProductList(ListView):
    """Template view to list all products."""
    model = Product
    context_object_name = 'products'
    template_name = 'products.html'
    ordering = ['name']

    def get_queryset(self):
        return ProductRepository.get_all()


class Category_Products_ListView(ListView):
    """Template view to list products within a specific category."""
    model = Category
    template_name = 'category_products.html'
    context_object_name = 'products'

    def get_queryset(self):
        return ProductRepository.get_by_category_id(self.kwargs['pk'])


class ProductViewSet(viewsets.ModelViewSet):
    """
    REST API ViewSet for Products.
    - Public catalog search & discovery.
    - Vendor product management scoped to owned stores.
    """
    serializer_class = ProductSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'catalog']:
            return [AllowAny()]
        return [IsAuthenticated(), IsVendor()]

    def get_queryset(self):
        if self.request.user.is_authenticated and hasattr(self.request.user, 'role') and self.request.user.role == 'vendor':
            vendor_stores = self.request.user.stores.values_list('id', flat=True)
            return Product.objects.filter(store_id__in=vendor_stores, is_deleted=False).select_related('category', 'store')
        return Product.objects.filter(is_deleted=False, is_active=True).select_related('category', 'store')

    def create(self, request, *args, **kwargs):
        store_id = request.data.get('store') or request.data.get('store_id')
        if not store_id:
            store = request.user.stores.filter(is_deleted=False).first()
            if not store:
                return custome_error_response("Store is required.", status_code=status.HTTP_400_BAD_REQUEST)
            store_id = store.id

        store = Store.objects.filter(pk=store_id, is_deleted=False).first()
        if not store:
            return custome_error_response("Store not found.", status_code=status.HTTP_404_NOT_FOUND)
        if store.vendor != request.user and not request.user.is_superuser:
            return custome_error_response("You do not own this store.", status_code=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save(store=store)
        if product.store_id:
            CacheService.invalidate_catalog(product.store_id)
        return custome_success_response(
            message="Product created successfully.",
            data=ProductSerializer(product).data,
            data_title="product",
            status_code=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        product = self.get_object()
        if product.store and product.store.vendor != request.user and not request.user.is_superuser:
            return custome_error_response("You do not own this store.", status_code=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(product, data=request.data, partial=kwargs.get('partial', False))
        serializer.is_valid(raise_exception=True)
        updated_product = serializer.save()
        if updated_product.store_id:
            CacheService.invalidate_catalog(updated_product.store_id)
        return custome_success_response(
            message="Product updated successfully.",
            data=ProductSerializer(updated_product).data,
            data_title="product"
        )

    def destroy(self, request, *args, **kwargs):
        product = self.get_object()
        if product.store and product.store.vendor != request.user and not request.user.is_superuser:
            return custome_error_response("You do not own this store.", status_code=status.HTTP_403_FORBIDDEN)

        store_id = product.store_id
        ProductRepository.delete_product(product)
        if store_id:
            CacheService.invalidate_catalog(store_id)
        return custome_success_response(
            message="Product deleted successfully.",
            status_code=status.HTTP_204_NO_CONTENT
        )

    @action(detail=False, methods=['get'])
    def catalog(self, request):
        """Public product catalog search and filtering with tenant-safe caching."""
        query = request.query_params.get('search')
        store_id = request.query_params.get('store_id')
        category_id = request.query_params.get('category_id')
        page_num = request.query_params.get('page', 1)

        cache_key = None
        if store_id:
            cache_key = CacheService.build_cache_key(
                store_id=store_id,
                namespace="catalog",
                identifier="search",
                params={'query': query or '', 'category_id': category_id or '', 'page': page_num}
            )
            cached_payload = CacheService.get(cache_key)
            if cached_payload is not None:
                if isinstance(cached_payload, dict) and 'results' in cached_payload:
                    return Response(cached_payload)
                return custome_success_response(
                    message="Products retrieved successfully.",
                    data=cached_payload
                )

        products = ProductRepository.search_catalog(
            query=query,
            store_id=int(store_id) if store_id else None,
            category_id=int(category_id) if category_id else None
        )
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            res = self.get_paginated_response(serializer.data)
            if cache_key:
                CacheService.set(cache_key, res.data, timeout=CacheService.DEFAULT_TTL)
            return res

        serializer = self.get_serializer(products, many=True)
        if cache_key:
            CacheService.set(cache_key, serializer.data, timeout=CacheService.DEFAULT_TTL)
        return custome_success_response(
            message="Products retrieved successfully.",
            data=serializer.data
        )
