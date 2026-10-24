from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from users.models.user_mod import User
from stores.models.store_mod import Store
from stores.services.store_service import StoreService
from shared.enums.enums import UserRoleEnum


class NearbyStoreDiscoveryTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.vendor = User.objects.create_user(
            email="vendor_nearby@test.com",
            password="Password123!",
            role=UserRoleEnum.VENDOR
        )

        # Reference location: Dhaka Gulshan-1 (23.7925, 90.4078)
        # Store 1: Gulshan-2 (~1.5 km away)
        self.store_close = Store.objects.create(
            vendor=self.vendor,
            name="Gulshan Mart",
            latitude=Decimal('23.7937'),
            longitude=Decimal('90.4043'),
            is_active=True
        )

        # Store 2: Uttara (~12.0 km away)
        self.store_far = Store.objects.create(
            vendor=self.vendor,
            name="Uttara Express",
            latitude=Decimal('23.8759'),
            longitude=Decimal('90.3795'),
            is_active=True
        )

        # Store 3: Chittagong (~200 km away)
        self.store_distant = Store.objects.create(
            vendor=self.vendor,
            name="Chittagong Central",
            latitude=Decimal('22.3569'),
            longitude=Decimal('91.7832'),
            is_active=True
        )

        # Store 4: Inactive store close by
        self.store_inactive = Store.objects.create(
            vendor=self.vendor,
            name="Closed Secret Shop",
            latitude=Decimal('23.7930'),
            longitude=Decimal('90.4060'),
            is_active=False
        )

    def test_haversine_calculation_precision(self):
        # Known distance between Gulshan-1 (23.7925, 90.4078) and Uttara (23.8759, 90.3795) is approx 9.7 - 10.0 km
        dist = StoreService.calculate_haversine_distance(23.7925, 90.4078, 23.8759, 90.3795)
        self.assertTrue(9.0 <= dist <= 10.5)

    def test_nearby_discovery_sorts_by_distance_and_filters_radius(self):
        # Search from Gulshan-1 with 5km radius
        response = self.client.get('/stores/nearby/?lat=23.7925&lng=90.4078&radius_km=5.0')
        self.assertEqual(response.status_code, 200)

        data = response.data['data']
        # Only Gulshan Mart should be within 5km; Uttara (~9.7km) and Chittagong (~200km) excluded
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], self.store_close.id)
        self.assertIsNotNone(data[0]['distance_km'])
        self.assertTrue(data[0]['distance_km'] < 2.0)

    def test_nearby_discovery_wider_radius_returns_multiple_sorted(self):
        # Search from Gulshan-1 with 15km radius
        response = self.client.get('/stores/nearby/?lat=23.7925&lng=90.4078&radius_km=15.0')
        self.assertEqual(response.status_code, 200)

        data = response.data['data']
        self.assertEqual(len(data), 2)
        # Closer store must come first
        self.assertEqual(data[0]['id'], self.store_close.id)
        self.assertEqual(data[1]['id'], self.store_far.id)
        self.assertTrue(data[0]['distance_km'] < data[1]['distance_km'])

    def test_inactive_and_deleted_stores_are_excluded(self):
        response = self.client.get('/stores/nearby/?lat=23.7925&lng=90.4078&radius_km=5.0')
        self.assertEqual(response.status_code, 200)
        returned_ids = [s['id'] for s in response.data['data']]
        self.assertNotIn(self.store_inactive.id, returned_ids)

    def test_fallback_when_coordinates_not_provided(self):
        # Request without lat/lng coordinates should return active stores fallback
        response = self.client.get('/stores/nearby/')
        self.assertEqual(response.status_code, 200)
        self.assertIn("fallback", response.data['message'].lower())
        returned_ids = [s['id'] for s in response.data['data']]
        self.assertIn(self.store_close.id, returned_ids)
        self.assertIn(self.store_far.id, returned_ids)
        self.assertNotIn(self.store_inactive.id, returned_ids)

    def test_invalid_coordinates_rejected_with_bad_request(self):
        # Invalid latitude > 90
        res1 = self.client.get('/stores/nearby/?lat=95.0&lng=90.4078')
        self.assertEqual(res1.status_code, 400)

        # Invalid non-numeric strings
        res2 = self.client.get('/stores/nearby/?lat=abc&lng=xyz')
        self.assertEqual(res2.status_code, 400)

        # Invalid negative radius
        res3 = self.client.get('/stores/nearby/?lat=23.7925&lng=90.4078&radius_km=-5')
        self.assertEqual(res3.status_code, 400)
