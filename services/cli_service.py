"""
CLI Service
-----------
Command-line interface for:
  1. Simulating an image upload (publishes image.submitted)
  2. Submitting a similarity query using a fake embedding (publishes query.submitted)

The CLI must NEVER talk directly to the database — all actions go through the broker.

Usage:
    python -m services.cli_service upload --image-id img_9999 --source camera_A
    python -m services.cli_service query --image-id img_1005 --k 3
"""

import argparse
import json
import time

from broker.redis_broker import RedisBroker
from events.schemas import TOPICS, make_event
from services.embedding_service import generate_fake_embedding


def cmd_upload(broker: RedisBroker, image_id: str, source: str, path: str) -> None:
    """Simulate an image upload by publishing an image.submitted event."""
    event = make_event(
        TOPICS["IMAGE_SUBMITTED"],
        {
            "image_id": image_id,
            "path": path,
            "source": source,
        },
    )
    broker.publish(TOPICS["IMAGE_SUBMITTED"], event)
    print(f"[CLI] Upload event sent for {image_id}")


def cmd_query(broker: RedisBroker, image_id: str, k: int) -> None:
    """
    Submit a similarity query using the embedding of a known image.
    Publishes query.submitted and waits briefly for query.completed.
    """
    query_vector = generate_fake_embedding(image_id)
    query_id = f"query_{image_id}"

    # Subscribe to query.completed before publishing so we don't miss the response
    pubsub = broker.subscribe("query.completed")

    query_event = make_event(
        "query.submitted",
        {
            "query_id": query_id,
            "image_id": image_id,
            "vector": query_vector,
            "k": k,
        },
    )
    broker.publish("query.submitted", query_event)
    print(f"[CLI] Query submitted for image similar to {image_id} (k={k})")

    # Wait for query.completed response (timeout after 5 seconds)
    deadline = time.time() + 5
    for raw in pubsub.listen():
        if time.time() > deadline:
            print("[CLI] Query timed out — is the Vector Index Service running?")
            break
        if raw["type"] == "message":
            response = json.loads(raw["data"])
            results = response["payload"].get("results", [])
            print(f"\n[CLI] Top {len(results)} similar images:")
            for i, r in enumerate(results, 1):
                print(f"  {i}. {r['image_id']}  (distance: {r['distance']})")
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CLI Service for image annotation system")
    subparsers = parser.add_subparsers(dest="command")

    # Upload subcommand
    upload_parser = subparsers.add_parser("upload", help="Simulate an image upload")
    upload_parser.add_argument("--image-id", required=True)
    upload_parser.add_argument("--source", default="camera_A")
    upload_parser.add_argument("--path", default="images/default.jpg")

    # Query subcommand
    query_parser = subparsers.add_parser("query", help="Find similar images")
    query_parser.add_argument("--image-id", required=True, help="Use this image as query")
    query_parser.add_argument("--k", type=int, default=5, help="Number of results")

    args = parser.parse_args()
    broker = RedisBroker()

    if args.command == "upload":
        cmd_upload(broker, args.image_id, args.source, args.path)
    elif args.command == "query":
        cmd_query(broker, args.image_id, args.k)
    else:
        parser.print_help()
