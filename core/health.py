"""
Health check endpoint that verifies connectivity to all services.

GET /health/ returns:
{
    "status": "healthy" | "degraded" | "unhealthy",
    "services": {
        "database": {"status": "up", "latency_ms": 1.2},
        "redis": {"status": "up", "latency_ms": 0.5},
        "kafka": {"status": "down", "error": "..."},
        "elasticsearch": {"status": "down", "error": "..."}
    }
}
"""
import time

from django.db import connection
from django.http import JsonResponse


def health_check(request):
    services = {}
    all_critical_up = True

    # Database check
    services['database'] = _check_database()
    if services['database']['status'] != 'up':
        all_critical_up = False

    # Redis check
    services['redis'] = _check_redis()
    if services['redis']['status'] != 'up':
        all_critical_up = False

    # Kafka check (non-critical — graceful degradation)
    services['kafka'] = _check_kafka()

    # Elasticsearch check (non-critical — graceful degradation)
    services['elasticsearch'] = _check_elasticsearch()

    non_critical_up = all(
        services[s]['status'] == 'up'
        for s in ['kafka', 'elasticsearch']
    )

    if all_critical_up and non_critical_up:
        overall = 'healthy'
    elif all_critical_up:
        overall = 'degraded'
    else:
        overall = 'unhealthy'

    status_code = 200 if all_critical_up else 503
    return JsonResponse({
        'status': overall,
        'services': services,
    }, status=status_code)


def _check_database() -> dict:
    try:
        start = time.monotonic()
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        latency = (time.monotonic() - start) * 1000
        return {'status': 'up', 'latency_ms': round(latency, 2)}
    except Exception as e:
        return {'status': 'down', 'error': str(e)}


def _check_redis() -> dict:
    try:
        from django.core.cache import cache
        start = time.monotonic()
        cache.set('__health_check__', '1', timeout=5)
        value = cache.get('__health_check__')
        latency = (time.monotonic() - start) * 1000
        if value == '1':
            return {'status': 'up', 'latency_ms': round(latency, 2)}
        return {'status': 'down', 'error': 'Cache read mismatch'}
    except Exception as e:
        return {'status': 'down', 'error': str(e)}


def _check_kafka() -> dict:
    try:
        from django.conf import settings
        from kafka import KafkaProducer
        start = time.monotonic()
        bootstrap = getattr(settings, 'KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        producer = KafkaProducer(
            bootstrap_servers=bootstrap,
            request_timeout_ms=3000,
            max_block_ms=3000,
        )
        producer.close(timeout=3)
        latency = (time.monotonic() - start) * 1000
        return {'status': 'up', 'latency_ms': round(latency, 2)}
    except Exception as e:
        return {'status': 'down', 'error': str(e)}


def _check_elasticsearch() -> dict:
    try:
        from django.conf import settings
        from elasticsearch import Elasticsearch
        start = time.monotonic()
        es_url = getattr(settings, 'ELASTICSEARCH_URL', 'http://localhost:9200')
        client = Elasticsearch(es_url, request_timeout=3)
        info = client.info()
        latency = (time.monotonic() - start) * 1000
        return {'status': 'up', 'latency_ms': round(latency, 2)}
    except Exception as e:
        return {'status': 'down', 'error': str(e)}
