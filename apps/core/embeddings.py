"""Optional sentence-transformers encoder for semantic document search.

Imports are deferred so the package is only loaded if someone actually wants
embeddings. The fallback (LIKE-based search in apps.core.documents) keeps working
without this module installed.
"""
from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any

_CACHE_DIR = Path.home() / ".cache" / "agent-maaz" / "embeddings"
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EXPECTED_DIM = 384

_model: Any = None
_model_id: str | None = None


def is_available() -> bool:
    """True if sentence-transformers is installed and loadable."""
    try:
        import sentence_transformers  # noqa: F401
        return True
    except ImportError:
        return False


def _get_model(model_id: str = DEFAULT_MODEL) -> Any:
    global _model, _model_id
    if _model is not None and _model_id == model_id:
        return _model
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        raise RuntimeError(
            "sentence-transformers is not installed. "
            "Run: pip install sentence-transformers"
        ) from e
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _model = SentenceTransformer(model_id, cache_folder=str(_CACHE_DIR))
    _model_id = model_id
    return _model


def encode(text: str, model_id: str | None = None) -> list[float]:
    """Encode a text → 384-d vector (cosine-ready). Falls back to a hash-based
    pseudo-vector if sentence-transformers is unavailable, so the search pipeline
    always has something deterministic to compare against."""
    if not text.strip():
        return [0.0] * EXPECTED_DIM
    if not is_available():
        return _pseudo_vector(text)
    model = _get_model(model_id or DEFAULT_MODEL)
    vec = model.encode(text, normalize_embeddings=True)
    return [float(x) for x in vec.tolist()]


def encode_batch(texts: list[str], model_id: str | None = None) -> list[list[float]]:
    if not texts:
        return []
    if not is_available():
        return [_pseudo_vector(t) for t in texts]
    model = _get_model(model_id or DEFAULT_MODEL)
    vecs = model.encode(texts, normalize_embeddings=True)
    return [v.tolist() for v in vecs]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Standard cosine sim; returns 0 if either vector is empty."""
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    da = sum(a[i] * a[i] for i in range(n))
    db = sum(b[i] * b[i] for i in range(n))
    if da == 0.0 or db == 0.0:
        return 0.0
    dot = sum(a[i] * b[i] for i in range(n))
    return dot / (math.sqrt(da) * math.sqrt(db))


def _pseudo_vector(text: str) -> list[float]:
    """Deterministic embedding fallback used when the model isn't installed.

    Hashes words into the vector space. Quality is much worse than a real model,
    but it keeps the API surface testable and gives reproducible results so
    downstream code (cosine sim, ranking) doesn't need special-casing.
    """
    import hashlib

    vec = [0.0] * EXPECTED_DIM
    tokens = text.lower().split()
    for tok in tokens:
        h = hashlib.sha256(tok.encode("utf-8")).digest()
        for i in range(0, len(h), 4):
            j = (h[i] << 24 | h[i + 1] << 16 | h[i + 2] << 8 | h[i + 3]) % EXPECTED_DIM
            vec[j] += 1.0
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def rank_by_similarity(
    query: str,
    candidates: list[str],
    top_k: int | None = None,
) -> list[tuple[int, float]]:
    """Return (index, score) pairs sorted by similarity descending."""
    if not candidates:
        return []
    query_vec = encode(query)
    cand_vecs = encode_batch(candidates)
    scored = [
        (i, cosine_similarity(query_vec, cand_vecs[i]))
        for i in range(len(candidates))
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k] if top_k else scored


def reset() -> None:
    """For tests: drop cached model so a fresh load happens."""
    global _model, _model_id
    _model = None
    _model_id = None
