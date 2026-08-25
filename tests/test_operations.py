from unittest.mock import patch

from django.db.utils import OperationalError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient


class HealthCheckTests(TestCase):
    def test_liveness_does_not_require_authentication_or_database_query(self):
        with patch("config.health.connection.cursor") as cursor:
            response = APIClient().get('/api/v1/health/live/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'status': 'ok'})
        cursor.assert_not_called()

    def test_readiness_checks_database(self):
        response = APIClient().get('/api/v1/health/ready/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'status': 'ok'})

    def test_readiness_returns_503_when_database_is_unavailable(self):
        with patch(
            "config.health.connection.cursor",
            side_effect=OperationalError("database unavailable"),
        ):
            response = APIClient().get('/api/v1/health/ready/')

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data, {'status': 'unavailable'})

    def test_response_contains_request_id(self):
        response = APIClient().get(
            '/api/v1/health/live/',
            HTTP_X_REQUEST_ID='portfolio-smoke-check',
        )

        self.assertEqual(response['X-Request-ID'], 'portfolio-smoke-check')
