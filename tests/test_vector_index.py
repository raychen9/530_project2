"""
Unit tests for the Vector Index Service.
Tests FAISS index operations without requiring a live Redis connection.
"""

import numpy as np
import pytest
from unittest.mock import MagicMock

from events.schemas import TOPICS, make_event

EMBEDDING_DIM = 128


def make_random_vector(seed: int = 0) -> list:
    """Generate a normalized random vector for testing."""
    rng = np.random.default_rng(seed)
    v = rng.uniform(-1.0, 1.0, EMBEDDING_DIM).astype(np.float32)
    v = v / np.linalg.norm(v)
    return v.tolist()


class TestVectorIndexService:
    def setup_method(self):
        """Create a fresh VectorIndexService with an empty index for each test."""
        # Patch _load_from_disk so tests start with an empty index
        from services.vector_index_service import VectorIndexService
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(VectorIndexService, "_load_from_disk", lambda self: None)
            self.service = VectorIndexService()

    def test_add_vector_increases_index_size(self):
        """Adding a vector must increase the FAISS index size by 1."""
        self.service.add_vector("img_001", make_random_vector(1))
        assert self.service.index.ntotal == 1

    def test_add_multiple_vectors(self):
        """Adding three vectors must result in index size 3."""
        for i in range(3):
            self.service.add_vector(f"img_00{i}", make_random_vector(i))
        assert self.service.index.ntotal == 3

    def test_search_returns_correct_count(self):
        """search() must return exactly k results when k <= index size."""
        for i in range(10):
            self.service.add_vector(f"img_{i:03d}", make_random_vector(i))
        results = self.service.search(make_random_vector(99), k=3)
        assert len(results) == 3

    def test_search_result_has_required_fields(self):
        """Each search result must contain image_id and distance."""
        self.service.add_vector("img_001", make_random_vector(1))
        results = self.service.search(make_random_vector(2), k=1)
        assert "image_id" in results[0]
        assert "distance" in results[0]

    def test_search_exact_match_is_closest(self):
        """Searching with the exact same vector must return that image as the top result."""
        vec = make_random_vector(42)
        self.service.add_vector("img_exact", vec)
        for i in range(5):
            self.service.add_vector(f"img_other_{i}", make_random_vector(i))
        results = self.service.search(vec, k=1)
        assert results[0]["image_id"] == "img_exact"
        assert results[0]["distance"] < 1e-4  # Near-zero distance for exact match

    def test_search_empty_index_returns_empty(self):
        """Searching an empty index must return an empty list without raising."""
        results = self.service.search(make_random_vector(0), k=5)
        assert results == []

    def test_search_k_larger_than_index(self):
        """Requesting k > index size must return all available results."""
        self.service.add_vector("img_001", make_random_vector(1))
        results = self.service.search(make_random_vector(2), k=10)
        assert len(results) == 1


class TestVectorIndexHandlers:
    def setup_method(self):
        from services.vector_index_service import VectorIndexService
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(VectorIndexService, "_load_from_disk", lambda self: None)
            self.service = VectorIndexService()
        self.broker = MagicMock()

    def test_handle_embedding_created_adds_to_index(self):
        """handle_embedding_created must add the vector to the index."""
        from services.vector_index_service import handle_embedding_created
        event = make_event(
            TOPICS["EMBEDDING_CREATED"],
            {"image_id": "img_001", "vector": make_random_vector(1), "dim": EMBEDDING_DIM},
        )
        handle_embedding_created(self.service, self.broker, event)
        assert self.service.index.ntotal == 1

    def test_handle_invalid_embedding_event_skipped(self):
        """An invalid embedding event must be skipped without modifying the index."""
        from services.vector_index_service import handle_embedding_created
        handle_embedding_created(self.service, self.broker, {"bad": "data"})
        assert self.service.index.ntotal == 0

    def test_handle_query_submitted_publishes_result(self):
        """handle_query_submitted must publish a query.completed event."""
        from services.vector_index_service import handle_query_submitted
        self.service.add_vector("img_001", make_random_vector(1))
        event = make_event(
            "query.submitted",
            {"query_id": "q_001", "vector": make_random_vector(1), "k": 1},
        )
        handle_query_submitted(self.service, self.broker, event)
        self.broker.publish.assert_called_once()
        call_topic = self.broker.publish.call_args[0][0]
        assert call_topic == "query.completed"
