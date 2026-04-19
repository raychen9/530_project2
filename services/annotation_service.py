"""
Annotation Service
------------------
Subscribes to inference.completed events.
Stores annotation data in a simple in-memory document store (dict).
Publishes annotation.stored when the document is saved.

In Week 2 this will be replaced with a real document DB (e.g. MongoDB or TinyDB).
"""

import json

from broker.redis_broker import RedisBroker
from events.schemas import TOPICS, make_event, validate_event

# In-memory document store: image_id -> annotation document
# This simulates a document DB for Week 1
document_store: dict = {}


def store_annotation(image_id: str, document: dict) -> None:
    """
    Save or update an annotation document.
    Uses image_id as the key — idempotent if same image_id arrives twice.
    """
    document_store[image_id] = document
    print(f"[AnnotationService] Stored annotation for {image_id} | total docs: {len(document_store)}")


def handle_inference_completed(broker: RedisBroker, message: dict) -> None:
    """
    Handle an inference.completed event.
    Saves annotation to the document store and publishes annotation.stored.
    """
    if not validate_event(message):
        print(f"[AnnotationService] Invalid event — skipping: {message}")
        return

    payload = message["payload"]
    image_id = payload.get("image_id")

    # Build the annotation document
    document = {
        "image_id": image_id,
        "camera": payload.get("source"),
        "objects": payload.get("objects", []),
        "review": {"status": "pending", "notes": []},
        "history": ["submitted", "inference_completed"],
    }

    # Idempotency: update existing document instead of creating a duplicate
    store_annotation(image_id, document)

    # Publish annotation.stored for embedding service to pick up
    next_event = make_event(
        TOPICS["ANNOTATION_STORED"],
        {
            "image_id": image_id,
            "object_count": len(document["objects"]),
        },
    )
    broker.publish(TOPICS["ANNOTATION_STORED"], next_event)


def run(broker: RedisBroker) -> None:
    """Start the annotation service listener."""
    print("[AnnotationService] Listening on inference.completed ...")
    pubsub = broker.subscribe(TOPICS["INFERENCE_COMPLETED"])

    for raw in pubsub.listen():
        if raw["type"] == "message":
            try:
                event = json.loads(raw["data"])
                handle_inference_completed(broker, event)
            except Exception as e:
                print(f"[AnnotationService] Error handling message: {e}")


if __name__ == "__main__":
    broker = RedisBroker()
    run(broker)
