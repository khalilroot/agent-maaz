from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def test_is_available_returns_false_when_model_missing(monkeypatch):
    """Pretend sentence-transformers isn't importable."""
    import builtins
    real_import = builtins.__import__
    def fake_import(name, *args, **kwargs):
        if name.startswith("sentence_transformers"):
            raise ImportError("simulated absence")
        return real_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", fake_import)
    import importlib
    from apps.core import embeddings
    importlib.reload(embeddings)
    assert embeddings.is_available() is False


def test_encode_fallback_is_deterministic():
    from apps.core import embeddings
    embeddings.reset()
    importlib = __import__("importlib")
    importlib.reload(embeddings)
    a = embeddings.encode("hello world")
    b = embeddings.encode("hello world")
    assert a == b


def test_encode_fallback_dim_is_384():
    from apps.core import embeddings
    vec = embeddings.encode("anything at all", model_id=None)
    assert len(vec) == 384


def test_cosine_similarity_same_input_is_1():
    from apps.core.embeddings import cosine_similarity
    v = [0.3, 0.4, 0.0, 0.1]
    assert abs(cosine_similarity(v, v) - 1.0) < 1e-9


def test_cosine_similarity_orthogonal_is_0():
    from apps.core.embeddings import cosine_similarity
    assert abs(cosine_similarity([1.0, 0.0], [0.0, 1.0])) < 1e-9


def test_cosine_similarity_empty_returns_0():
    from apps.core.embeddings import cosine_similarity
    assert cosine_similarity([], [1.0]) == 0.0
    assert cosine_similarity([1.0], []) == 0.0


def test_rank_sorts_by_score():
    from apps.core.embeddings import rank_by_similarity
    ranked = rank_by_similarity(
        "python programming",
        [
            "cooking pasta with garlic",
            "python decorators tutorial",
            "python snake habitat",
            "weather forecast today",
        ],
        top_k=2,
    )
    assert len(ranked) == 2
    assert all(ranked[i][1] >= ranked[i + 1][1] for i in range(len(ranked) - 1))


def test_encode_batch_returns_matching_length():
    from apps.core.embeddings import encode_batch
    vecs = encode_batch(["a", "b", "c"])
    assert len(vecs) == 3
    for v in vecs:
        assert len(v) == 384


def test_pseudo_vector_deterministic():
    """Hash-based fallback should give same result for same text."""
    from apps.core.embeddings import _pseudo_vector
    a = _pseudo_vector("Egypt capital city")
    b = _pseudo_vector("Egypt capital city")
    assert a == b
    c = _pseudo_vector("Cairo is in Egypt")
    # c is different from a but probably similar (both mention Egypt)
    assert c != a
