from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path
from typing import Generator

from dotenv import load_dotenv
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from apps.core import documents, memory  # noqa: E402

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)

SESSIONS: dict[str, list[dict]] = {}

FALLBACK_CHAIN: list[str] = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen3-coder:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "google/gemma-4-31b-it:free",
]

TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "browser_search",
            "description": "Search the web using DuckDuckGo. Use for up-to-date info, facts, or any knowledge you are unsure about.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query in natural language."},
                    "max_results": {"type": "integer", "default": 5, "description": "Maximum number of results (1-20)."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_fetch",
            "description": "Fetch a URL and return its plain-text content. Use to read articles or pages found via search.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Absolute URL to fetch."},
                    "max_length": {"type": "integer", "default": 5000, "description": "Max characters to return."},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Evaluate a math expression and return the numeric result. Use this for any arithmetic or scientific computation (LLMs are unreliable at multi-step math).",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Math expression to evaluate. Supports +,-,*,/,**,%, parentheses, and constants/functions: pi,e,tau,inf,nan,sqrt,sin,cos,tan,log,log10,log2,exp,abs,round,ceil,floor,min,max.",
                    }
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current date and time in ISO 8601 format, with optional timezone. Use when the user asks 'what time is it' or 'what's today's date' — LLMs often have wrong or stale dates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "default": "UTC",
                        "description": "IANA timezone name (e.g. 'Africa/Cairo', 'America/New_York', 'UTC').",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "wikipedia_search",
            "description": "Search Wikipedia for articles on a topic. Returns up to 5 matching titles with short snippets. Use for general factual knowledge (history, science, biography, geography). Free, no API key needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Topic to search for in natural language."},
                    "lang": {"type": "string", "default": "en", "description": "Two-letter Wikipedia language code (en, ar, fr, de, es, it, pt, ru, zh, ja, ko)."},
                    "limit": {"type": "integer", "default": 5, "description": "Max results (1-10)."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "wikipedia_summary",
            "description": "Fetch the introductory summary of a specific Wikipedia article by its exact title. Returns a 5-sentence plain-text excerpt.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Exact article title (use wikipedia_search first to find it)."},
                    "lang": {"type": "string", "default": "en", "description": "Wikipedia language code."},
                    "sentences": {"type": "integer", "default": 5, "description": "Number of sentences (1-20)."},
                },
                "required": ["title"],
            },
        },
    },
]


def execute_tool(name: str, args: dict) -> str:
    if name == "browser_search":
        from apps.tools import browser
        results = browser.search(args["query"], args.get("max_results", 5))
        return json.dumps(results, ensure_ascii=False)
    if name == "browser_fetch":
        from apps.tools import browser
        return browser.fetch(args["url"], args.get("max_length", 5000))
    if name == "calculator":
        from apps.tools import calculator
        try:
            value = calculator.safe_eval(args["expression"])
            if isinstance(value, float):
                text = repr(value)
            else:
                text = str(value)
            return json.dumps({"result": text}, ensure_ascii=False)
        except calculator.CalculatorError as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
    if name == "get_current_time":
        from apps.tools import clock
        return json.dumps(clock.now(args.get("timezone", "UTC")), ensure_ascii=False)
    if name == "wikipedia_search":
        from apps.tools import wikipedia
        results = wikipedia.search(
            args["query"],
            lang=args.get("lang", "en"),
            limit=args.get("limit", 5),
        )
        return json.dumps(results, ensure_ascii=False)
    if name == "wikipedia_summary":
        from apps.tools import wikipedia
        result = wikipedia.summary(
            args["title"],
            lang=args.get("lang", "en"),
            sentences=args.get("sentences", 5),
        )
        return json.dumps(result, ensure_ascii=False)
    return json.dumps({"error": f"unknown tool: {name}"})


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
        FALLBACK_CHAIN[0],
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


def _call_model(client: OpenAI, model: str, messages: list[dict], stream: bool, tools: list[dict] | None = None):
    kwargs = {"model": model, "messages": messages, "stream": stream}
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"
    return client.chat.completions.create(**kwargs)


def _resolve_models(model: str | None) -> list[str]:
    if model:
        return [model]
    primary = get_primary_model()
    return [primary] + [m for m in FALLBACK_CHAIN if m != primary]


def chat(sid: str, user_message: str, model: str | None = None) -> str:
    client = get_client()
    messages = get_session(sid)
    messages.append({"role": "user", "content": user_message})
    memory.save_message(sid, "user", user_message)
    last_err: Exception | None = None
    for m in _resolve_models(model):
        try:
            response = _call_model(client, m, messages, stream=False)
            reply = response.choices[0].message.content or ""
            messages.append({"role": "assistant", "content": reply})
            memory.save_message(sid, "assistant", reply)
            return reply
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"all fallback models failed, last error: {last_err}")


def chat_stream(sid: str, user_message: str, model: str | None = None) -> Generator[str, None, None]:
    client = get_client()
    messages = get_session(sid)
    messages.append({"role": "user", "content": user_message})
    memory.save_message(sid, "user", user_message)
    last_err: Exception | None = None
    for m in _resolve_models(model):
        try:
            stream = _call_model(client, m, messages, stream=True)
            full_reply = ""
            for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    full_reply += delta
                    yield delta
            messages.append({"role": "assistant", "content": full_reply})
            memory.save_message(sid, "assistant", full_reply)
            return
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"all fallback models failed, last error: {last_err}")


def chat_with_tools(
    sid: str,
    user_message: str,
    model: str | None = None,
    max_iterations: int = 5,
) -> tuple[str, list[dict]]:
    """LLM-driven tool use. Returns (final_reply, tool_call_log).

    The LLM decides when to call browser_search / browser_fetch. Loop until
    the model returns plain text (no tool_calls), the iteration cap, or all
    fallback models fail.
    """
    client = get_client()
    messages = get_session(sid)
    messages.append({"role": "user", "content": user_message})
    memory.save_message(sid, "user", user_message)

    working = list(messages)
    log: list[dict] = []
    last_err: Exception | None = None

    for model_name in _resolve_models(model):
        try:
            for _ in range(max_iterations):
                response = _call_model(
                    client, model_name, working, stream=False, tools=TOOLS
                )
                msg = response.choices[0].message
                tool_calls = getattr(msg, "tool_calls", None)
                if not tool_calls:
                    reply = msg.content or ""
                    working.append({"role": "assistant", "content": reply})
                    messages.append({"role": "assistant", "content": reply})
                    memory.save_message(sid, "assistant", reply)
                    return reply, log

                assistant_msg = {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in tool_calls
                    ],
                }
                working.append(assistant_msg)
                messages.append(assistant_msg)

                for tc in tool_calls:
                    args = json.loads(tc.function.arguments or "{}")
                    result = execute_tool(tc.function.name, args)
                    tool_msg = {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    }
                    working.append(tool_msg)
                    messages.append(tool_msg)
                    log.append({
                        "tool": tc.function.name,
                        "args": args,
                        "result_excerpt": result[:200],
                    })

            reply = "tool iteration cap reached without final text"
            working.append({"role": "assistant", "content": reply})
            messages.append({"role": "assistant", "content": reply})
            memory.save_message(sid, "assistant", reply)
            return reply, log
        except Exception as e:
            last_err = e
            continue

    raise RuntimeError(f"all fallback models failed, last error: {last_err}")


def chat_with_rag(
    sid: str,
    user_message: str,
    doc_ids: list[int] | None = None,
    model: str | None = None,
    max_iterations: int = 5,
    top_k: int = 3,
) -> tuple[str, list[dict], str]:
    """RAG-augmented chat. Returns (final_reply, tool_log, rag_context_used).

    Searches local documents (LIKE match) before sending to the LLM. If
    relevant chunks exist, prepends them as context. The LLM still has tool
    access for browser_search when external info is needed.
    """
    rag_results = documents.search_chunks(user_message, limit=top_k, doc_ids=doc_ids)
    rag_context = documents.format_rag_context(rag_results)

    augmented = user_message
    if rag_context:
        augmented = (
            "اعتمد على السياق التالي من المستندات المحلية للإجابة. "
            "اذا السياق مش كافي، استخدم browser_search.\n\n"
            f"=== السياق ===\n{rag_context}\n=== نهاية السياق ===\n\n"
            f"سؤال المستخدم: {user_message}"
        )

    reply, tool_log = chat_with_tools(
        sid,
        augmented,
        model=model,
        max_iterations=max_iterations,
    )
    return reply, tool_log, rag_context


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
