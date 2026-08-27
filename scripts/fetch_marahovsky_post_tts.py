#!/usr/bin/env python3
"""Fetch one Marahovsky Sponsr post → TTS MP3 → Telegram."""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from empire_notify import send, send_file  # noqa: E402
from marahovsky_pdf_tts_send import clean_for_speech, slugify, synth  # noqa: E402
from prepare_md_for_tts import prepare_for_tts  # noqa: E402
from sponsr_crimson_to_obsidian import (  # noqa: E402
    BASE,
    SESSION_PATH,
    extract_post_html,
    html_to_markdown,
    load_env,
    login_and_save_session,
)

DEFAULT_OUT = ROOT / "data" / "audio" / "marahovsky"


def fetch_post(post_id: int, out_dir: Path) -> tuple[Path, str]:
    from playwright.sync_api import sync_playwright

    email, password = load_env()
    if not SESSION_PATH.is_file():
        login_and_save_session(email, password)
    url = f"{BASE}/marahovsky/{post_id}/"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=str(SESSION_PATH))
        page = context.new_page()
        page.goto(url, wait_until="networkidle", timeout=120000)
        time.sleep(0.5)
        html = page.content()
        browser.close()

    body = extract_post_html(html, post_id)
    if len(body or "") < 500:
        raise RuntimeError(f"post {post_id}: body too short ({len(body or '')} chars)")
    title = ""
    for line in html.splitlines():
        if "<h1" in line.lower():
            from bs4 import BeautifulSoup

            title = BeautifulSoup(line, "html.parser").get_text(" ", strip=True)
            break
    if not title:
        import re

        m = re.search(r"<title>([^<|]+)", html)
        title = (m.group(1).strip() if m else f"post_{post_id}")
    md = html_to_markdown(body)
    txt = out_dir / f"{slugify(title)}.txt"
    txt.write_text(f"# {title}\n\n{md}\n", encoding="utf-8")
    return txt, title


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("post_id", type=int)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--no-telegram", action="store_true")
    args = ap.parse_args()

    out_dir = args.out_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    txt, title = fetch_post(args.post_id, out_dir)
    slug = slugify(title)
    tts_path = out_dir / f"{slug}_tts.txt"
    mp3_path = out_dir / f"{slug}.mp3"
    cleaned = clean_for_speech(txt.read_text(encoding="utf-8"))
    tts_path.write_text(cleaned, encoding="utf-8")
    print(f"TXT {slug}: clean={len(cleaned)}", flush=True)

    if not args.no_telegram:
        send(f"🎙 Marahovsky: озвучка «{title}»")

    print(f"SYNTH: {title}", flush=True)
    synth(tts_path, mp3_path)

    if args.no_telegram:
        print(f"DONE: {mp3_path}")
        return 0

    size = mp3_path.stat().st_size / 1024 / 1024
    print(f"SEND: {mp3_path.name} ({size:.1f} MB)", flush=True)
    if send_file(mp3_path, caption=f"Мараховский: {title}", as_audio=True):
        send(f"✅ Готово: {title}")
        print("OK telegram", flush=True)
        return 0
    send(f"❌ Не удалось отправить: {title}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
