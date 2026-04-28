"""
Vector Index Service
--------------------
Subscribes to embedding.created events.
Indexes embedding vectors in FAISS for fast nearest-neighbor search.
Handles query.submitted events and returns top-k similar images.

The FAISS index is kept in memory and rebuilt from data/embeddings.npy on startup.
"""

import json
import os
import numpy as np
import faiss

from broker.redis_broker import RedisBroker
from events.schemas import TOPICS, make_event, validate_event

EMBEDDING_DIM = 128


class VectorIndexService:
    """
    Manages a FAISS flat L2 index for image embedding vectors.
    Supports incremental addition of new vectors and top-k similarity search.
    """

    def __init__(self):
        # Flat L2 index — exact search, suitable for up to ~100k vectors
        self.index = faiss.IndexFlatL2(EMBEDDING_DIM)
        # Maps FAISS integer position -> image_id string
        self.id_map: list = []

        # Load existing embeddings from disk if available
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Load pre-generated embeddings into the FAISS index on startup."""
        embeddings_path = "data/embeddings.npy"
        id_index_path = "data/image_id_index.json"

        if os.path.exists(embeddings_path) and os.path.exists(id_index_path):
            vectors = np.load(embeddings_path).astype(np.float32)
            with open(id_index_path) as f:
                image_ids = json.load(f)

            self.index.add(vectors)
            self.id_map = image_ids
            print(f"[VectorIndex] Loaded {self.index.ntotal} vectors from disk")
        else:
            print("[VectorIndex] No existing embeddings found — starting empty index")

    def add_vector(self, image_id: str, vector: list) -> None:
        """Add a new embedding vector to the FAISS index."""
        vec = np.array([vector], dtype=np.float32)
        self.index.add(vec)
        self.id_map.append(image_id)
        print(f"[VectorIndex] Added vector for {image_id} | total: {self.index.ntotal}")

    def search(self, query_vector: list, k: int = 5) -> list:
        """
        Search for the top-k most similar images to a query vector.

        Args:
            query_vector: The query embedding vector
            k: Number of results to return

        Returns:
            List of dicts with image_id and distance score
        """
        if self.index.ntotal == 0:
            return []

        k = min(k, self.index.ntotal)
        vec = np.array([query_vector], dtype=np.float32)
        distances, indices = self.index.search(vec, k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx >= 0 and idx < len(self.id_map):
                results.append({
                    "image_id": self.id_map[idx],
                    "distance": round(float(dist), 4),
                })
        return results


def handle_embedding_created(service: VectorIndexService, broker: RedisBroker, message: dict) -> None:
    """
    Handle an embedding.created event.
    Adds the new vector to the FAISS index.
    """
    if not validate_event(message):
        print(f"[VectorIndex] Invalid event — skipping: {message}")
        return

    payload = message["payload"]
    image_id = payload.get("image_id")
    vector = payload.get("vector")

    if not vector:
        print(f"[VectorIndex] No vector in payload for {image_id} — skipping")
        return

    service.add_vector(image_id, vector)


def handle_query_submitted(service: VectorIndexService, broker: RedisBroker, message: dict) -> None:
    """
    Handle a query.submitted event.
    Searches the FAISS index and publishes query.completed with results.
    """
    if not validate_event(message):
        print(f"[VectorIndex] Invalid query event — skipping: {message}")
        return

    payload = message["payload"]
    query_id = payload.get("query_id")
    query_vector = payload.get("vector")
    k = payload.get("k", 5)

    if not query_vector:
        print(f"[VectorIndex] No query vector in payload — skipping")
        return

    results = service.search(query_vector, k=k)
    print(f"[VectorIndex] Query {query_id} returned {len(results)} results")

    result_event = make_event(
        "query.completed",
        {
            "query_id": query_id,
            "results": results,
        },
    )
    broker.publish("query.completed", result_event)


def run(broker: RedisBroker) -> None:
    """Start the vector index service listener."""
    service = VectorIndexService()
    print("[VectorIndex] Listening on embedding.created and query.submitted ...")
    pubsub = broker.subscribe(TOPICS["EMBEDDING_CREATED"], "query.submitted")

    for raw in pubsub.listen():
        if raw["type"] == "message":
            try:
                event = json.loads(raw["data"])
                topic = event.get("topic")

                if topic == TOPICS["EMBEDDING_CREATED"]:
                    handle_embedding_created(service, broker, event)
                elif topic == "query.submitted":
                    handle_query_submitted(service, broker, event)
            except Exception as e:
                print(f"[VectorIndex] Error handling message: {e}")


if __name__ == "__main__":
    broker = RedisBroker()
    run(broker)
