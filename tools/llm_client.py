"""Unified LLM client: direct provider APIs + OpenRouter fallback.

OpenRouter часто отдаёт 403 ToS на GPT/Claude/Gemini (ограничение аккаунта/региона).
Прямые ключи провайдеров обходят OpenRouter для frontier-моделей.

Env:
  OPENROUTER_API_KEY   — open-weight и запасной маршрут
  OPENAI_API_KEY       — platform.openai.com
  ANTHROPIC_API_KEY    — console.anthropic.com
  GEMINI_API_KEY       — aistudio.google.com (или GOOGLE_AI_API_KEY)
  DEEPSEEK_API_KEY     — platform.deepseek.com
  LLM_HTTP_PROXY       — опционально, для прямых API через residential proxy
"""
from __future__ import annotations

import json
import os
from typing import Any

import httpx

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Модели OpenRouter, которые стабильно работают с VPS (июль 2026)
OPENROUTER_WORKING_DEFAULTS = (
    "qwen/qwen3-235b-a22b",
    "deepseek/deepseek-v3.2",
    "deepseek/deepseek-chat",
    "mistralai/mistral-small-3.1-24b-instruct",
)

JUDGE_FALLBACK_CHAIN = (
    "openai/gpt-4o",
    "anthropic/claude-sonnet-4",
    "google/gemini-2.5-flash",
    *OPENROUTER_WORKING_DEFAULTS,
)


def _proxy() -> str | None:
    return (os.getenv("LLM_HTTP_PROXY") or os.getenv("HTTPS_PROXY") or "").strip() or None


def _or_key() -> str:
    return os.getenv("OPENROUTER_API_KEY", "").strip()


def _gemini_key() -> str:
    return (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_AI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
        or ""
    ).strip()


def _err_msg(data: dict | Any) -> str:
    if isinstance(data, dict):
        err = data.get("error")
        if isinstance(err, dict):
            return str(err.get("message") or err.get("code") or err)
        if err:
            return str(err)
    return str(data or "unknown error")


def _normalize_openrouter_model(model: str) -> str:
    m = model.strip()
    if "/" in m:
        return m
    if m.startswith("gpt-") or m.startswith("o"):
        return f"openai/{m}"
    if m.startswith("claude-"):
        return f"anthropic/{m}"
    if m.startswith("gemini-"):
        return f"google/{m}"
    if m.startswith("deepseek-"):
        return f"deepseek/{m}"
    return m


def _openrouter_model_id(model: str) -> str:
    """OpenRouter slug; gemini-2.0-* часто сняты — подменяем на актуальные."""
    m = _normalize_openrouter_model(model)
    replacements = {
        "google/gemini-2.0-flash": "google/gemini-2.5-flash",
        "google/gemini-2.0-flash-001": "google/gemini-2.5-flash",
        "anthropic/claude-3.5-haiku": "anthropic/claude-sonnet-4",
        "anthropic/claude-3.7-sonnet": "anthropic/claude-sonnet-4",
    }
    return replacements.get(m, m)


def _gemini_model_id(model: str) -> str:
    m = model.split("/", 1)[-1] if "/" in model else model
    if m.startswith("gemini-"):
        return m
    return "gemini-2.0-flash"


async def _chat_openai_direct(
    model: str,
    user_prompt: str,
    *,
    system_prompt: str | None,
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> tuple[int, str, dict]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return 0, "", {"error": "OPENAI_API_KEY не задан"}
    model_id = model.split("/", 1)[-1] if model.startswith("openai/") else model
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    async with httpx.AsyncClient(proxy=_proxy()) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model_id,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=timeout,
        )
    return _parse_openai_style(resp)


async def _chat_anthropic_direct(
    model: str,
    user_prompt: str,
    *,
    system_prompt: str | None,
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> tuple[int, str, dict]:
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return 0, "", {"error": "ANTHROPIC_API_KEY не задан"}
    model_id = model.split("/", 1)[-1] if model.startswith("anthropic/") else model
    payload: dict[str, Any] = {
        "model": model_id,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    if system_prompt:
        payload["system"] = system_prompt
    async with httpx.AsyncClient(proxy=_proxy()) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=timeout,
        )
    body = (resp.text or "").strip()
    try:
        data = json.loads(body) if body else {}
    except json.JSONDecodeError:
        return resp.status_code, body, {"error": "не JSON"}
    if resp.status_code != 200:
        return resp.status_code, body, {"error": data.get("error", data)}
    parts = data.get("content") or []
    text = "".join(p.get("text", "") for p in parts if isinstance(p, dict) and p.get("type") == "text")
    return resp.status_code, text, data


async def _chat_gemini_direct(
    model: str,
    user_prompt: str,
    *,
    system_prompt: str | None,
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> tuple[int, str, dict]:
    api_key = _gemini_key()
    if not api_key:
        return 0, "", {"error": "GEMINI_API_KEY не задан"}
    model_id = _gemini_model_id(model)
    parts = [{"text": user_prompt}]
    payload: dict[str, Any] = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
    }
    if system_prompt:
        payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent"
    async with httpx.AsyncClient(proxy=_proxy()) as client:
        resp = await client.post(
            url,
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=timeout,
        )
    body = (resp.text or "").strip()
    try:
        data = json.loads(body) if body else {}
    except json.JSONDecodeError:
        return resp.status_code, body, {"error": "не JSON"}
    if resp.status_code != 200:
        return resp.status_code, body, {"error": data.get("error", data)}
    candidates = data.get("candidates") or []
    if not candidates:
        return resp.status_code, body, {"error": "empty candidates"}
    resp_parts = (candidates[0].get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in resp_parts if p.get("text"))
    return resp.status_code, text, data


async def _chat_deepseek_direct(
    model: str,
    user_prompt: str,
    *,
    system_prompt: str | None,
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> tuple[int, str, dict]:
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        return 0, "", {"error": "DEEPSEEK_API_KEY не задан"}
    model_id = model.split("/", 1)[-1] if model.startswith("deepseek/") else model
    if model_id == "deepseek-chat":
        model_id = "deepseek-chat"
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    async with httpx.AsyncClient(proxy=_proxy()) as client:
        resp = await client.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model_id,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=timeout,
        )
    return _parse_openai_style(resp)


def _parse_openai_style(resp: httpx.Response) -> tuple[int, str, dict]:
    body = (resp.text or "").strip()
    if not body:
        return resp.status_code, "", {"error": "пустой ответ"}
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        return resp.status_code, body, {"error": f"не JSON: {e}"}
    if resp.status_code != 200:
        return resp.status_code, body, {"error": data.get("error", data)}
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return resp.status_code, body, {"error": "нет choices[0].message.content"}
    return resp.status_code, content or "", data


async def openrouter_chat(
    model: str,
    user_prompt: str,
    *,
    system_prompt: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 4096,
    timeout: float = 120.0,
    referer: str = "https://neverretire.ru/",
    title: str = "Empire",
) -> tuple[int, str, dict]:
    api_key = _or_key()
    if not api_key:
        return 0, "", {"error": "OPENROUTER_API_KEY не задан"}

    requested = _normalize_openrouter_model(model)
    model = _openrouter_model_id(requested)
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": referer,
        "X-Title": title,
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "provider": {"data_collection": "allow", "allow_fallbacks": True},
    }

    async with httpx.AsyncClient(proxy=_proxy()) as client:
        resp = await client.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=timeout,
        )
    status, content, data = _parse_openai_style(resp)
    if status != 200:
        err = data.get("error") if isinstance(data, dict) else data
        return status, resp.text, {"error": err, "backend": "openrouter", "model": model}
    if isinstance(data, dict):
        data["backend"] = "openrouter"
        data["model"] = model
    return status, content, data


def _direct_routes(model: str) -> list[str]:
    m = _normalize_openrouter_model(model)
    family = m.split("/", 1)[0] if "/" in m else m
    routes: list[str] = []
    if family == "openai" or m.startswith("gpt-") or m.startswith("o"):
        routes.append("openai")
    if family == "anthropic" or m.startswith("claude-"):
        routes.append("anthropic")
    if family == "google" or m.startswith("gemini-"):
        routes.append("gemini")
    if family == "deepseek" or m.startswith("deepseek-"):
        routes.append("deepseek")
    routes.append("openrouter")
    return routes


async def chat(
    model: str,
    user_prompt: str,
    *,
    system_prompt: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 4096,
    timeout: float = 120.0,
    prefer_direct: bool = True,
) -> tuple[int, str, dict]:
    """Chat with auto-routing: direct provider API first, then OpenRouter."""
    model = _normalize_openrouter_model(model)
    routes = _direct_routes(model) if prefer_direct else ["openrouter"]
    last: tuple[int, str, dict] = (0, "", {"error": "no route"})

    dispatch = {
        "openai": _chat_openai_direct,
        "anthropic": _chat_anthropic_direct,
        "gemini": _chat_gemini_direct,
        "deepseek": _chat_deepseek_direct,
    }

    for route in routes:
        if route == "openrouter":
            status, content, data = await openrouter_chat(
                model,
                user_prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
        else:
            fn = dispatch[route]
            status, content, data = await fn(
                model,
                user_prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            if status == 0:
                continue
            if isinstance(data, dict):
                data.setdefault("backend", route)

        last = (status, content, data if isinstance(data, dict) else {"raw": data})
        if status == 200 and (content or "").strip():
            return last

    return last


async def chat_with_fallback(
    models: list[str],
    user_prompt: str,
    *,
    system_prompt: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 4096,
    timeout: float = 120.0,
) -> tuple[str, str, dict]:
    """Try models in order. Returns (model_used, content, data)."""
    last_model = models[-1] if models else ""
    last_data: dict = {"error": "all models failed"}
    last_content = ""
    for model in models:
        status, content, data = await chat(
            model,
            user_prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        last_model, last_content, last_data = model, content, data if isinstance(data, dict) else {"raw": data}
        if status == 200 and (content or "").strip():
            return model, content.strip(), last_data
    return last_model, last_content, last_data
