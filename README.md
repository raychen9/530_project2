# Event-Driven Image Annotation and Retrieval System

**EC530 — Principles of Software Engineering, Boston University**

An event-driven pipeline for image annotation and similarity search, built with Redis pub/sub, TinyDB as the document store, and FAISS for vector similarity search.

---

## Architecture Overview

All services communicate exclusively through Redis pub/sub topics. No service talks directly to another service's database. The pipeline flows as follows:

The CLI or Event Generator publishes an image.submitted event. The Image Service listens for this event, simulates object detection inference, and publishes inference.completed. The Document DB Service listens for inference.completed, stores the annotation document in TinyDB, and publishes annotation.stored. The Embedding Service listens for annotation.stored, generates a 128-dimensional embedding vector for the image, and publishes embedding.created. The Vector Index Service listens for embedding.created and adds the vector to a FAISS index. When the CLI submits a query, the Vector Index Service performs nearest-neighbor search and publishes query.completed with the top-k results.

```
CLI / Event Generator
        |
        | image.submitted
        v
  [ Image Service ]              — Simulates inference, detects objects
        |
        | inference.completed
        v
  [ Document DB Service ]        — Stores annotation documents in TinyDB
        |
        | annotation.stored
        v
  [ Embedding Service ]          — Generates 128-dim embedding vectors
        |
        | embedding.created
        v
  [ Vector Index Service ]       — FAISS nearest-neighbor search
        |
        | query.completed
        v
  [ CLI Service ]                — Displays top-k similar images
```

---

## System Components

**Event Generator** (`event_generator.py`): Simulates image upload events for testing. Supports deterministic mode with a fixed seed for reproducible tests, and replay mode that sends a preset dataset including a deliberate duplicate to verify idempotency.

**Simulated Data Generator** (`generate_data.py`): Generates a realistic dataset of 50 image annotations and 128-dimensional embedding vectors. Saves data to `data/annotations.json`, `data/embeddings.json`, and `data/embeddings.npy` for use by the Vector Index Service on startup.

**Broker** (`broker/redis_broker.py`): A thin wrapper around the Redis client that provides publish and subscribe methods. All services use this broker exclusively — no service imports the Redis client directly. The broker also exposes a ping() method to verify the connection.

**Event Schemas** (`events/schemas.py`): Defines the shared event format used by all services. Every event contains type, topic, event_id, timestamp, and payload. The make_event() function generates events with a unique ID and UTC timestamp. The validate_event() function checks that all required fields are present, allowing services to reject malformed events safely.

**Image Service** (`services/image_service.py`): Subscribes to image.submitted. Simulates object detection by generating random bounding boxes and confidence scores for a set of realistic labels (car, person, truck, bicycle, bus, traffic light). Publishes the result as inference.completed.

**Document DB Service** (`services/document_db_service.py`): Subscribes to inference.completed. Builds a structured annotation document and stores it in TinyDB using image_id as the unique key. This makes the operation idempotent — a duplicate event updates the existing document rather than creating a second one. Publishes annotation.stored.

**Embedding Service** (`services/embedding_service.py`): Subscribes to annotation.stored. Generates a 128-dimensional fake embedding vector seeded from the image_id, so the same image always produces the same vector. Publishes embedding.created with the vector and its dimension.

**Vector Index Service** (`services/vector_index_service.py`): Subscribes to embedding.created and query.submitted. Maintains a FAISS flat L2 index in memory. On startup, loads pre-generated embeddings from disk. New vectors are added incrementally as embedding.created events arrive. On query.submitted, performs nearest-neighbor search and publishes query.completed with the top-k results.

**CLI Service** (`services/cli_service.py`): Provides a command-line interface for uploading images and submitting similarity queries. The CLI publishes events through the broker and never accesses any database directly, satisfying the architecture restriction stated in the assignment.

---

## Topics and Message Flow

| Topic | Publisher | Subscriber |
|---|---|---|
| `image.submitted` | CLI / Event Generator | Image Service |
| `inference.completed` | Image Service | Document DB Service |
| `annotation.stored` | Document DB Service | Embedding Service |
| `embedding.created` | Embedding Service | Vector Index Service |
| `annotation.corrected` | CLI Service | Document DB Service |
| `query.submitted` | CLI Service | Vector Index Service |
| `query.completed` | Vector Index Service | CLI Service |

---

## Event Schema

Every event in the system follows this standard structure:

```json
{
  "type": "publish",
  "topic": "image.submitted",
  "event_id": "evt_fd98862f",
  "timestamp": "2026-04-19T14:33:00+00:00",
  "payload": {
    "image_id": "img_1042",
    "path": "images/street_1042.jpg",
    "source": "camera_A"
  }
}
```

The event_id is a randomly generated hex string prefixed with `evt_`. The timestamp is UTC ISO 8601. The payload is event-specific and varies by topic.

---

## Design Decisions

**Why Redis pub/sub?** Redis pub/sub provides a lightweight, low-latency messaging layer that works identically on Windows, Mac, and Linux with no local installation required when using Redis Cloud. It removes broker configuration overhead so development time can focus on system architecture and testability rather than infrastructure.

**Why TinyDB for the document store?** Each image can contain a variable number of detected objects with nested fields such as labels, bounding boxes, confidence scores, and reviewer notes. A relational schema would require a separate objects table with a foreign key, making the schema rigid and harder to evolve. TinyDB stores JSON documents directly and avoids premature normalization. It also accommodates corrections and model version updates as new fields without requiring schema migrations. TinyDB requires no server installation and stores data as a plain JSON file on disk.

**Why FAISS for vector search?** FAISS (Facebook AI Similarity Search) provides efficient nearest-neighbor search over dense embedding vectors. We use a flat L2 index which performs exact search and is well-suited for datasets up to ~100k vectors. The index is kept in memory for fast query response and pre-populated from generated embeddings on startup.

**Why keep services fully decoupled?** Each service owns exactly one responsibility and one data store. Services never call each other directly — all coordination happens through published events. This design makes each service independently testable with mocks, replaceable without touching other services, and scalable independently if one stage becomes a bottleneck.

**Idempotency design:** The Document DB Service uses image_id as the document key in TinyDB. If the same event is delivered twice — due to network retry, duplicate publish, or replay — the document is simply overwritten with the same data rather than creating a second record.

**Robustness design:** Every service wraps its message handler in a try/except block so that a malformed or unexpected event logs an error and continues running rather than crashing the entire service. The validate_event() function provides a first line of defense by checking required fields before any processing begins.

---

## System Guarantees

| Guarantee | Implementation |
|---|---|
| **Idempotency** | Document DB uses image_id as TinyDB key — duplicate events overwrite, never duplicate |
| **Robustness** | validate_event() rejects malformed events; all handlers wrapped in try/except |
| **Eventual Consistency** | Each stage publishes its output event only after completing its own work |
| **Testability** | All broker interactions use a mockable interface; all 39 tests run without live Redis |

---

## Getting Started

### Prerequisites

- Python 3.10+
- A Redis Cloud account (free tier at [redis.io/cloud](https://redis.io/cloud))

### Setup

```bash
# Clone the repository
git clone https://github.com/raychen9/530_project2.git
cd 530_project2

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate      # Windows
source venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Configure Redis credentials
cp .env.example .env
# Edit .env and fill in your REDIS_HOST, REDIS_PORT, REDIS_PASSWORD

# Generate simulated dataset
python generate_data.py --count 50
```

### Run the full pipeline

Open five terminals, activate the virtual environment in each, then:

```bash
# Terminal 1
python -m services.image_service

# Terminal 2
python -m services.document_db_service

# Terminal 3
python -m services.embedding_service

# Terminal 4
python -m services.vector_index_service

# Terminal 5 — send events
python event_generator.py --mode deterministic --count 5

# Terminal 5 — query for similar images
python -m services.cli_service query --image-id img_1000 --k 5

# Terminal 5 — upload a single image via CLI
python -m services.cli_service upload --image-id img_9999 --source camera_A
```

### Run tests

```bash
pytest tests/ -v
```

---

## Project Structure

```
project2/
├── .env                             # Redis credentials (not committed to git)
├── .env.example                     # Template for .env
├── .gitignore
├── requirements.txt
├── generate_data.py                 # Generates simulated annotations and embeddings
├── event_generator.py               # Simulates image upload events
├── README.md
├── broker/
│   └── redis_broker.py              # Redis pub/sub wrapper
├── events/
│   └── schemas.py                   # Event format, validation, topic constants
├── services/
│   ├── image_service.py             # Subscribes to image.submitted
│   ├── document_db_service.py       # Subscribes to inference.completed, TinyDB
│   ├── embedding_service.py         # Subscribes to annotation.stored
│   ├── vector_index_service.py      # FAISS index, handles query.submitted
│   ├── inference_service.py         # Stub (reserved for future use)
│   └── cli_service.py               # CLI for uploads and similarity queries
└── tests/
    ├── test_schemas.py              # Unit tests for event schemas (13 tests)
    ├── test_broker.py               # Unit tests for broker with mocks (8 tests)
    ├── test_document_db.py          # Unit tests for TinyDB service (8 tests)
    └── test_vector_index.py         # Unit tests for FAISS service (10 tests)
```

---

## Test Coverage

| Test File | Tests | What is covered |
|---|---|---|
| `test_schemas.py` | 13 | Event creation, field validation, unique IDs, topic definitions |
| `test_broker.py` | 8 | Publish, subscribe, ping — all mocked, no live Redis needed |
| `test_document_db.py` | 8 | TinyDB upsert, idempotency, retrieval, invalid event handling |
| `test_vector_index.py` | 10 | FAISS add, search, exact match, empty index, query handler |

**Total: 39 tests, 0 failures.** All tests run without a live Redis connection using mocked clients.