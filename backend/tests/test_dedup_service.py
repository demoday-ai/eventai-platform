"""Tests for dedup_service."""

import pytest

from app.services.dedup_service import compute_file_hash


def test_compute_file_hash_deterministic():
    content = b"hello world"
    h1 = compute_file_hash(content)
    h2 = compute_file_hash(content)
    assert h1 == h2


def test_compute_file_hash_different_content():
    h1 = compute_file_hash(b"file content A")
    h2 = compute_file_hash(b"file content B")
    assert h1 != h2


def test_compute_file_hash_is_sha256():
    import hashlib
    content = b"test data"
    expected = hashlib.sha256(content).hexdigest()
    assert compute_file_hash(content) == expected


def test_compute_file_hash_empty_bytes():
    h = compute_file_hash(b"")
    assert isinstance(h, str)
    assert len(h) == 64  # SHA-256 hex length


def test_compute_file_hash_large_content():
    content = b"x" * 10_000_000  # 10 MB
    h = compute_file_hash(content)
    assert isinstance(h, str)
    assert len(h) == 64
