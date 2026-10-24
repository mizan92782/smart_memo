from rest_framework import viewsets, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from categories.models.category_mod import Category
from categories.serializers.category_ser import CategorySerializer
from categories.repositories.category_repository import CategoryRepository
from stores.models.store_mod import Store
from shared.permissions.permissions import IsStoreOwner, IsVendor
from shared.responses.responses import custome_success_response, custome_error_response
from shared.caching.cache_service import CacheService


class CategoryViewSet(viewsets.ModelViewSet):
    """API endpoint to list, retrieve, and manage categories."""
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated(), IsVendor()]

    def get_queryset(self):
        store_id = self.request.query_params.get('store_id')
        if store_id:
            return CategoryRepository.get_by_store(int(store_id))
        if self.request.user.is_authenticated and hasattr(self.request.user, 'role') and self.request.user.role == 'vendor':
            # Default to categories belonging to vendor's stores
            vendor_stores = self.request.user.stores.values_list('id', flat=True)
            return Category.objects.filter(store_id__in=vendor_stores, is_deleted=False).order_by('name')
        return CategoryRepository.get_all()

    def list(self, request, *args, **kwargs):
        store_id = request.query_params.get('store_id')
        if store_id:
            cache_key = CacheService.build_cache_key(store_id=store_id, namespace="catalog", identifier="category_list")
            cached = CacheService.get(cache_key)
            if cached is not None:
                return custome_success_response(
                    message="Categories retrieved successfully.",
                    data=cached,
                    data_title="categories"
                )
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            CacheService.set(cache_key, serializer.data, timeout=CacheService.DEFAULT_TTL)
            return custome_success_response(
                message="Categories retrieved successfully.",
                data=serializer.data,
                data_title="categories"
            )
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        name = request.data.get('name')
        store_id = request.data.get('store_id')
        if not name:
            return custome_error_response("Name is required.")

        store = None
        if store_id:
            store = Store.objects.filter(pk=store_id, is_deleted=False).first()
            if not store:
                return custome_error_response("Store not found.", status_code=status.HTTP_404_NOT_FOUND)
            if store.vendor != request.user and not request.user.is_superuser:
                return custome_error_response("You do not own this store.", status_code=status.HTTP_403_FORBIDDEN)
        else:
            # Fallback to vendor's first store if exists
            store = request.user.stores.filter(is_deleted=False).first()

        category = CategoryRepository.create_category(name=name, store=store)
        if store:
            CacheService.invalidate_catalog(store.id)
        return custome_success_response(
            message="Category created successfully.",
            data=CategorySerializer(category).data,
            data_title="category",
            status_code=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        category = self.get_object()
        if category.store and category.store.vendor != request.user and not request.user.is_superuser:
            return custome_error_response("You do not own this store.", status_code=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(category, data=request.data, partial=kwargs.get('partial', False))
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        if updated.store_id:
            CacheService.invalidate_catalog(updated.store_id)
        return custome_success_response(
            message="Category updated successfully.",
            data=serializer.data,
            data_title="category"
        )

    def destroy(self, request, *args, **kwargs):
        category = self.get_object()
        if category.store and category.store.vendor != request.user and not request.user.is_superuser:
            return custome_error_response("You do not own this store.", status_code=status.HTTP_403_FORBIDDEN)
        store_id = category.store_id
        CategoryRepository.delete_category(category)
        if store_id:
            CacheService.invalidate_catalog(store_id)
        return custome_success_response(
            message="Category deleted successfully.",
            status_code=status.HTTP_204_NO_CONTENT
        )

