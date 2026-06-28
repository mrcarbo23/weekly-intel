import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.processing.fingerprint import (
    compute_content_hash, compute_minhash, jaccard_similarity,
    compute_simhash, simhash_distance, is_near_duplicate
)


def test_exact_hash_identical():
    assert compute_content_hash("hello world") == compute_content_hash("hello world")


def test_exact_hash_different():
    assert compute_content_hash("hello world") != compute_content_hash("goodbye world")


def test_minhash_identical_texts():
    text = "The quick brown fox jumps over the lazy dog " * 5
    m1 = compute_minhash(text)
    m2 = compute_minhash(text)
    sim = jaccard_similarity(m1, m2)
    assert sim > 0.99


def test_minhash_different_texts():
    m1 = compute_minhash("Python is a great programming language " * 5)
    m2 = compute_minhash("JavaScript is used for web development " * 5)
    sim = jaccard_similarity(m1, m2)
    assert sim < 0.5


def test_minhash_near_duplicate():
    base = "OpenAI released a new model called GPT-5 today with significant improvements " * 10
    near_dup = base.replace("today", "this week").replace("significant", "major")
    m1 = compute_minhash(base)
    m2 = compute_minhash(near_dup)
    assert is_near_duplicate(m1, m2, threshold=0.6)


def test_simhash():
    h1 = compute_simhash("The quick brown fox " * 5)
    h2 = compute_simhash("The quick brown fox " * 5)
    assert simhash_distance(h1, h2) == 0
