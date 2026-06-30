"""Утилиты видео-клипов для карточек бань (без импорта main.py)."""

from __future__ import annotations

import json
import re
import urllib.parse


def parse_video_clip(url: str) -> dict | None:
    if not url:
        return None
    url = url.strip()
    try:
        p = urllib.parse.urlparse(url)
    except Exception:
        return None
    host = (p.hostname or "").lower()
    path = p.path or ""
    qs = urllib.parse.parse_qs(p.query or "")

    if host in {"vk.com", "m.vk.com", "vkvideo.ru", "vk.ru"}:
        m = re.search(r"/(?:video|clip)(-?\d+)_(\d+)", path)
        if m:
            oid, vid = m.group(1), m.group(2)
            embed = f"https://vk.com/video_ext.php?oid={oid}&id={vid}&hd=2"
            h = (qs.get("hash") or [""])[0]
            if h:
                embed += f"&hash={h}"
            return {"provider": "vk", "id": f"{oid}_{vid}", "url": url, "embed_url": embed}
        if "video_ext.php" in path:
            oid = (qs.get("oid") or [""])[0]
            vid = (qs.get("id") or [""])[0]
            if oid and vid:
                embed = f"https://vk.com/video_ext.php?oid={oid}&id={vid}&hd=2"
                h = (qs.get("hash") or [""])[0]
                if h:
                    embed += f"&hash={h}"
                return {"provider": "vk", "id": f"{oid}_{vid}", "url": url, "embed_url": embed}

    if host.endswith("rutube.ru"):
        m = re.search(r"/(?:video|shorts|play/embed)/([A-Za-z0-9]+)/?", path)
        if m:
            vid = m.group(1)
            return {
                "provider": "rutube",
                "id": vid,
                "url": url,
                "embed_url": f"https://rutube.ru/play/embed/{vid}/",
            }

    if host in {"youtu.be"}:
        vid = path.lstrip("/").split("/")[0]
        if vid:
            return {
                "provider": "youtube",
                "id": vid,
                "url": url,
                "embed_url": f"https://www.youtube.com/embed/{vid}",
            }
    if "youtube.com" in host:
        vid = (qs.get("v") or [""])[0]
        if not vid:
            m = re.search(r"/(?:shorts|embed)/([A-Za-z0-9_\-]{6,})", path)
            if m:
                vid = m.group(1)
        if vid:
            return {
                "provider": "youtube",
                "id": vid,
                "url": url,
                "embed_url": f"https://www.youtube.com/embed/{vid}",
            }

    if host in {"t.me", "telegram.me"}:
        m = re.match(r"^/([^/]+)/(\d+)/?$", path)
        if m:
            ch, msg = m.group(1), m.group(2)
            return {
                "provider": "telegram",
                "id": f"{ch}/{msg}",
                "url": url,
                "embed_url": f"https://t.me/{ch}/{msg}?embed=1&dark=1",
            }

    if path.lower().endswith((".mp4", ".webm", ".mov", ".m4v")):
        return {"provider": "file", "id": url, "url": url, "embed_url": url}

    return None


def _sanitize_banya_clip_embed_url(raw: object) -> str:
    if not isinstance(raw, str):
        return ""
    s = raw.strip()
    if s.startswith(("https://", "http://")):
        return s
    if s.startswith("/") and not s.startswith("//"):
        return s
    return ""


def normalize_clip_list(raw) -> list[dict]:
    out: list[dict] = []
    if not raw:
        return out
    try:
        data = raw if isinstance(raw, list) else json.loads(raw)
    except Exception:
        return out
    for item in data or []:
        if isinstance(item, dict) and item.get("embed_url"):
            out.append(item)
        elif isinstance(item, str):
            parsed = parse_video_clip(item)
            if parsed:
                out.append(parsed)
            else:
                out.append({"provider": "file", "id": item, "url": item, "embed_url": item})
    for d in out:
        if isinstance(d, dict):
            d["embed_url"] = _sanitize_banya_clip_embed_url(d.get("embed_url"))
    return out
