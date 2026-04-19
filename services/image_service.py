"""
Image Service
-------------
Subscribes to image.submitted events.
Validates the event and publishes inference.completed to trigger the next stage.

In a real system this would call an ML model.
For this project we simulate inference with a fake result.
"""

import json
import time
import random

from broker.redis_broker import RedisBroker
from events.schemas import TOPICS, make_event, validate_event

# Simulated object detection labels
FAKE_LABELS = ["car", "person", "truck", "bicycle", "bus", "traffic light"]


def simulate_inference(image_id: str) -> list:
    """
    Simulate object detection inference on an image.
    Returns a list of detected objects with bounding boxes and confidence scores.
    """
    num_objects = random.randint(1, 4)
    objects = []
    for _ in range(num_objects):
        objects.append(
            {
                "label": random.choice(FAKE_LABELS),
                "bbox": [
                    random.randint(0, 100),
                    random.randint(0, 100),
                    random.randint(100, 400),
                    random.randint(100, 400),
                ],
                "conf": round(random.uniform(0.70, 0.99), 2),
            }
        )
    return objects


def handle_image_submitted(broker: RedisBroker, message: dict) -> None:
    """
    Handle an image.submitted event.
    Runs simulated inference and publishes inference.completed.
    """
    if not validate_event(message):
        print(f"[ImageService] Invalid event — skipping: {message}")
        return

    payload = message["payload"]
    image_id = payload.get("image_id")
    print(f"[ImageService] Processing image: {image_id}")

    # Simulate inference delay
    time.sleep(0.2)
    detected_objects = simulate_inference(image_id)

    # Publish inference.completed for the annotation service to pick up
    next_event = make_event(
        TOPICS["INFERENCE_COMPLETED"],
        {
            "image_id": image_id,
            "source": payload.get("source"),
            "objects": detected_objects,
        },
    )
    broker.publish(TOPICS["INFERENCE_COMPLETED"], next_event)


def run(broker: RedisBroker) -> None:
    """Start the image service listener."""
    print("[ImageService] Listening on image.submitted ...")
    pubsub = broker.subscribe(TOPICS["IMAGE_SUBMITTED"])

    for raw in pubsub.listen():
        if raw["type"] == "message":
            try:
                event = json.loads(raw["data"])
                handle_image_submitted(broker, event)
            except Exception as e:
                print(f"[ImageService] Error handling message: {e}")


if __name__ == "__main__":
    broker = RedisBroker()
    run(broker)
