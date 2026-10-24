from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from users.models.user_mod import User
from users.repositories.user_repository import UserRepository
from stores.models.store_mod import Store
from stores.repositories.store_repository import StoreRepository
from products.models.product_mod import Product
from cards.services.card_service import CardService
from shared.enums.enums import UserRoleEnum


class PlatformAdminGovernanceTests(TestCase):
    """
    Automated test suite verifying Platform Administration & Store Governance
    per .agents/skills/store-management/SKILL.md and MASTER_PROMPT.md.
    """

    def setUp(self):
        self.client = APIClient()

        # Users
        self.admin = UserRepository.create_user(
            email='admin@platform.com',
            password='AdminPassword123!',
            role=UserRoleEnum.SUPERUSER,
            is_staff=True,
            is_superuser=True
        )
        self.staff = UserRepository.create_user(
            email='staff@platform.com',
            password='StaffPassword123!',
            role=UserRoleEnum.STAFF,
            is_staff=True
        )
        self.vendor_a = UserRepository.create_user(
            email='vendor_a@store.com',
            password='VendorPassword123!',
            role=UserRoleEnum.VENDOR
        )
        self.vendor_b = UserRepository.create_user(
            email='vendor_b@store.com',
            password='VendorPassword123!',
            role=UserRoleEnum.VENDOR
        )
        self.customer = UserRepository.create_user(
            email='customer@buyer.com',
            password='CustomerPassword123!',
            role=UserRoleEnum.CUSTOMER
        )

        # Stores
        self.store_a = StoreRepository.create_store(
            vendor=self.vendor_a,
            name="Vendor A Supermarket",
            address="123 Alpha Road",
            is_active=True,
            is_verified=True,
            delivery_enabled=True,
            pickup_enabled=True
        )
        self.store_b = StoreRepository.create_store(
            vendor=self.vendor_b,
            name="Vendor B Electronics",
            address="456 Beta Avenue",
            is_active=True,
            is_verified=False,  # Unverified
            delivery_enabled=True,
            pickup_enabled=True
        )

    def test_platform_staff_can_list_all_stores_across_tenants(self):
        """Platform staff sees stores across all tenants in GET /stores/."""
        self.client.force_authenticate(user=self.staff)
        response = self.client.get('/stores/')
        self.assertEqual(response.status_code, 200)
        data = response.data['data'] if 'data' in response.data else response.data['results']
        store_ids = [s['id'] for s in data]
        self.assertIn(self.store_a.id, store_ids)
        self.assertIn(self.store_b.id, store_ids)

    def test_vendor_sees_only_own_stores(self):
        """Vendor A only sees Store A in GET /stores/; Store B is excluded."""
        self.client.force_authenticate(user=self.vendor_a)
        response = self.client.get('/stores/')
        self.assertEqual(response.status_code, 200)
        data = response.data['data'] if 'data' in response.data else response.data['results']
        store_ids = [s['id'] for s in data]
        self.assertIn(self.store_a.id, store_ids)
        self.assertNotIn(self.store_b.id, store_ids)

    def test_platform_staff_can_verify_unverified_store(self):
        """POST /stores/{id}/verify/ allows staff to approve and verify a store."""
        self.client.force_authenticate(user=self.staff)
        response = self.client.post(f'/stores/{self.store_b.id}/verify/', {
            'notes': 'Trade license and TIN verified.'
        })
        self.assertEqual(response.status_code, 200)
        self.store_b.refresh_from_db()
        self.assertTrue(self.store_b.is_verified)
        self.assertIsNotNone(self.store_b.verified_at)
        self.assertEqual(self.store_b.verification_notes, 'Trade license and TIN verified.')

    def test_vendor_cannot_verify_store(self):
        """Vendor cannot approve or verify a store (403 Forbidden)."""
        self.client.force_authenticate(user=self.vendor_a)
        response = self.client.post(f'/stores/{self.store_b.id}/verify/', {
            'notes': 'Unauthorized verification attempt.'
        })
        self.assertEqual(response.status_code, 403)

    def test_customer_cannot_verify_store(self):
        """Customer cannot approve or verify a store (403 Forbidden)."""
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(f'/stores/{self.store_b.id}/verify/', {})
        self.assertEqual(response.status_code, 403)

    def test_vendor_cannot_self_verify_via_patch(self):
        """Vendor updating store profile cannot self-verify via read-only fields."""
        self.client.force_authenticate(user=self.vendor_b)
        response = self.client.patch(f'/stores/{self.store_b.id}/', {
            'is_verified': True,
            'name': 'Updated Vendor B Name'
        })
        self.assertEqual(response.status_code, 200)
        self.store_b.refresh_from_db()
        self.assertEqual(self.store_b.name, 'Updated Vendor B Name')
        self.assertFalse(self.store_b.is_verified)  # is_verified unchanged

    def test_platform_staff_can_suspend_and_reactivate_store(self):
        """Staff can suspend a store and subsequently reactivate it."""
        self.client.force_authenticate(user=self.staff)

        # Suspend
        suspend_resp = self.client.post(f'/stores/{self.store_a.id}/suspend/', {
            'reason': 'Customer policy violation.'
        })
        self.assertEqual(suspend_resp.status_code, 200)
        self.store_a.refresh_from_db()
        self.assertFalse(self.store_a.is_active)
        self.assertEqual(self.store_a.verification_notes, 'Customer policy violation.')

        # Reactivate
        activate_resp = self.client.post(f'/stores/{self.store_a.id}/activate/')
        self.assertEqual(activate_resp.status_code, 200)
        self.store_a.refresh_from_db()
        self.assertTrue(self.store_a.is_active)

    def test_suspended_or_unverified_store_excluded_from_public_discovery(self):
        """Unverified or suspended stores do not appear in GET /stores/public/."""
        # store_b is unverified
        response = self.client.get('/stores/public/')
        self.assertEqual(response.status_code, 200)
        store_names = [s['name'] for s in response.data['data']]
        self.assertIn(self.store_a.name, store_names)
        self.assertNotIn(self.store_b.name, store_names)

        # Suspend store_a as well
        self.store_a.is_active = False
        self.store_a.save()

        response2 = self.client.get('/stores/public/')
        self.assertEqual(response2.status_code, 200)
        store_names2 = [s['name'] for s in response2.data['data']]
        self.assertNotIn(self.store_a.name, store_names2)

    def test_order_rejected_for_unverified_or_suspended_store(self):
        """Customer cannot submit checkout on an unverified or inactive store."""
        # Create product in unverified store_b
        product = Product.objects.create(
            store=self.store_b,
            name="Test Widget",
            price=Decimal("50.00"),
            sku="WIDGET-01",
            is_active=True
        )

        # Customer adds item to draft memo
        memo = CardService.get_or_create_active_memo(self.customer)
        CardService.add_product_to_card(card_id=memo.id, product_id=product.id, quantity=Decimal("1.000"), actor=self.customer)


        # Checkout attempt
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(f'/cards/{memo.id}/checkout/', {
            'fulfillment_type': 'PICKUP'
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("inactive or pending administrative verification", response.data['message'])

    def test_platform_staff_can_view_governance_overview(self):
        """Staff user can retrieve aggregated platform overview metrics."""
        self.client.force_authenticate(user=self.staff)
        response = self.client.get('/stores/governance-overview/')
        self.assertEqual(response.status_code, 200)
        data = response.data['data'] if 'data' in response.data else response.data
        overview = data.get('overview', data)
        self.assertIn('stores', overview)
        self.assertIn('users', overview)
        self.assertIn('orders', overview)
        self.assertGreaterEqual(overview['stores']['total'], 2)
        self.assertGreaterEqual(overview['users']['total_vendors'], 2)

    def test_vendor_and_customer_blocked_from_governance_overview(self):
        """Vendors and customers cannot access platform governance overview."""
        self.client.force_authenticate(user=self.vendor_a)
        resp_vendor = self.client.get('/stores/governance-overview/')
        self.assertEqual(resp_vendor.status_code, 403)

        self.client.force_authenticate(user=self.customer)
        resp_cust = self.client.get('/stores/governance-overview/')
        self.assertEqual(resp_cust.status_code, 403)

    def test_unauthenticated_requests_blocked(self):
        """Unauthenticated requests to admin governance endpoints return 401 or 403."""
        endpoints = [
            ('post', f'/stores/{self.store_a.id}/verify/'),
            ('post', f'/stores/{self.store_a.id}/suspend/'),
            ('post', f'/stores/{self.store_a.id}/activate/'),
            ('get', '/stores/governance-overview/'),
        ]
        for method, url in endpoints:
            req_func = getattr(self.client, method)
            response = req_func(url)
            self.assertIn(response.status_code, [401, 403])
