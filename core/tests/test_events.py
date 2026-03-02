import pytest
from unittest.mock import patch, MagicMock
from core.events import publish_event


class TestPublishEvent:
    @patch('core.events._get_producer')
    def test_publish_event_with_producer(self, mock_get_producer):
        mock_producer = MagicMock()
        mock_get_producer.return_value = mock_producer
        publish_event('test-topic', 'test.event', {'key': 'value'}, key='1')
        mock_producer.send.assert_called_once()
        mock_producer.flush.assert_called_once()

    @patch('core.events._get_producer')
    def test_publish_event_without_producer(self, mock_get_producer):
        mock_get_producer.return_value = None
        # Should not raise
        publish_event('test-topic', 'test.event', {'key': 'value'})
