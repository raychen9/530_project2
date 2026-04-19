"""
Embedding Service
-----------------
Subscribes to annotation.stored events.
Generates a fake embedding vector for each image (simulated for Week 1).
Publishes embedding.created when the vector is ready.

In Week 2 this will use a real embedding model or FAISS index.
"""

import json
import random

from broker.redis_broker import RedisBroker
from events.schemas import TOPICS, make_event, validate_event

# Dimension of the simulated embedding vector
EMBEDDING_DIM = 128


def generate_fake_embedding(image_id: str) -> list:
    """
    Generate a fake fixed-length embedding vector for an image.
    Uses image_id as seed so the same image always gets the same vector.
    """
    seed = sum(ord(c) for c in image_id)
    random.seed(seed)
    return [round(random.uniform(-1.0, 1.0), 4) for _ in range(EMBEDDING_DIM)]


def handle_annotation_stored(broker: RedisBroker, message: dict) -> None:
    """
    Handle an annotation.stored event.
    Generates a simulated embedding and publishes embedding.created.
    """
    if not validate_event(message):
        print(f"[EmbeddingService] Invalid event — skipping: {message}")
        return

    payload = message["payload"]
    image_id = payload.get("image_id")
    print(f"[EmbeddingService] Generating embedding for {image_id}")

    vector = generate_fake_embedding(image_id)

    # Publish embedding.created for the vector index service
    next_event = make_event(
        TOPICS["EMBEDDING_CREATED"],
        {
            "image_id": image_id,
            "vector": vector,
            "dim": EMBEDDING_DIM,
        },
    )
    broker.publish(TOPICS["EMBEDDING_CREATED"], next_event)


def run(broker: RedisBroker) -> None:
    """Start the embedding service listener."""
    print("[EmbeddingService] Listening on annotation.stored ...")
    pubsub = broker.subscribe(TOPICS["ANNOTATION_STORED"])

    for raw in pubsub.listen():
        if raw["type"] == "message":
            try:
                event = json.loads(raw["data"])
                handle_annotation_stored(broker, event)
            except Exception as e:
                print(f"[EmbeddingService] Error handling message: {e}")


if __name__ == "__main__":
    broker = RedisBroker()
    run(broker)
