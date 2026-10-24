from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from stores.models.store_mod import Store
from stores.serializers.store_ser import StoreSerializer, PublicStoreSerializer, FavoriteStoreSerializer
from stores.repositories.store_repository import StoreRepository
from stores.services.store_service import StoreService
from stores.services.favorite_service import FavoriteService
from shared.permissions.permissions import IsStoreOwner, IsVendor, IsCustomer, IsStaffOrAdmin
from shared.enums.enums import UserRoleEnum
from shared.responses.responses import custome_success_response, custome_error_response
from shared.pagination.pagination import StandardResultsPagination
from shared.caching.cache_service import CacheService
from shared.throtling import NearbyDiscoveryThrottle



class StoreViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Store management, public discovery, geospatial nearby search, customer favorites,
    and platform administration governance.
    - Vendor endpoints: Scoped strictly to request.user.
    - Public discovery: Lists only active and verified stores.
    - Geospatial search: /stores/nearby/?lat=...&lng=...&radius_km=...
    - Favorites: Scoped strictly to authenticated customer.
    - Governance: Scoped strictly to platform staff and superusers.
    """
    serializer_class = StoreSerializer
    pagination_class = StandardResultsPagination

    def get_permissions(self):
        if self.action in ['public', 'public_detail', 'nearby']:
            return [AllowAny()]
        if self.action in ['favorite', 'unfavorite', 'favorites']:
            return [IsAuthenticated(), IsCustomer()]
        if self.action in ['verify', 'suspend', 'activate', 'governance_overview']:
            return [IsAuthenticated(), IsStaffOrAdmin()]
        if self.action == 'create':
            return [IsAuthenticated(), IsVendor()]
        return [IsAuthenticated(), IsStoreOwner()]

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Store.objects.none()
        if (
            self.request.user.is_superuser
            or self.request.user.is_staff
            or getattr(self.request.user, 'role', None) in (UserRoleEnum.STAFF, UserRoleEnum.SUPERUSER)
        ):
            return StoreRepository.get_all_stores()
        return StoreRepository.get_by_vendor(self.request.user.id)


    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        store = StoreService.register_store(vendor=request.user, **serializer.validated_data)
        return custome_success_response(
            message="Store created successfully.",
            data=StoreSerializer(store).data,
            data_title="store",
            status_code=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        store = self.get_object()
        serializer = self.get_serializer(store, data=request.data, partial=kwargs.get('partial', False))
        serializer.is_valid(raise_exception=True)
        updated_store = StoreService.update_store_profile(store, **serializer.validated_data)
        CacheService.invalidate_store_profile(store.id)
        CacheService.invalidate_catalog(store.id)
        return custome_success_response(
            message="Store updated successfully.",
            data=StoreSerializer(updated_store).data,
            data_title="store"
        )

    def destroy(self, request, *args, **kwargs):
        store = self.get_object()
        CacheService.invalidate_store_profile(store.id)
        CacheService.invalidate_catalog(store.id)
        StoreRepository.delete_store(store)
        return custome_success_response(
            message="Store deleted successfully.",
            status_code=status.HTTP_204_NO_CONTENT
        )

    @action(detail=False, methods=['get'])
    def public(self, request):
        """Public endpoint to discover active stores."""
        stores = StoreRepository.get_public_active_stores()
        serializer = PublicStoreSerializer(stores, many=True, context={'request': request})
        return custome_success_response(
            message="Active stores retrieved successfully.",
            data=serializer.data
        )

    @action(detail=True, methods=['get'], url_path='public-detail')
    def public_detail(self, request, pk=None):
        """Public endpoint to retrieve single active store with tenant-safe caching."""
        cache_key = CacheService.build_cache_key(store_id=pk, namespace="store", identifier="public_detail")
        cached_data = CacheService.get(cache_key)
        if cached_data is not None:
            return custome_success_response(
                message="Store detail retrieved successfully.",
                data=cached_data,
                data_title="store"
            )

        store = StoreRepository.get_id(pk) if hasattr(StoreRepository, 'get_id') else StoreRepository.get_by_id(pk)
        if not store or not store.is_active:
            return custome_error_response("Store not found or inactive.", status_code=status.HTTP_404_NOT_FOUND)
        serializer = PublicStoreSerializer(store, context={'request': request})
        CacheService.set(cache_key, serializer.data, timeout=CacheService.DEFAULT_TTL)
        return custome_success_response(
            message="Store detail retrieved successfully.",
            data=serializer.data,
            data_title="store"
        )

    @action(detail=False, methods=['get'], throttle_classes=[NearbyDiscoveryThrottle])
    def nearby(self, request):
        """
        Geospatial discovery endpoint.
        Query params:
            lat: Latitude (-90.0 to 90.0)
            lng: Longitude (-180.0 to 180.0)
            radius_km: Radius in kilometers (0.1 to 100.0, default 10.0)
        """
        lat_param = request.query_params.get('lat')
        lng_param = request.query_params.get('lng')
        radius_param = request.query_params.get('radius_km', '10.0')

        lat, lng, radius_km = None, None, 10.0
        if lat_param is not None or lng_param is not None:
            if lat_param is None or lng_param is None:
                return custome_error_response("Both lat and lng coordinates must be provided together.")
            try:
                lat = float(lat_param)
                lng = float(lng_param)
            except ValueError:
                return custome_error_response("Coordinates lat and lng must be valid floating point numbers.")

        try:
            radius_km = float(radius_param)
        except ValueError:
            return custome_error_response("radius_km must be a valid number.")

        try:
            stores, is_fallback = StoreService.discover_nearby_stores(
                lat=lat,
                lng=lng,
                radius_km=radius_km
            )
        except ValueError as err:
            return custome_error_response(str(err))

        page = self.paginate_queryset(stores)
        msg = "Showing active stores (location fallback)." if is_fallback else f"Found {len(stores)} stores within {radius_km}km."
        if page is not None:
            serializer = PublicStoreSerializer(page, many=True, context={'request': request})
            res = self.get_paginated_response(serializer.data)
            res.data['message'] = msg
            return res

        serializer = PublicStoreSerializer(stores, many=True, context={'request': request})
        return custome_success_response(
            message=msg,
            data=serializer.data
        )


    @action(detail=True, methods=['post', 'delete'])
    def favorite(self, request, pk=None):
        """
        POST /stores/{id}/favorite/ -> Adds store to customer's favorites.
        DELETE /stores/{id}/favorite/ -> Removes store from customer's favorites.
        """
        if request.method == 'DELETE':
            try:
                removed = FavoriteService.remove_store_from_favorites(customer=request.user, store_id=pk)
                msg = "Store removed from favorites." if removed else "Store was not in favorites."
                return custome_success_response(message=msg)
            except ValueError as exc:
                return custome_error_response(str(exc), status_code=status.HTTP_404_NOT_FOUND)

        # POST
        try:
            fav = FavoriteService.add_store_to_favorites(customer=request.user, store_id=pk)
            return custome_success_response(
                message="Store added to favorites successfully.",
                data=FavoriteStoreSerializer(fav, context={'request': request}).data,
                data_title="favorite",
                status_code=status.HTTP_201_CREATED
            )
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='unfavorite')
    def unfavorite(self, request, pk=None):
        """POST /stores/{id}/unfavorite/ -> Helper alias to remove store from favorites."""
        try:
            removed = FavoriteService.remove_store_from_favorites(customer=request.user, store_id=pk)
            msg = "Store removed from favorites." if removed else "Store was not in favorites."
            return custome_success_response(message=msg)
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def favorites(self, request):
        """GET /stores/favorites/ -> Lists authenticated customer's favorite stores."""
        favorites_qs = FavoriteService.get_customer_favorites(request.user)
        page = self.paginate_queryset(favorites_qs)
        if page is not None:
            serializer = FavoriteStoreSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = FavoriteStoreSerializer(favorites_qs, many=True, context={'request': request})
        return custome_success_response(
            message="Favorite stores retrieved successfully.",
            data=serializer.data
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsStaffOrAdmin])
    def verify(self, request, pk=None):
        """POST /stores/{id}/verify/ -> Platform admin approves and verifies a store."""
        store = StoreRepository.get_by_id(pk)
        if not store:
            return custome_error_response("Store not found.", status_code=status.HTTP_404_NOT_FOUND)
        notes = request.data.get('notes', '')
        verified_store = StoreService.verify_store(store, verified_by=request.user, notes=notes)
        return custome_success_response(
            message="Store verified successfully.",
            data=StoreSerializer(verified_store).data,
            data_title="store"
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsStaffOrAdmin])
    def suspend(self, request, pk=None):
        """POST /stores/{id}/suspend/ -> Platform admin suspends a store."""
        store = StoreRepository.get_by_id(pk)
        if not store:
            return custome_error_response("Store not found.", status_code=status.HTTP_404_NOT_FOUND)
        reason = request.data.get('reason', '')
        suspended_store = StoreService.suspend_store(store, reason=reason, actor=request.user)
        return custome_success_response(
            message="Store suspended successfully.",
            data=StoreSerializer(suspended_store).data,
            data_title="store"
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsStaffOrAdmin])
    def activate(self, request, pk=None):
        """POST /stores/{id}/activate/ -> Platform admin reactivates a suspended store."""
        store = StoreRepository.get_by_id(pk)
        if not store:
            return custome_error_response("Store not found.", status_code=status.HTTP_404_NOT_FOUND)
        activated_store = StoreService.activate_store(store, actor=request.user)
        return custome_success_response(
            message="Store reactivated successfully.",
            data=StoreSerializer(activated_store).data,
            data_title="store"
        )

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsStaffOrAdmin], url_path='governance-overview')
    def governance_overview(self, request):
        """GET /stores/governance-overview/ -> Platform metrics for administrators."""
        metrics = StoreService.get_platform_governance_overview()
        return custome_success_response(
            message="Platform governance overview retrieved.",
            data=metrics,
            data_title="overview"
        )


