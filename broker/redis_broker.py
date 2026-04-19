import json
import os
import redis
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class RedisBroker:
    """
    Wrapper around Redis pub/sub.
    Provides publish and subscribe methods for the event-driven pipeline.
    """

    def __init__(self):
        # Connect to Redis Cloud using credentials from .env
        self.client = redis.Redis(
            host=os.getenv("REDIS_HOST"),
            port=int(os.getenv("REDIS_PORT")),
            password=os.getenv("REDIS_PASSWORD"),
            decode_responses=True,
        )

    def publish(self, topic: str, event: dict) -> None:
        """
        Publish an event to a topic.

        Args:
            topic: The Redis channel name (e.g. "image.submitted")
            event: The event dict created by make_event()
        """
        self.client.publish(topic, json.dumps(event))
        print(f"[Broker] Published to '{topic}': event_id={event.get('event_id')}")

    def subscribe(self, *topics: str):
        """
        Subscribe to one or more topics and return a pubsub listener.

        Args:
            *topics: One or more topic names to subscribe to

        Returns:
            A Redis PubSub object ready to listen for messages
        """
        pubsub = self.client.pubsub()
        for topic in topics:
            pubsub.subscribe(topic)
            print(f"[Broker] Subscribed to '{topic}'")
        return pubsub

    def ping(self) -> bool:
        """
        Test the Redis connection.

        Returns:
            True if connection is alive, False otherwise
        """
        try:
            return self.client.ping()
        except Exception as e:
            print(f"[Broker] Connection failed: {e}")
            return False
