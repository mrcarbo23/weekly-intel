"""Content fingerprinting for deduplication - Layer 1."""
import hashlib
import logging
import pickle
import re
from typing import Optional
from datasketch import MinHash
from simhash import Simhash

logger = logging.getLogger(__name__)

MINHASH_NUM_PERM = 128
SIMILARITY_THRESHOLD = 0.80


def compute_content_hash(text: str) -> str:
    """SHA-256 hash for exact duplicate detection."""
    normalized = _normalize_text(text)
    return hashlib.sha256(normalized.encode()).hexdigest()


def compute_minhash(text: str) -> bytes:
    """MinHash signature for near-duplicate detection."""
    m = MinHash(num_perm=MINHASH_NUM_PERM)
    for shingle in _get_shingles(text):
        m.update(shingle.encode("utf-8"))
    return pickle.dumps(m)


def compute_simhash(text: str) -> str:
    """SimHash fingerprint for fast similarity check."""
    tokens = _normalize_text(text).split()
    return str(Simhash(tokens).value)


def jaccard_similarity(minhash_bytes1: bytes, minhash_bytes2: bytes) -> float:
    """Estimate Jaccard similarity between two MinHash signatures."""
    m1 = pickle.loads(minhash_bytes1)
    m2 = pickle.loads(minhash_bytes2)
    return m1.jaccard(m2)


def simhash_distance(hash1: str, hash2: str) -> int:
    """Hamming distance between two SimHash values (lower = more similar)."""
    try:
        return bin(int(hash1) ^ int(hash2)).count("1")
    except (ValueError, TypeError):
        return 64


def is_near_duplicate(
    new_minhash: bytes,
    existing_minhash: bytes,
    threshold: float = SIMILARITY_THRESHOLD,
) -> bool:
    return jaccard_similarity(new_minhash, existing_minhash) >= threshold


def _normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _get_shingles(text: str, k: int = 5) -> list[str]:
    words = _normalize_text(text).split()
    return [" ".join(words[i:i+k]) for i in range(max(1, len(words) - k + 1))]
