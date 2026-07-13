#!/usr/bin/env python3
"""Текстовые сессии Gemini для Снегири (finmodel, аудит, NPD).

Требует GEMINI_API_KEY в .env или /etc/empire/empire.env.

Примеры:
  ./venv/bin/python scripts/gemini_session.py --check
  ./venv/bin/python scripts/gemini_session.py --session 0
  python3 scripts/gemini_session.py --session A --attach docs/snegiri_product_prelaunch_methodology.md
  python3 scripts/gemini_session.py --prompt-file /tmp/my.txt --out docs/snegiri_gemini_custom.md
"""
from __future__ import annotations

import argparse
import os
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "docs" / "snegiri_gemini_master_sessions.md"

SESSION_MARKERS = {
    "0": "# СЕССИЯ 0",
    "A": "# СЕССИЯ A",
    "B": "# СЕССИЯ B",
    "C": "# СЕССИЯ C",
    "D": "# СЕССИЯ D",
    "E": "# СЕССИЯ E",
    "F": "# СЕССИЯ F",
    "G": "# СЕССИЯ G",
    "H": "# СЕССИЯ H",
    "I": "# СЕССИЯ I",
    "J": "# СЕССИЯ J",
    "K": "# СЕССИЯ K",
    "L": "# СЕССИЯ L",
    "M": "# СЕССИЯ M",
}

DEFAULT_OUT = {
    "0": "docs/snegiri_gemini_session_0_audit.md",
    "A": "docs/snegiri_gemini_session_A_prelaunch.md",
    "B": "docs/snegiri_gemini_session_B_finmodel.md",
}


def load_env() -> None:
    load_dotenv(ROOT / ".env")
    load_dotenv("/etc/empire/empire.env")


def api_key() -> str:
    return (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_AI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
        or ""
    ).strip()


def default_model() -> str:
    return (
        os.getenv("SNEGIRI_GEMINI_TEXT_MODEL")
        or os.getenv("GEMINI_TEXT_MODEL")
        or "gemini-2.5-flash"
    ).strip()


def extract_session_prompt(master_text: str, session_id: str) -> str:
    marker = SESSION_MARKERS.get(session_id.upper())
    if not marker:
        raise SystemExit(f"unknown session: {session_id}")
    start = master_text.find(marker)
    if start < 0:
        raise SystemExit(f"marker not found: {marker}")
    rest = master_text[start + len(marker) :]
    # до следующей СЕССИИ или конца файла
    next_pos = len(rest)
    for sid, m in SESSION_MARKERS.items():
        if sid == session_id.upper():
            continue
        p = rest.find(m)
        if p >= 0:
            next_pos = min(next_pos, p)
    block = rest[:next_pos]
    # вытащить первый fenced ``` block (промпт)
    fence = block.find("```")
    if fence < 0:
        raise SystemExit(f"no ``` prompt in session {session_id}")
    inner = block[fence + 3 :]
    if inner.startswith("\n"):
        inner = inner[1:]
    end = inner.find("```")
    if end < 0:
        raise SystemExit(f"unclosed ``` in session {session_id}")
    return inner[:end].strip()


def read_attachments(paths: list[str]) -> str:
    chunks: list[str] = []
    for raw in paths:
        p = Path(raw)
        if not p.is_file():
            raise SystemExit(f"attachment not found: {p}")
        text = p.read_text(encoding="utf-8")
        chunks.append(f"\n\n---\n# ATTACHMENT: {p.name}\n\n{text}")
    return "".join(chunks)


def call_gemini(
    *,
    api_key: str,
    model: str,
    prompt: str,
    timeout: float = 180.0,
) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 8192,
        },
    }
    with httpx.Client(timeout=timeout) as client:
        res = client.post(url, headers=headers, json=payload)
    if res.status_code != 200:
        hint = ""
        if res.status_code == 429:
            hint = (
                "\n\nQuota 429: free tier лимит. AI Studio → Usage / Rate limit; "
                "подождать сброс или Set up billing. Либо Сессии 0/A вручную в gemini.google.com."
            )
        raise SystemExit(f"Gemini HTTP {res.status_code}: {(res.text or '')[:500]}{hint}")
    data = res.json()
    candidates = data.get("candidates") or []
    if not candidates:
        raise SystemExit(f"empty candidates: {data}")
    parts = (candidates[0].get("content") or {}).get("parts") or []
    texts = [p.get("text", "") for p in parts if p.get("text")]
    if not texts:
        raise SystemExit(f"no text in response: {data}")
    return "\n".join(texts).strip()


def write_output(path: Path, session: str, model: str, prompt: str, answer: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    header = textwrap.dedent(
        f"""\
        # Gemini · Сессия {session} · ответ

        **Дата:** {ts}  
        **Модель:** `{model}`  
        **Источник промпта:** `docs/snegiri_gemini_master_sessions.md`

        ---

        """
    )
    body = f"{header}{answer}\n"
    path.write_text(body, encoding="utf-8")
    print(f"OK: {path} ({len(answer)} chars)")


def main() -> int:
    load_env()
    ap = argparse.ArgumentParser(description="Gemini text session runner for Snegiri")
    ap.add_argument("--check", action="store_true", help="verify API key (no generation)")
    ap.add_argument("--session", help="session id: 0, A, B, … M")
    ap.add_argument("--attach", action="append", default=[], help="extra markdown to append to prompt")
    ap.add_argument("--prompt-file", help="custom prompt file instead of master session")
    ap.add_argument("--out", help="output markdown path")
    ap.add_argument("--model", help=f"override model (default {default_model()})")
    args = ap.parse_args()

    key = api_key()
    if not key:
        print(
            "GEMINI_API_KEY не задан.\n"
            "1. AI Studio → Create API key (или NanoBanana)\n"
            "2. echo 'GEMINI_API_KEY=...' >> /root/projects/empire/.env\n"
            "3. python3 scripts/gemini_session.py --check",
            file=sys.stderr,
        )
        return 1

    model = args.model or default_model()

    if args.check:
        try:
            ans = call_gemini(
                api_key=key,
                model=model,
                prompt="Ответь одной строкой: API OK, модель работает.",
                timeout=60.0,
            )
            print(f"API OK · model={model}\n{ans[:200]}")
            return 0
        except SystemExit as e:
            print(str(e), file=sys.stderr)
            return 1

    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8").strip()
        session = "custom"
        out = Path(args.out or "docs/snegiri_gemini_custom.md")
    elif args.session:
        session = args.session.upper()
        master = MASTER.read_text(encoding="utf-8")
        prompt = extract_session_prompt(master, session)
        if args.attach:
            prompt += read_attachments(args.attach)
        out = Path(args.out or DEFAULT_OUT.get(session, f"docs/snegiri_gemini_session_{session}.md"))
    else:
        ap.print_help()
        return 1

    print(f"Session {session} · model={model} · prompt {len(prompt)} chars …")
    answer = call_gemini(api_key=key, model=model, prompt=prompt)
    write_output(out, session, model, prompt, answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
