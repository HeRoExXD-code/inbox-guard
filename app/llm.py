"""Thin wrapper around the class proxy (OpenAI-compatible API)."""
from typing import Callable

from openai import OpenAI

from . import config

ChatFn = Callable[[list[dict]], str]

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()  # reads OPENAI_API_KEY / OPENAI_BASE_URL from the environment
    return _client


def fold_system(messages: list[dict]) -> list[dict]:
    """Merge a leading system message into the first user message."""
    if not messages or messages[0]["role"] != "system":
        return messages
    system, rest = messages[0]["content"], list(messages[1:])
    if rest and rest[0]["role"] == "user":
        rest[0] = {"role": "user", "content": f"{system}\n\n{rest[0]['content']}"}
    else:
        rest.insert(0, {"role": "user", "content": system})
    return rest


def chat(messages: list[dict]) -> str:
    if config.SYSTEM_AS_USER:
        messages = fold_system(messages)
    resp = _get_client().chat.completions.create(
        model=config.MODEL,
        messages=messages,
        temperature=config.TEMPERATURE,
        max_tokens=config.MAX_TOKENS,
    )
    return resp.choices[0].message.content or ""
