from unittest.mock import patch
from django.test import TestCase, Client
from django.core.cache import cache


class ObservabilityAndHealthTests(TestCase):
    """
    Automated test suite verifying deployment readiness, liveness probes,
    database checks, cache checks, and secret protection per .agents/skills/deployment-observability/SKILL.md.
    """

    def setUp(self):
        self.client = Client()

    def test_health_view_html_render(self):
        """Default GET /health/ returns HTML dashboard for human monitoring."""
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/html', response['Content-Type'])
        self.assertContains(response, 'Smart Memo')
        self.assertContains(response, 'Server health')

    def test_health_view_json_content_negotiation(self):
        """GET /health/ with Accept: application/json returns structured metrics JSON."""
        response = self.client.get('/health/', HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/json', response['Content-Type'])
        data = response.json()
        self.assertEqual(data.get('status'), 'ok')
        self.assertIn('server_health', data)
        self.assertIn('system', data)

    def test_liveness_probe_returns_200_alive(self):
        """GET /health/live/ returns 200 alive for container orchestrators."""
        response = self.client.get('/health/live/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'alive')
        self.assertEqual(data.get('service'), 'smart-memo-backend')

    def test_readiness_probe_returns_200_when_healthy(self):
        """GET /health/ready/ verifies database, migrations, and cache."""
        response = self.client.get('/health/ready/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'ready')
        self.assertEqual(data['checks'].get('database'), 'connected')
        self.assertEqual(data['checks'].get('migrations'), 'up_to_date')
        self.assertEqual(data['checks'].get('cache'), 'connected')

    def test_readiness_probe_returns_503_on_db_outage(self):
        """GET /health/ready/ returns 503 if database connection fails."""
        with patch('django.db.connection.cursor', side_effect=Exception("DB Connection Timeout")):
            response = self.client.get('/health/ready/')
            self.assertEqual(response.status_code, 503)
            data = response.json()
            self.assertEqual(data.get('status'), 'unhealthy')
            self.assertIn('unhealthy', data['checks'].get('database'))

    def test_health_endpoints_never_leak_secrets(self):
        """Verify health checks do not leak environment passwords or Django secret key."""
        from django.conf import settings
        secret_key = settings.SECRET_KEY

        for endpoint in ['/health/', '/health/live/', '/health/ready/']:
            response = self.client.get(endpoint)
            content = response.content.decode('utf-8')
            self.assertNotIn(secret_key, content)
            self.assertNotIn('PASSWORD', content)
