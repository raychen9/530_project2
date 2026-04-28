"""
Simulated Data Generator
------------------------
Generates a realistic dataset of image annotations and embedding vectors.
Saves data to data/annotations.json and data/embeddings.npy for use by services.

Usage:
    python generate_data.py --count 50
"""

import argparse
import json
import os
import random
import numpy as np
from datetime import datetime, timezone

# Reproducible seed
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

# Simulated object labels
LABELS = ["car", "person", "truck", "bicycle", "bus", "traffic light", "motorcycle", "van"]
CAMERAS = ["camera_A", "camera_B", "camera_C", "camera_D"]
EMBEDDING_DIM = 128


def generate_objects(image_id: str) -> list:
    """Generate a variable number of detected objects for an image."""
    random.seed(sum(ord(c) for c in image_id))
    num_objects = random.randint(1, 5)
    objects = []
    for _ in range(num_objects):
        x1 = random.randint(0, 300)
        y1 = random.randint(0, 300)
        objects.append({
            "label": random.choice(LABELS),
            "bbox": [x1, y1, x1 + random.randint(50, 200), y1 + random.randint(50, 200)],
            "conf": round(random.uniform(0.70, 0.99), 2),
        })
    return objects


def generate_embedding(image_id: str) -> list:
    """Generate a deterministic fake embedding vector for an image."""
    seed = sum(ord(c) for c in image_id)
    rng = np.random.default_rng(seed)
    vector = rng.uniform(-1.0, 1.0, EMBEDDING_DIM)
    # L2 normalize so cosine similarity works correctly
    vector = vector / np.linalg.norm(vector)
    return vector.tolist()


def generate_dataset(count: int) -> tuple:
    """
    Generate a full dataset of annotations and embeddings.

    Returns:
        annotations: list of annotation dicts
        embeddings: dict mapping image_id to embedding vector
    """
    annotations = []
    embeddings = {}

    for i in range(count):
        image_id = f"img_{1000 + i}"
        camera = random.choice(CAMERAS)
        objects = generate_objects(image_id)
        embedding = generate_embedding(image_id)

        annotation = {
            "image_id": image_id,
            "camera": camera,
            "path": f"images/street_{1000 + i}.jpg",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "objects": objects,
            "review": {"status": "pending", "notes": []},
            "history": ["submitted", "inference_completed", "annotation_stored"],
        }

        annotations.append(annotation)
        embeddings[image_id] = embedding

    return annotations, embeddings


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate simulated dataset")
    parser.add_argument("--count", type=int, default=50, help="Number of images to generate")
    args = parser.parse_args()

    # Create data directory
    os.makedirs("data", exist_ok=True)

    print(f"[DataGen] Generating {args.count} images ...")
    annotations, embeddings = generate_dataset(args.count)

    # Save annotations as JSON
    annotations_path = "data/annotations.json"
    with open(annotations_path, "w") as f:
        json.dump(annotations, f, indent=2)
    print(f"[DataGen] Saved {len(annotations)} annotations to {annotations_path}")

    # Save embeddings as JSON (for easy inspection)
    embeddings_path = "data/embeddings.json"
    with open(embeddings_path, "w") as f:
        json.dump(embeddings, f, indent=2)
    print(f"[DataGen] Saved {len(embeddings)} embeddings to {embeddings_path}")

    # Save embeddings as numpy array for FAISS
    image_ids = list(embeddings.keys())
    vectors = np.array([embeddings[k] for k in image_ids], dtype=np.float32)
    np.save("data/embeddings.npy", vectors)

    # Save image_id index for FAISS lookup
    with open("data/image_id_index.json", "w") as f:
        json.dump(image_ids, f)
    print(f"[DataGen] Saved FAISS-ready embeddings to data/embeddings.npy")
    print(f"[DataGen] Done. Dataset ready in data/")
