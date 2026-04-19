"""
Unit tests for the Redis broker.
Uses mocking so tests run without a live Redis connection.
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from events.schemas import TOPICS, make_event


class TestRedisBrokerPublish:
    def _make_broker_with_mock_client(self):
        """Helper: create a RedisBroker instance with a mocked Redis client."""
        from broker.redis_broker import RedisBroker
        broker = RedisBroker.__new__(RedisBroker)
        broker.client = MagicMock()
        return broker

    def test_publish_calls_redis_publish(self):
        """broker.publish() must call client.publish() exactly once."""
        broker = self._make_broker_with_mock_client()
        event = make_event(TOPICS["IMAGE_SUBMITTED"], {"image_id": "img_001"})
        broker.publish(TOPICS["IMAGE_SUBMITTED"], event)
        broker.client.publish.assert_called_once()

    def test_publish_uses_correct_topic(self):
        """broker.publish() must pass the correct topic to Redis."""
        broker = self._make_broker_with_mock_client()
        event = make_event(TOPICS["IMAGE_SUBMITTED"], {"image_id": "img_002"})
        broker.publish("image.submitted", event)
        call_args = broker.client.publish.call_args
        assert call_args[0][0] == "image.submitted"

    def test_publish_serializes_event_to_json(self):
        """The second argument to client.publish() must be valid JSON."""
        broker = self._make_broker_with_mock_client()
        event = make_event(TOPICS["IMAGE_SUBMITTED"], {"image_id": "img_003"})
        broker.publish("image.submitted", event)
        call_args = broker.client.publish.call_args
        raw = call_args[0][1]
        parsed = json.loads(raw)  # Must not raise
        assert parsed["topic"] == "image.submitted"

    def test_duplicate_events_call_publish_twice(self):
        """Publishing the same event twice must result in two publish calls."""
        broker = self._make_broker_with_mock_client()
        event = make_event(TOPICS["IMAGE_SUBMITTED"], {"image_id": "img_001"})
        broker.publish("image.submitted", event)
        broker.publish("image.submitted", event)
        assert broker.client.publish.call_count == 2


class TestRedisBrokerSubscribe:
    def _make_broker_with_mock_client(self):
        from broker.redis_broker import RedisBroker
        broker = RedisBroker.__new__(RedisBroker)
        broker.client = MagicMock()
        return broker

    def test_subscribe_creates_pubsub(self):
        """broker.subscribe() must call client.pubsub()."""
        broker = self._make_broker_with_mock_client()
        broker.subscribe("image.submitted")
        broker.client.pubsub.assert_called_once()

    def test_subscribe_multiple_topics(self):
        """broker.subscribe() with multiple topics must subscribe to each one."""
        broker = self._make_broker_with_mock_client()
        mock_pubsub = MagicMock()
        broker.client.pubsub.return_value = mock_pubsub
        broker.subscribe("image.submitted", "inference.completed")
        assert mock_pubsub.subscribe.call_count == 2


class TestRedisBrokerPing:
    def test_ping_returns_true_on_success(self):
        """broker.ping() must return True when Redis is reachable."""
        from broker.redis_broker import RedisBroker
        broker = RedisBroker.__new__(RedisBroker)
        broker.client = MagicMock()
        broker.client.ping.return_value = True
        assert broker.ping() is True

    def test_ping_returns_false_on_failure(self):
        """broker.ping() must return False (not raise) when Redis is unreachable."""
        from broker.redis_broker import RedisBroker
        broker = RedisBroker.__new__(RedisBroker)
        broker.client = MagicMock()
        broker.client.ping.side_effect = Exception("Connection refused")
        assert broker.ping() is False
