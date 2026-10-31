"""Генерация картинок для Studio (Gemini flash image) + stub."""

from __future__ import annotations

import base64
import logging
import os
import uuid
from pathlib import Path

import httpx

logger = logging.getLogger("empire.publisher")

ROOT = Path(__file__).resolve().parent.parent
STUB_PATH = ROOT / "media" / "publisher" / "stub.jpg"
GEN_DIR = ROOT / "media" / "publisher" / "generated"


def stub_path() -> Path | None:
    if STUB_PATH.is_file():
        return STUB_PATH
    return None


def _model() -> str:
    return (
        os.getenv("EMPIRE_STUDIO_IMAGE_MODEL")
        or os.getenv("GDEPAR_VENIK_GEMINI_MODEL")
        or "gemini-2.5-flash-image"
    ).strip()


def generate_gemini_image(prompt: str, *, dest: Path | None = None) -> Path | None:
    """Синхронная генерация через Gemini API. None при ошибке."""
    api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if not api_key:
        logger.warning("studio image: no GEMINI_API_KEY")
        return None
    prompt = (prompt or "").strip()
    if not prompt:
        return None
    GEN_DIR.mkdir(parents=True, exist_ok=True)
    out = dest or (GEN_DIR / f"studio_{uuid.uuid4().hex[:12]}.jpg")
    model = _model()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
    payloads = [
        {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"],
                "responseFormat": {"image": {"aspectRatio": "4:3", "imageSize": "1K"}},
            },
        },
        {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["IMAGE"]},
        },
    ]
    try:
        with httpx.Client(timeout=120.0) as client:
            for payload in payloads:
                res = client.post(url, headers=headers, json=payload)
                if res.status_code != 200:
                    logger.warning("studio gemini HTTP %s: %s", res.status_code, (res.text or "")[:200])
                    continue
                data = res.json()
                for cand in data.get("candidates") or []:
                    for part in (cand.get("content") or {}).get("parts") or []:
                        inline = part.get("inlineData") or part.get("inline_data")
                        if not inline or not inline.get("data"):
                            continue
                        raw = base64.b64decode(inline["data"])
                        out.parent.mkdir(parents=True, exist_ok=True)
                        out.write_bytes(raw)
                        return out
    except Exception as exc:
        logger.warning("studio gemini error: %s", type(exc).__name__)
    return None
