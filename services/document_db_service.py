"""
Document DB Service
-------------------
Subscribes to inference.completed events.
Stores annotation documents in TinyDB (a lightweight JSON document database).
Publishes annotation.stored when the document is saved.

TinyDB stores all documents in data/annotations_db.json.
Each document is keyed by image_id for idempotent upserts.
"""

import json
import os
from tinydb import TinyDB, Query

from broker.redis_broker import RedisBroker
from events.schemas import TOPICS, make_event, validate_event

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

# TinyDB instance — persists to disk as JSON
db = TinyDB("data/annotations_db.json")
ImageRecord = Query()


def upsert_annotation(document: dict) -> None:
    """
    Insert or update an annotation document in TinyDB.
    Uses image_id as the unique key — idempotent on duplicate events.
    """
    image_id = document["image_id"]
    db.upsert(document, ImageRecord.image_id == image_id)
    count = len(db)
    print(f"[DocumentDB] Upserted annotation for {image_id} | total docs: {count}")


def get_annotation(image_id: str) -> dict | None:
    """Retrieve an annotation document by image_id."""
    results = db.search(ImageRecord.image_id == image_id)
    return results[0] if results else None


def get_all_annotations() -> list:
    """Return all annotation documents."""
    return db.all()


def handle_inference_completed(broker: RedisBroker, message: dict) -> None:
    """
    Handle an inference.completed event.
    Saves annotation to TinyDB and publishes annotation.stored.
    """
    if not validate_event(message):
        print(f"[DocumentDB] Invalid event — skipping: {message}")
        return

    payload = message["payload"]
    image_id = payload.get("image_id")

    document = {
        "image_id": image_id,
        "camera": payload.get("source"),
        "objects": payload.get("objects", []),
        "review": {"status": "pending", "notes": []},
        "history": ["submitted", "inference_completed"],
    }

    upsert_annotation(document)

    next_event = make_event(
        TOPICS["ANNOTATION_STORED"],
        {
            "image_id": image_id,
            "object_count": len(document["objects"]),
        },
    )
    broker.publish(TOPICS["ANNOTATION_STORED"], next_event)


def run(broker: RedisBroker) -> None:
    """Start the document DB service listener."""
    print("[DocumentDB] Listening on inference.completed ...")
    pubsub = broker.subscribe(TOPICS["INFERENCE_COMPLETED"])

    for raw in pubsub.listen():
        if raw["type"] == "message":
            try:
                event = json.loads(raw["data"])
                handle_inference_completed(broker, event)
            except Exception as e:
                print(f"[DocumentDB] Error handling message: {e}")


if __name__ == "__main__":
    broker = RedisBroker()
    run(broker)
