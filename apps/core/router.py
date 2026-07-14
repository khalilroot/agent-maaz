from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path
from typing import Generator

from dotenv import load_dotenv
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from apps.core import memory  # noqa: E402

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)

SESSIONS: dict[str, list[dict]] = {}


def get_client() -> OpenAI:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY missing in .env")
    return OpenAI(
        api_key=api_key,
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    )


def get_primary_model() -> str:
    return os.getenv(
        "AGENT_MAAZ_PRIMARY_MODEL",
        "nvidia/nemotron-3-ultra-550b-a55b:free",
    )


def new_session(system: str | None = None) -> str:
    sid = str(uuid.uuid4())
    SESSIONS[sid] = []
    if system:
        SESSIONS[sid].append({"role": "system", "content": system})
    return sid


def get_session(sid: str) -> list[dict]:
    if sid not in SESSIONS:
        raise KeyError(f"session {sid} not found")
    return SESSIONS[sid]


def chat(sid: str, user_message: str, model: str | None = None) -> str:
    client = get_client()
    messages = get_session(sid)
    messages.append({"role": "user", "content": user_message})
    memory.save_message(sid, "user", user_message)
    response = client.chat.completions.create(
        model=model or get_primary_model(),
        messages=messages,
    )
    reply = response.choices[0].message.content or ""
    messages.append({"role": "assistant", "content": reply})
    memory.save_message(sid, "assistant", reply)
    return reply


def chat_stream(sid: str, user_message: str, model: str | None = None) -> Generator[str, None, None]:
    client = get_client()
    messages = get_session(sid)
    messages.append({"role": "user", "content": user_message})
    memory.save_message(sid, "user", user_message)
    stream = client.chat.completions.create(
        model=model or get_primary_model(),
        messages=messages,
        stream=True,
    )
    full_reply = ""
    for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            full_reply += delta
            yield delta
    messages.append({"role": "assistant", "content": full_reply})
    memory.save_message(sid, "assistant", full_reply)


def reset_session(sid: str) -> None:
    SESSIONS.pop(sid, None)


if __name__ == "__main__":
    print("--- multi-turn + stream test ---")
    sid = new_session(
        system="انت مساعد ذكي اسمه agent-maaz. بترد بالعربي. خلي ردك قصير ومباشر."
    )
    prompts = [
        "اسمي محمود.",
        "ممكن تساعدني بالكود؟",
        "فاكرة اسمي ايه؟",
    ]
    for prompt in prompts:
        print(f"\nUser: {prompt}")
        print("agent-maaz: ", end="", flush=True)
        for chunk in chat_stream(sid, prompt):
            print(chunk, end="", flush=True)
        print()
    session = get_session(sid)
    print(f"\n--- session {sid[:8]} kept {len(session)} messages in history ---")
