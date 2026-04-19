import uuid
from datetime import datetime, timezone

# All topic names used across the pub-sub system
TOPICS = {
    "IMAGE_SUBMITTED": "image.submitted",
    "INFERENCE_COMPLETED": "inference.completed",
    "ANNOTATION_STORED": "annotation.stored",
    "EMBEDDING_CREATED": "embedding.created",
    "ANNOTATION_CORRECTED": "annotation.corrected",
}


def make_event(topic: str, payload: dict) -> dict:
    """
    Create a standard-format event message.

    Args:
        topic: The pub-sub topic to publish to (use TOPICS constants)
        payload: The event-specific data

    Returns:
        A dict with required fields: type, topic, event_id, timestamp, payload
    """
    return {
        "type": "publish",
        "topic": topic,
        "event_id": f"evt_{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }


def validate_event(event: dict) -> bool:
    """
    Check that an event contains all required fields.

    Required fields: type, topic, event_id, timestamp, payload

    Returns:
        True if all required fields are present, False otherwise
    """
    required = {"type", "topic", "event_id", "timestamp", "payload"}
    return required.issubset(event.keys())
