# Event-Driven Image Annotation and Retrieval System

**EC530 — Principles of Software Engineering, Boston University**

An event-driven pipeline for image annotation and similarity search, built with Redis pub/sub, a document store, and a vector embedding layer.

---

## Architecture Overview

```
CLI / Event Generator
        |
        | image.submitted
        v
  [ Image Service ]          — Simulates inference, detects objects
        |
        | inference.completed
        v
  [ Annotation Service ]     — Stores annotation documents
        |
        | annotation.stored
        v
  [ Embedding Service ]      — Generates embedding vectors
        |
        | embedding.created
        v
  [ Vector Index Service ]   — (Week 2) FAISS similarity search
```

All services communicate exclusively through Redis pub/sub topics. No service talks directly to another service's database.

---

## System Components

| Component | File | Responsibility |
|---|---|---|
| Event Generator | `event_generator.py` | Simulates image uploads for testing |
| Broker | `broker/redis_broker.py` | Redis pub/sub wrapper |
| Event Schemas | `events/schemas.py` | Shared event format and validation |
| Image Service | `services/image_service.py` | Handles image.submitted, runs simulated inference |
| Annotation Service | `services/annotation_service.py` | Stores annotation documents, idempotent |
| Embedding Service | `services/embedding_service.py` | Generates embedding vectors per image |
| CLI Service | `services/cli_service.py` | Command-line interface for uploads and queries |

---

## Topics and Message Flow

| Topic | Publisher | Subscriber |
|---|---|---|
| `image.submitted` | CLI / Event Generator | Image Service |
| `inference.completed` | Image Service | Annotation Service |
| `annotation.stored` | Annotation Service | Embedding Service |
| `embedding.created` | Embedding Service | Vector Index Service (Week 2) |
| `annotation.corrected` | CLI Service | Annotation Service |

### Event Schema

Every event follows this standard format:

```json
{
  "type": "publish",
  "topic": "image.submitted",
  "event_id": "evt_fd98862f",
  "timestamp": "2026-04-19T14:33:00Z",
  "payload": {
    "image_id": "img_1042",
    "path": "images/street_1042.jpg",
    "source": "camera_A"
  }
}
```

---

## Design Decisions

### Why Redis pub/sub?
Redis pub/sub provides a lightweight, low-latency messaging layer that works identically across Windows, Mac, and Linux. It removes broker configuration overhead so the focus stays on system architecture.

### Why a document model for annotations?
Each image can contain a variable number of detected objects with nested fields (labels, bounding boxes, confidence scores, reviewer notes). A document model stores these JSON-like records directly and avoids premature normalization. It also accommodates evolving fields over time (corrections, model version updates) without schema migrations.

### Why keep services decoupled?
Each service owns exactly one responsibility and one data store. Services never call each other directly — all coordination happens through events. This makes each service independently testable, replaceable, and scalable.

### Idempotency
The Annotation Service uses `image_id` as the document key. If the same `image_id` arrives twice (e.g. from a duplicate event), the document is updated in place rather than duplicated. This satisfies the idempotency guarantee required by the system.

---

## System Guarantees

| Guarantee | Implementation |
|---|---|
| **Idempotency** | Duplicate events update existing documents rather than creating new ones |
| **Robustness** | `validate_event()` rejects malformed events without crashing the service |
| **Eventual Consistency** | Each stage publishes to the next topic only after its own work is complete |
| **Testability** | All broker interactions use a mockable interface; tests run without a live Redis connection |

---

## Getting Started

### Prerequisites
- Python 3.10+
- A Redis Cloud account (free tier at [redis.io/cloud](https://redis.io/cloud))

### Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd project2

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate      # Windows
source venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Configure Redis credentials
cp .env.example .env
# Edit .env and fill in your REDIS_HOST, REDIS_PORT, REDIS_PASSWORD
```

### Run the pipeline

Open four terminals, activate the virtual environment in each, then:

**Terminal 1 — Image Service**
```bash
python -m services.image_service
```

**Terminal 2 — Annotation Service**
```bash
python -m services.annotation_service
```

**Terminal 3 — Embedding Service**
```bash
python -m services.embedding_service
```

**Terminal 4 — Send test events**
```bash
# Deterministic mode (reproducible)
python event_generator.py --mode deterministic --count 5

# Replay mode (includes a duplicate to test idempotency)
python event_generator.py --mode replay

# CLI upload
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
├── .env                        # Redis credentials (not committed)
├── .env.example                # Template for .env
├── .gitignore
├── requirements.txt
├── event_generator.py          # Simulates image upload events
├── README.md
├── broker/
│   └── redis_broker.py         # Redis pub/sub wrapper
├── events/
│   └── schemas.py              # Event format, validation, topic constants
├── services/
│   ├── image_service.py        # Handles image.submitted
│   ├── annotation_service.py   # Handles inference.completed
│   ├── embedding_service.py    # Handles annotation.stored
│   ├── inference_service.py    # Stub for Week 2
│   └── cli_service.py          # CLI for uploads and queries
└── tests/
    ├── test_schemas.py         # Unit tests for event schemas
    └── test_broker.py          # Unit tests for broker (mocked)
```

---

## Week 2 Plan

- Replace in-memory document store with a real document DB (MongoDB or TinyDB)
- Integrate FAISS for vector similarity search
- Implement the Vector Index Service
- Add query pipeline: `query.submitted` → query worker → `query.completed`
- Add failure injection tests (dropped messages, delayed delivery, subscriber downtime)

---

## Testing Coverage

| Test File | Tests | What is covered |
|---|---|---|
| `test_schemas.py` | 13 | Event creation, field validation, topic definitions |
| `test_broker.py` | 8 | Publish, subscribe, ping — all mocked, no live Redis needed |

**Total: 21 tests, 0 failures**
