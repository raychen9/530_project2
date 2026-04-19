"""
Event Generator
---------------
Simulates the image upload pipeline by publishing events to Redis topics.
Supports deterministic mode (fixed seed) and replay mode (from a dataset).

Usage:
    python event_generator.py --mode deterministic --count 5
    python event_generator.py --mode replay
"""

import argparse
import random
import time

from broker.redis_broker import RedisBroker
from events.schemas import TOPICS, make_event

# Sample image sources for simulation
CAMERAS = ["camera_A", "camera_B", "camera_C"]
IMAGE_PATHS = [f"images/street_{i:04d}.jpg" for i in range(1, 101)]


def generate_image_submitted_event(image_id: str, source: str, path: str) -> dict:
    """Create an image.submitted event payload."""
    return make_event(
        TOPICS["IMAGE_SUBMITTED"],
        {
            "image_id": image_id,
            "path": path,
            "source": source,
        },
    )


def run_deterministic(broker: RedisBroker, seed: int, count: int) -> None:
    """
    Publish a fixed set of events using a random seed.
    Useful for reproducible unit tests and demos.
    """
    random.seed(seed)
    print(f"[Generator] Deterministic mode | seed={seed} | count={count}")

    for i in range(count):
        image_id = f"img_{1000 + i}"
        source = random.choice(CAMERAS)
        path = random.choice(IMAGE_PATHS)
        event = generate_image_submitted_event(image_id, source, path)
        broker.publish(TOPICS["IMAGE_SUBMITTED"], event)
        time.sleep(0.1)  # Small delay between publishes

    print(f"[Generator] Done. Published {count} events.")


def run_replay(broker: RedisBroker) -> None:
    """
    Replay a hardcoded sample dataset of events.
    Simulates a real sequence of image submissions.
    """
    sample_dataset = [
        ("img_2001", "camera_A", "images/street_2001.jpg"),
        ("img_2002", "camera_B", "images/street_2002.jpg"),
        ("img_2003", "camera_A", "images/street_2003.jpg"),
        ("img_2001", "camera_A", "images/street_2001.jpg"),  # Duplicate — tests idempotency
        ("img_2004", "camera_C", "images/street_2004.jpg"),
    ]

    print(f"[Generator] Replay mode | {len(sample_dataset)} events in dataset")

    for image_id, source, path in sample_dataset:
        event = generate_image_submitted_event(image_id, source, path)
        broker.publish(TOPICS["IMAGE_SUBMITTED"], event)
        time.sleep(0.1)

    print("[Generator] Replay complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Event Generator for image pipeline")
    parser.add_argument(
        "--mode",
        choices=["deterministic", "replay"],
        default="deterministic",
        help="Generator mode",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed (deterministic mode)")
    parser.add_argument("--count", type=int, default=5, help="Number of events to generate")
    args = parser.parse_args()

    broker = RedisBroker()

    if not broker.ping():
        print("[Generator] ERROR: Cannot connect to Redis. Check your .env file.")
        exit(1)

    if args.mode == "deterministic":
        run_deterministic(broker, seed=args.seed, count=args.count)
    else:
        run_replay(broker)
