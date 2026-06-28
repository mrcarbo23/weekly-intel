"""Semantic embeddings for clustering - Layer 2."""
import logging
import os
import pickle
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)


def get_embedding(text: str) -> np.ndarray:
    """
    Get embedding vector for text.
    Uses OpenAI if OPENAI_API_KEY is set, otherwise falls back to sentence-transformers.
    """
    if os.environ.get("OPENAI_API_KEY"):
        return _openai_embedding(text)
    return _local_embedding(text)


def _openai_embedding(text: str) -> np.ndarray:
    from openai import OpenAI
    client = OpenAI()
    # Truncate to avoid token limits
    text = text[:8000]
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return np.array(response.data[0].embedding)


def _local_embedding(text: str) -> np.ndarray:
    from sentence_transformers import SentenceTransformer
    model = _get_local_model()
    return model.encode(text, normalize_embeddings=True)


_local_model = None


def _get_local_model():
    global _local_model
    if _local_model is None:
        from sentence_transformers import SentenceTransformer
        _local_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _local_model


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)
    if a_norm == 0 or b_norm == 0:
        return 0.0
    return float(np.dot(a, b) / (a_norm * b_norm))


def serialize_embedding(embedding: np.ndarray) -> bytes:
    return pickle.dumps(embedding)


def deserialize_embedding(data: bytes) -> np.ndarray:
    return pickle.loads(data)
