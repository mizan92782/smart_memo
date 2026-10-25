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
        if self.action in ['list', 'retrieve', 'public', 'public_detail', 'public_storefront', 'nearby', 'calculate_delivery_fee']:
            return [AllowAny()]
        if self.action == 'reviews':
            if self.request.method == 'GET':
                return [AllowAny()]
            return [IsAuthenticated(), IsCustomer()]
        if self.action in ['favorite', 'unfavorite', 'favorites']:
            return [IsAuthenticated(), IsCustomer()]
        if self.action in ['verify', 'suspend', 'activate', 'governance_overview']:
            return [IsAuthenticated(), IsStaffOrAdmin()]
        if self.action == 'create':
            return [IsAuthenticated(), IsVendor()]
        return [IsAuthenticated(), IsStoreOwner()]

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return StoreRepository.get_public_active_stores()
        if (
            self.request.user.is_superuser
            or self.request.user.is_staff
            or getattr(self.request.user, 'role', None) in (UserRoleEnum.STAFF, UserRoleEnum.SUPERUSER)
        ):
            return StoreRepository.get_all_stores()
        if getattr(self.request.user, 'role', None) == UserRoleEnum.VENDOR:
            return StoreRepository.get_by_vendor(self.request.user.id)
        return StoreRepository.get_public_active_stores()

    def get_serializer_class(self):
        if self.action in ['public', 'public_detail', 'public_storefront', 'nearby']:
            return PublicStoreSerializer
        if not self.request.user.is_authenticated or getattr(self.request.user, 'role', None) == UserRoleEnum.CUSTOMER:
            if self.action in ['list', 'retrieve']:
                return PublicStoreSerializer
        return StoreSerializer


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

    @action(detail=False, methods=['get'], permission_classes=[AllowAny], url_path=r'public-store/(?P<slug_or_domain>[^/]+)')
    def public_storefront(self, request, slug_or_domain=None):
        """
        Public storefront resolver for merchant websites.
        Consists of URLs like /Eshopping/shopname.com/ or /Eshopping/:slug.
        Resolves store by public_url_slug or slug or ID.
        Returns complete store branding info, owner details, operating hours, categories, and active products with images.
        """
        if not slug_or_domain:
            return custome_error_response("Store identifier or domain is required.", status_code=status.HTTP_400_BAD_REQUEST)

        store = StoreRepository.get_by_slug_or_domain(slug_or_domain)
        if not store or not store.is_active:
            return custome_error_response("Store website not found or inactive.", status_code=status.HTTP_404_NOT_FOUND)

        from categories.models.category_mod import Category
        from categories.serializers.category_ser import CategorySerializer
        from products.models.product_mod import Product
        from products.serializers.product_ser import ProductSerializer

        store_data = PublicStoreSerializer(store, context={'request': request}).data

        categories = Category.objects.filter(store=store, is_deleted=False)
        category_data = CategorySerializer(categories, many=True).data

        products = Product.objects.filter(
            store=store,
            is_deleted=False,
            is_active=True
        ).select_related('category').prefetch_related('images').order_by('name')
        product_data = ProductSerializer(products, many=True).data

        return custome_success_response(
            message=f"Storefront for '{store.name}' retrieved.",
            data={
                "store": store_data,
                "categories": category_data,
                "products": product_data,
                "product_count": len(product_data),
                "public_url": f"/Eshopping/{store.public_url_slug}/",
            },
            data_title="storefront"
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

    @action(detail=True, methods=['post'], permission_classes=[AllowAny], url_path='calculate-delivery-fee')
    def calculate_delivery_fee(self, request, pk=None):
        """POST /stores/{id}/calculate-delivery-fee/ -> Computes dynamic delivery fee based on customer address/coordinates."""
        store = StoreRepository.get_by_id(pk)
        if not store:
            return custome_error_response("Store not found.", status_code=status.HTTP_404_NOT_FOUND)

        customer_lat = None
        customer_lng = None

        address_id = request.data.get('address_id')
        if address_id:
            from users.models.address_mod import CustomerAddress
            try:
                addr = CustomerAddress.objects.get(id=address_id, is_deleted=False)
                customer_lat = addr.latitude
                customer_lng = addr.longitude
            except CustomerAddress.DoesNotExist:
                return custome_error_response("Address not found.", status_code=status.HTTP_404_NOT_FOUND)
        else:
            lat_val = request.data.get('lat')
            lng_val = request.data.get('lng')
            if lat_val is not None and lng_val is not None:
                try:
                    customer_lat = float(lat_val)
                    customer_lng = float(lng_val)
                except (ValueError, TypeError):
                    return custome_error_response("Coordinates must be valid numbers.")

        fee, dist = StoreService.calculate_delivery_fee(store, customer_lat=customer_lat, customer_lng=customer_lng)
        return custome_success_response(
            message="Delivery fee calculated successfully.",
            data={
                "store_id": store.id,
                "distance_km": round(dist, 2) if dist is not None else None,
                "delivery_fee": str(fee),
                "is_dynamic": dist is not None
            }
        )

    @action(detail=True, methods=['get', 'post'], url_path='reviews')
    def reviews(self, request, pk=None):
        """
        GET /stores/{id}/reviews/ -> Lists verified customer reviews for this store (Public).
        POST /stores/{id}/reviews/ -> Authenticated customer submits a review for a completed order.
        """
        store = StoreRepository.get_by_id(pk)
        if not store:
            return custome_error_response("Store not found.", status_code=status.HTTP_404_NOT_FOUND)

        if request.method == 'GET':
            from stores.services.review_service import ReviewService
            from stores.serializers.review_ser import StoreReviewSerializer
            reviews_qs = ReviewService.get_store_reviews(store_id=pk)
            page = self.paginate_queryset(reviews_qs)
            if page is not None:
                serializer = StoreReviewSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = StoreReviewSerializer(reviews_qs, many=True)
            return custome_success_response(
                message="Store reviews retrieved successfully.",
                data=serializer.data
            )

        # POST: Create review
        from stores.serializers.review_ser import StoreReviewCreateSerializer, StoreReviewSerializer
        from stores.services.review_service import ReviewService

        serializer = StoreReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            review = ReviewService.create_review(
                customer=request.user,
                store_id=store.id,
                order_id=serializer.validated_data['order_id'],
                rating=serializer.validated_data['rating'],
                comment=serializer.validated_data.get('comment', '')
            )
            return custome_success_response(
                message="Review submitted successfully.",
                data=StoreReviewSerializer(review).data,
                status_code=status.HTTP_201_CREATED
            )
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)
        except PermissionError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_403_FORBIDDEN)

    @action(detail=True, methods=['get', 'post'], permission_classes=[IsAuthenticated, IsVendor])
    def coupons(self, request, pk=None):
        """
        GET /stores/{id}/coupons/ -> Lists vendor's promotional coupons for this store.
        POST /stores/{id}/coupons/ -> Vendor creates a promotional coupon for this store.
        """
        store = StoreRepository.get_by_id(pk)
        if not store:
            return custome_error_response("Store not found.", status_code=status.HTTP_404_NOT_FOUND)

        from stores.services.coupon_service import CouponService
        from stores.serializers.coupon_ser import CouponSerializer

        if request.method == 'GET':
            try:
                coupons_qs = CouponService.get_store_coupons(store_id=store.id, actor=request.user)
                page = self.paginate_queryset(coupons_qs)
                if page is not None:
                    serializer = CouponSerializer(page, many=True)
                    return self.get_paginated_response(serializer.data)

                serializer = CouponSerializer(coupons_qs, many=True)
                return custome_success_response(
                    message="Coupons retrieved successfully.",
                    data=serializer.data
                )
            except PermissionError as exc:
                return custome_error_response(str(exc), status_code=status.HTTP_403_FORBIDDEN)
            except ValueError as exc:
                return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

        # POST
        try:
            coupon = CouponService.create_coupon(
                store_id=store.id,
                actor=request.user,
                data=request.data
            )
            return custome_success_response(
                message=f"Coupon '{coupon.code}' created successfully.",
                data=CouponSerializer(coupon).data,
                status_code=status.HTTP_201_CREATED
            )
        except PermissionError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_403_FORBIDDEN)
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get', 'post'], url_path='memo', permission_classes=[IsAuthenticated])
    def store_memo(self, request, pk=None):
        """
        GET /stores/{id}/memo/ — read the customer's current draft memo for this store.
        Pass ?create=false to peek without opening one (returns null when absent), so the
        UI can require the customer to name a memo before shopping.

        POST /stores/{id}/memo/ — open a memo for this store.
        Accepts 'title' (memo name) and 'shopping_mode' ('walk_in' or 'remote').
        Pass 'force_new': true to start an *additional* memo alongside any existing
        ones — a shopper can run several named memos at the same store at once
        (e.g. "Weekly Grocery" and "Office Supplies") and check them out separately.
        Without it, an existing draft is reused and renamed.
        """
        store = StoreRepository.get_by_id(pk)
        if not store:
            return custome_error_response("Store not found.", status_code=status.HTTP_404_NOT_FOUND)

        is_post = request.method == 'POST'
        shopping_mode = request.data.get('shopping_mode') if is_post else request.query_params.get('shopping_mode', 'remote')
        if not shopping_mode:
            shopping_mode = 'remote'
        title = (request.data.get('title') or '').strip() if is_post else None
        force_new = bool(request.data.get('force_new')) if is_post else False

        from cards.services.card_service import CardService
        from cards.serializers.card_ser import CardSerializer
        try:
            if not is_post and request.query_params.get('create', 'true').lower() in ['false', '0']:
                card = CardService.get_active_memo(user=request.user, store=store)
                if not card:
                    return custome_success_response(
                        message=f"No draft memo open for '{store.name}' yet.",
                        data=None
                    )
                return custome_success_response(
                    message=f"Draft memo for '{store.name}' retrieved.",
                    data=CardSerializer(card).data
                )

            if force_new:
                card = CardService.create_store_memo(
                    user=request.user,
                    store=store,
                    title=title or None,
                    shopping_mode=shopping_mode
                )
                return custome_success_response(
                    message=f"New memo opened for '{store.name}'.",
                    data=CardSerializer(card).data,
                    status_code=status.HTTP_201_CREATED
                )

            card = CardService.get_or_create_active_memo(
                user=request.user,
                store=store,
                shopping_mode=shopping_mode,
                title=title or None
            )
            # An existing memo keeps its identity, but the customer may rename it or
            # switch between walk-in and from-home shopping when re-opening it.
            if is_post:
                changed = []
                if title and card.title != title:
                    card.title = title
                    changed.append('title')
                if shopping_mode and card.shopping_mode != shopping_mode:
                    card.shopping_mode = shopping_mode
                    changed.append('shopping_mode')
                if changed:
                    card.save(update_fields=changed + ['updated_at'])
            return custome_success_response(
                message=f"Draft memo for '{store.name}' retrieved.",
                data=CardSerializer(card).data
            )
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)




