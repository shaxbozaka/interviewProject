import json
import logging
from datetime import datetime
from typing import Any

from django.conf import settings

from .tracing import trace_step

logger = logging.getLogger(__name__)

_producer = None


def _get_producer():
    """Lazy initialization of Kafka producer."""
    global _producer
    if _producer is None:
        try:
            from kafka import KafkaProducer
            bootstrap_servers = getattr(
                settings, 'KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'
            )
            _producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
            )
            logger.info('Kafka producer connected to %s', bootstrap_servers)
        except Exception as e:
            logger.warning('Kafka producer unavailable: %s', e)
            return None
    return _producer


def publish_event(topic: str, event_type: str, data: dict[str, Any], key: str | None = None):
    """
    Publish an event to a Kafka topic.
    Fails silently if Kafka is unavailable (graceful degradation).
    """
    event = {
        'event_type': event_type,
        'timestamp': datetime.utcnow().isoformat(),
        'data': data,
    }
    producer = _get_producer()
    if producer is None:
        logger.debug('Kafka unavailable, event dropped: %s/%s', topic, event_type)
        trace_step(f'Kafka UNAVAILABLE — event dropped: {topic}/{event_type}', 'event')
        return
    try:
        producer.send(topic, value=event, key=key)
        producer.flush(timeout=5)
        logger.info('Event published: %s/%s', topic, event_type)
        trace_step(f'Kafka: sent {event_type} → {topic} (flushed)', 'event')
    except Exception as e:
        logger.error('Failed to publish event %s/%s: %s', topic, event_type, e)
        trace_step(f'Kafka FAILED: {topic}/{event_type} — {e}', 'event')
