"""
CLI Service
-----------
Command-line interface for:
  1. Simulating an image upload (publishes image.submitted)
  2. Querying the system (stub for Week 2)

The CLI must NEVER talk directly to the database — all actions go through the broker.

Usage:
    python -m services.cli_service upload --image-id img_9999 --source camera_A
    python -m services.cli_service query --topic "cars on street"
"""

import argparse

from broker.redis_broker import RedisBroker
from events.schemas import TOPICS, make_event


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


def cmd_query(broker: RedisBroker, topic: str) -> None:
    """
    Submit a natural-language query (stub for Week 2).
    Will publish a query.submitted event to the query worker.
    """
    print(f"[CLI] Query submitted: '{topic}' — query pipeline will be added in Week 2.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CLI Service for image annotation system")
    subparsers = parser.add_subparsers(dest="command")

    # Upload subcommand
    upload_parser = subparsers.add_parser("upload", help="Simulate an image upload")
    upload_parser.add_argument("--image-id", required=True)
    upload_parser.add_argument("--source", default="camera_A")
    upload_parser.add_argument("--path", default="images/default.jpg")

    # Query subcommand
    query_parser = subparsers.add_parser("query", help="Search for images by topic")
    query_parser.add_argument("--topic", required=True)

    args = parser.parse_args()
    broker = RedisBroker()

    if args.command == "upload":
        cmd_upload(broker, args.image_id, args.source, args.path)
    elif args.command == "query":
        cmd_query(broker, args.topic)
    else:
        parser.print_help()
