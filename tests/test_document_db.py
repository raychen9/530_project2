"""
Unit tests for the Document DB Service.
Uses a temporary TinyDB instance so tests do not touch the real database.
"""

import os
import pytest
import tempfile
from unittest.mock import MagicMock, patch
from tinydb import TinyDB, Query

from events.schemas import TOPICS, make_event


class TestDocumentDBUpsert:
    def setup_method(self):
        """Create a fresh temporary TinyDB for each test."""
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.db = TinyDB(self.tmp.name)
        self.ImageRecord = Query()

    def teardown_method(self):
        """Remove the temporary database after each test."""
        self.db.close()
        try:
            os.unlink(self.tmp.name)
        except PermissionError:
            pass  # Windows may keep file locked briefly — safe to ignore

    def _upsert(self, document: dict) -> None:
        image_id = document["image_id"]
        self.db.upsert(document, self.ImageRecord.image_id == image_id)

    def test_insert_new_document(self):
        """Inserting a new document must increase the document count."""
        doc = {"image_id": "img_001", "camera": "camera_A", "objects": []}
        self._upsert(doc)
        assert len(self.db) == 1

    def test_upsert_is_idempotent(self):
        """Upserting the same image_id twice must not create a duplicate."""
        doc = {"image_id": "img_001", "camera": "camera_A", "objects": []}
        self._upsert(doc)
        self._upsert(doc)
        assert len(self.db) == 1

    def test_upsert_updates_existing_document(self):
        """Upserting with a changed field must update the existing document."""
        doc = {"image_id": "img_001", "camera": "camera_A", "objects": []}
        self._upsert(doc)
        updated = {"image_id": "img_001", "camera": "camera_B", "objects": []}
        self._upsert(updated)
        result = self.db.search(self.ImageRecord.image_id == "img_001")
        assert result[0]["camera"] == "camera_B"

    def test_multiple_different_images(self):
        """Inserting three different images must result in three documents."""
        for i in range(3):
            self._upsert({"image_id": f"img_00{i}", "camera": "camera_A", "objects": []})
        assert len(self.db) == 3

    def test_retrieve_by_image_id(self):
        """Searching by image_id must return the correct document."""
        doc = {"image_id": "img_999", "camera": "camera_C", "objects": [{"label": "car"}]}
        self._upsert(doc)
        result = self.db.search(self.ImageRecord.image_id == "img_999")
        assert len(result) == 1
        assert result[0]["camera"] == "camera_C"

    def test_missing_image_returns_empty(self):
        """Searching for a non-existent image_id must return an empty list."""
        result = self.db.search(self.ImageRecord.image_id == "img_not_exist")
        assert result == []


class TestDocumentDBServiceHandler:
    def test_handle_valid_inference_completed(self):
        """
        handle_inference_completed must call upsert and publish annotation.stored.
        Uses a temporary DB and mocked broker.
        """
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Patch TinyDB path inside the service
            with patch("services.document_db_service.db", TinyDB(tmp_path)):
                from services.document_db_service import handle_inference_completed
                broker = MagicMock()
                event = make_event(
                    TOPICS["INFERENCE_COMPLETED"],
                    {
                        "image_id": "img_001",
                        "source": "camera_A",
                        "objects": [{"label": "car", "bbox": [0, 0, 100, 100], "conf": 0.9}],
                    },
                )
                handle_inference_completed(broker, event)
                broker.publish.assert_called_once()
                call_topic = broker.publish.call_args[0][0]
                assert call_topic == "annotation.stored"
        finally:
            os.unlink(tmp_path)

    def test_handle_invalid_event_skipped(self):
        """An invalid event must be skipped without calling broker.publish."""
        from services.document_db_service import handle_inference_completed
        broker = MagicMock()
        handle_inference_completed(broker, {"bad": "data"})
        broker.publish.assert_not_called()
