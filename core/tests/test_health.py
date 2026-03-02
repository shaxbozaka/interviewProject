from unittest.mock import patch, MagicMock

import pytest


@pytest.mark.django_db
class TestHealthCheck:
    def test_healthy_when_all_services_up(self, api_client):
        with patch('core.health._check_kafka', return_value={'status': 'up', 'latency_ms': 5.0}), \
             patch('core.health._check_elasticsearch', return_value={'status': 'up', 'latency_ms': 3.0}):
            response = api_client.get('/health/')
            assert response.status_code == 200
            data = response.json()
            assert data['status'] == 'healthy'
            assert data['services']['database']['status'] == 'up'
            assert data['services']['redis']['status'] == 'up'

    def test_degraded_when_non_critical_down(self, api_client):
        with patch('core.health._check_kafka', return_value={'status': 'down', 'error': 'unavailable'}), \
             patch('core.health._check_elasticsearch', return_value={'status': 'down', 'error': 'unavailable'}):
            response = api_client.get('/health/')
            assert response.status_code == 200
            data = response.json()
            assert data['status'] == 'degraded'

    def test_unhealthy_when_database_down(self, api_client):
        with patch('core.health._check_database', return_value={'status': 'down', 'error': 'connection refused'}), \
             patch('core.health._check_kafka', return_value={'status': 'up', 'latency_ms': 5.0}), \
             patch('core.health._check_elasticsearch', return_value={'status': 'up', 'latency_ms': 3.0}):
            response = api_client.get('/health/')
            assert response.status_code == 503
            data = response.json()
            assert data['status'] == 'unhealthy'

    def test_includes_all_service_statuses(self, api_client):
        with patch('core.health._check_kafka', return_value={'status': 'down', 'error': 'n/a'}), \
             patch('core.health._check_elasticsearch', return_value={'status': 'down', 'error': 'n/a'}):
            response = api_client.get('/health/')
            data = response.json()
            assert 'database' in data['services']
            assert 'redis' in data['services']
            assert 'kafka' in data['services']
            assert 'elasticsearch' in data['services']

    def test_database_latency_included(self, api_client):
        with patch('core.health._check_kafka', return_value={'status': 'down', 'error': 'n/a'}), \
             patch('core.health._check_elasticsearch', return_value={'status': 'down', 'error': 'n/a'}):
            response = api_client.get('/health/')
            data = response.json()
            assert 'latency_ms' in data['services']['database']
