from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def test_enabled_by_default(monkeypatch):
    monkeypatch.delenv("RATE_LIMIT_ENABLED", raising=False)
    from apps.api import ratelimit
    ratelimit.configure()
    assert ratelimit.is_enabled() is True


def test_disabled_by_env(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
    from apps.api import ratelimit
    ratelimit.configure()
    assert ratelimit.is_enabled() is False


def test_enabled_truthy(monkeypatch):
    for v in ("1", "true", "yes", "on", "TRUE", "Yes"):
        monkeypatch.setenv("RATE_LIMIT_ENABLED", v)
        from apps.api import ratelimit
        ratelimit.configure()
        assert ratelimit.is_enabled() is True, f"value {v!r} should enable"


def test_disabled_falsy(monkeypatch):
    for v in ("0", "false", "no", "off"):
        monkeypatch.setenv("RATE_LIMIT_ENABLED", v)
        from apps.api import ratelimit
        ratelimit.configure()
        assert ratelimit.is_enabled() is False, f"value {v!r} should disable"


def test_unknown_env_value_defaults_to_enabled(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "definitely-not-a-bool")
    from apps.api import ratelimit
    ratelimit.configure()
    assert ratelimit.is_enabled() is True


def test_limit_default_60(monkeypatch):
    monkeypatch.delenv("RATE_LIMIT_PER_MINUTE", raising=False)
    from apps.api import ratelimit
    ratelimit.configure()
    assert ratelimit.get_limit() == 60


def test_limit_custom(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "10")
    from apps.api import ratelimit
    ratelimit.configure()
    assert ratelimit.get_limit() == 10


def test_limit_invalid_falls_back(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "not-a-number")
    from apps.api import ratelimit
    ratelimit.configure()
    assert ratelimit.get_limit() == 60


def test_limit_minimum_one(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "0")
    from apps.api import ratelimit
    ratelimit.configure()
    assert ratelimit.get_limit() == 1


def test_limit_negative_clamped_to_one(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "-5")
    from apps.api import ratelimit
    ratelimit.configure()
    assert ratelimit.get_limit() == 1


def test_check_allows_under_limit(monkeypatch):
    from apps.api.ratelimit import RateLimiter
    rl = RateLimiter(max_per_minute=3)
    for _ in range(3):
        allowed, count = rl.check("user-1")
        assert allowed is True
    allowed, count = rl.check("user-1")
    assert allowed is False
    assert count == 3


def test_per_key_isolation():
    from apps.api.ratelimit import RateLimiter
    rl = RateLimiter(max_per_minute=2)
    for _ in range(2):
        rl.check("user-1")
    allowed_a, _ = rl.check("user-1")
    allowed_b, _ = rl.check("user-2")
    assert allowed_a is False
    assert allowed_b is True


def test_window_expiry_resets():
    from apps.api.ratelimit import RateLimiter, WINDOW_SECONDS
    rl = RateLimiter(max_per_minute=2)
    rl.check("user-1")
    rl.check("user-1")
    allowed, _ = rl.check("user-1")
    assert allowed is False
    rl._buckets["user-1"].timestamps.clear()
    expired_ts = time.time() - (WINDOW_SECONDS + 5)
    rl._buckets["user-1"].timestamps.append(expired_ts)
    allowed, _ = rl.check("user-1")
    assert allowed is True


def test_reset_clears_buckets():
    from apps.api.ratelimit import RateLimiter
    rl = RateLimiter(max_per_minute=2)
    rl.check("user-1")
    rl.check("user-1")
    rl.reset()
    allowed, _ = rl.check("user-1")
    assert allowed is True


def test_configure_changes_limit():
    from apps.api import ratelimit
    ratelimit.configure_for(100)
    assert ratelimit._limiter.max_per_minute == 100
    ratelimit.configure_for(5)
    assert ratelimit._limiter.max_per_minute == 5


def test_module_check_uses_singleton():
    from apps.api import ratelimit
    ratelimit.configure_for(2)
    ratelimit.reset()
    ratelimit.check("key-1")
    ratelimit.check("key-1")
    allowed, _ = ratelimit.check("key-1")
    assert allowed is False


def test_error_message_shape():
    from apps.api.ratelimit import RateLimiter, error_message, WINDOW_SECONDS
    import apps.api.ratelimit as rl_module
    rl = RateLimiter(max_per_minute=5)
    rl_module._limiter = rl
    msg = error_message(current=5)
    assert msg["detail"] == "rate limit exceeded"
    assert msg["limit_per_minute"] == 5
    assert msg["current_count"] == 5
    assert msg["retry_after_seconds"] == WINDOW_SECONDS
