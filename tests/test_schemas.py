"""
Unit tests for event schemas.
Tests that events are well-formed and validation logic works correctly.
"""

import pytest
from events.schemas import make_event, validate_event, TOPICS


class TestMakeEvent:
    def test_event_has_all_required_fields(self):
        """A valid event must contain type, topic, event_id, timestamp, and payload."""
        event = make_event(TOPICS["IMAGE_SUBMITTED"], {"image_id": "img_001"})
        assert "type" in event
        assert "topic" in event
        assert "event_id" in event
        assert "timestamp" in event
        assert "payload" in event

    def test_event_type_is_publish(self):
        """Event type must always be 'publish'."""
        event = make_event(TOPICS["IMAGE_SUBMITTED"], {})
        assert event["type"] == "publish"

    def test_event_topic_matches_input(self):
        """The topic in the event must match the topic passed in."""
        event = make_event(TOPICS["INFERENCE_COMPLETED"], {"image_id": "img_002"})
        assert event["topic"] == "inference.completed"

    def test_event_ids_are_unique(self):
        """Two events generated back-to-back must have different event_ids."""
        e1 = make_event(TOPICS["IMAGE_SUBMITTED"], {})
        e2 = make_event(TOPICS["IMAGE_SUBMITTED"], {})
        assert e1["event_id"] != e2["event_id"]

    def test_payload_is_preserved(self):
        """The payload passed in must appear unchanged in the event."""
        payload = {"image_id": "img_003", "source": "camera_B"}
        event = make_event(TOPICS["IMAGE_SUBMITTED"], payload)
        assert event["payload"] == payload

    def test_timestamp_is_string(self):
        """Timestamp must be a non-empty string."""
        event = make_event(TOPICS["IMAGE_SUBMITTED"], {})
        assert isinstance(event["timestamp"], str)
        assert len(event["timestamp"]) > 0


class TestValidateEvent:
    def test_valid_event_passes(self):
        """A well-formed event must pass validation."""
        event = make_event(TOPICS["IMAGE_SUBMITTED"], {"image_id": "img_004"})
        assert validate_event(event) is True

    def test_missing_topic_fails(self):
        """An event missing 'topic' must fail validation."""
        event = make_event(TOPICS["IMAGE_SUBMITTED"], {})
        del event["topic"]
        assert validate_event(event) is False

    def test_missing_event_id_fails(self):
        """An event missing 'event_id' must fail validation."""
        event = make_event(TOPICS["IMAGE_SUBMITTED"], {})
        del event["event_id"]
        assert validate_event(event) is False

    def test_empty_dict_fails(self):
        """An empty dict must fail validation."""
        assert validate_event({}) is False

    def test_malformed_event_does_not_raise(self):
        """Passing a malformed event to validate_event must not raise an exception."""
        try:
            result = validate_event({"random": "garbage"})
            assert result is False
        except Exception:
            pytest.fail("validate_event raised an exception on malformed input")


class TestTopics:
    def test_all_topics_are_strings(self):
        """Every topic value must be a non-empty string."""
        for key, value in TOPICS.items():
            assert isinstance(value, str) and len(value) > 0

    def test_required_topics_exist(self):
        """All five required topics must be defined."""
        required = {
            "IMAGE_SUBMITTED",
            "INFERENCE_COMPLETED",
            "ANNOTATION_STORED",
            "EMBEDDING_CREATED",
            "ANNOTATION_CORRECTED",
        }
        assert required.issubset(TOPICS.keys())
