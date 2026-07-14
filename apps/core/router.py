"""LLM router for agent-maaz.

Uses OpenRouter free tier as primary (verified model: deepseek-chat-v3.1:free).

Verified 2026-07-14: key works, model responds in Arabic, fits within free tier limits.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# Load .env once at module import so every function sees the same authoritative config.
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)


def get_client() -> OpenAI:
    """Build OpenAI-compatible client pointing at OpenRouter."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY missing in .env")
    return OpenAI(
        api_key=api_key,
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    )


def get_primary_model() -> str:
    return os.getenv("AGENT_MAAZ_PRIMARY_MODEL", "deepseek/deepseek-chat-v3.1:free")


def chat(message: str) -> str:
    """Single-turn chat. Returns assistant text."""
    client = get_client()
    response = client.chat.completions.create(
        model=get_primary_model(),
        messages=[{"role": "user", "content": message}],
    )
    return response.choices[0].message.content or ""


if __name__ == "__main__":
    print("--- agent-maaz router smoke test ---")
    print(f"primary model: {get_primary_model()}")
    print("--- sending: قول لي مرحبا بالعربي ---")
    result = chat("قول لي مرحبا بالعربي في جملة واحدة")
    print("--- response ---")
    print(result)
