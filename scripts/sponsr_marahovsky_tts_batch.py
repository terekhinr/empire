#!/usr/bin/env python3
"""Fetch Marahovsky (Sponsr) posts → TTS MP3 → Telegram."""
from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from empire_notify import send, send_file  # noqa: E402
from prepare_md_for_tts import prepare_for_tts  # noqa: E402
from sponsr_crimson_to_obsidian import (  # noqa: E402
    BASE,
    SESSION_PATH,
    _cookie_paths,
    extract_post_html,
    html_to_markdown,
    import_cookies_to_session,
    load_env,
    login_and_save_session,
    parse_next_data,
)

DEFAULT_POSTS: list[tuple[int, str, str]] = [
    (170762, "archimed_2026-07-15", "Архимед XXI века монетизируется на маркетплейсе"),
    (170369, "sportsmen_2026-07-13", "Великий спортсмен выигрывает ничтожный чемпионат галактики"),
    (170246, "depp_2026-07-12", "Богиня Джонни Деппа работает над ошибками хронической правоты"),
    (167813, "motorcycle_2026-06-30", "Взбунтовавшийся муж на мотоцикле ищет лекарство от скуки"),
]


def ensure_session(*, refresh: bool = False) -> None:
    if SESSION_PATH.is_file() and not refresh:
        return
    if SESSION_PATH.is_file() and refresh:
        SESSION_PATH.unlink(missing_ok=True)
    for path in _cookie_paths():
        try:
            import_cookies_to_session(path)
            return
        except SystemExit:
            continue
    email, password = load_env()
    login_and_save_session(email, password)


def fetch_posts(posts: list[tuple[int, str, str]], out_dir: Path) -> list[tuple[Path, str]]:
    from playwright.sync_api import sync_playwright

    ensure_session()
    saved: list[tuple[Path, str]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=str(SESSION_PATH))
        page = context.new_page()
        for pid, slug, label in posts:
            url = f"{BASE}/marahovsky/{pid}/"
            page.goto(url, wait_until="networkidle", timeout=90000)
            time.sleep(0.4)
            html = page.content()
            data = parse_next_data(html)
            post = data["props"]["pageProps"].get("post") or {}
            title = (post.get("title") or label).strip()
            body = extract_post_html(html, pid)
            if len(body or "") < 200:
                print(f"SKIP {pid}: body too short ({len(body or '')})", flush=True)
                continue
            md = html_to_markdown(body)
            txt = out_dir / f"{slug}.txt"
            txt.write_text(f"# {title}\n\n{md}\n", encoding="utf-8")
            saved.append((txt, title))
            print(f"OK {pid}: {len(md)} chars -> {txt}", flush=True)
        browser.close()
    return saved


def synth_mp3(txt: Path, mp3: Path) -> None:
    script = ROOT / "scripts" / "docx_to_mp3_edge.py"
    subprocess.run(
        [
            str(ROOT / "venv" / "bin" / "python3"),
            str(script),
            str(txt),
            "-o",
            str(mp3),
            "--skip-preflight",
        ],
        check=True,
        cwd=str(ROOT / "scripts"),
    )


def deliver(mp3: Path, label: str) -> bool:
    return send_file(mp3, caption=label, as_audio=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, default=ROOT / "data" / "audio" / "marahovsky")
    ap.add_argument("--fetch-only", action="store_true")
    ap.add_argument("--from-local", action="store_true", help="Use existing .txt in out-dir")
    ap.add_argument("--refresh-login", action="store_true")
    ap.add_argument("--no-telegram", action="store_true")
    args = ap.parse_args()

    out_dir = args.out_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.from_local:
        items = []
        for _, slug, label in DEFAULT_POSTS:
            txt = out_dir / f"{slug}.txt"
            if txt.is_file():
                items.append((txt, label))
        if not items:
            print("No local .txt files found", file=sys.stderr)
            return 1
    else:
        if args.refresh_login and SESSION_PATH.is_file():
            SESSION_PATH.unlink(missing_ok=True)
        items = fetch_posts(DEFAULT_POSTS, out_dir)
        if not items:
            send(
                "❌ Marahovsky TTS: не удалось скачать статьи. "
                "Обновите SESS: scripts/sponsr_export_session_pc.ps1 → /etc/empire/sponsr_session.json"
            )
            return 2
        if args.fetch_only:
            return 0

    ok = 0
    for txt, label in items:
        tts_txt = out_dir / f"{txt.stem}_tts.txt"
        raw = txt.read_text(encoding="utf-8")
        cleaned = prepare_for_tts(raw)
        tts_txt.write_text(cleaned, encoding="utf-8")
        mp3 = out_dir / f"{txt.stem}.mp3"
        print(f"Synth: {label}", flush=True)
        synth_mp3(tts_txt, mp3)
        if not args.no_telegram:
            send(f"✅ Озвучка: {label}")
            if deliver(mp3, label):
                ok += 1
            else:
                send(f"❌ Не удалось отправить: {label}")
        else:
            ok += 1

    if not args.no_telegram:
        send(f"Готово: {ok}/{len(items)} MP3 отправлено в бот.")
    return 0 if ok == len(items) else 1


if __name__ == "__main__":
    raise SystemExit(main())
