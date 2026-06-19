#!/usr/bin/env python3
"""Sponsr Crimson → Obsidian vault (логин email/пароль, Playwright).

Требует /etc/empire/sponsr.env:
  SPONSR_EMAIL, SPONSR_PASSWORD

Пример:
  sudo bash -c 'set -a; source /etc/empire/sponsr.env; set +a; ./venv/bin/python scripts/sponsr_crimson_to_obsidian.py --limit 3'
  ./venv/bin/python scripts/sponsr_crimson_to_obsidian.py   # все посты (~555)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data" / "obsidian_vault" / "База знаний" / "Инвестирование" / "Crimson"
SESSION_PATH = Path(os.environ.get("SPONSR_SESSION", "/etc/empire/sponsr_session.json"))
COOKIES_PATH = Path(
    os.environ.get(
        "SPONSR_COOKIES",
        str(ROOT / "data" / "obsidian_vault" / "Life" / "tools" / "sponsr_cookies.json"),
    )
)
STATE_PATH = ROOT / "data" / "sponsr_crimson_archive_state.json"
AUTH_COOKIE = "SESS"
PROJECT = os.environ.get("SPONSR_PROJECT", "crimsonanalytics").strip()
BASE = "https://sponsr.ru"


def load_env() -> tuple[str, str]:
    email = os.environ.get("SPONSR_EMAIL", "").strip()
    password = os.environ.get("SPONSR_PASSWORD", "").strip()
    if not email or not password:
        print("Задайте SPONSR_EMAIL и SPONSR_PASSWORD в /etc/empire/sponsr.env", file=sys.stderr)
        sys.exit(1)
    return email, password


def slugify(text: str, max_len: int = 70) -> str:
    text = text.lower().strip()
    text = re.sub(r"\[[^\]]+\]", "", text)
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_]+", "-", text).strip("-")
    return (text[:max_len].rstrip("-") or "post")


def parse_next_data(html: str) -> dict:
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        raise ValueError("нет __NEXT_DATA__ на странице")
    return json.loads(m.group(1))


def post_urls_from_html(html: str) -> dict[int, str]:
    out: dict[int, str] = {}
    for m in re.finditer(rf'href="(/{PROJECT}/(\d+)/([^"?#]+)/)"', html):
        path, pid, _slug = m.group(1), int(m.group(2)), m.group(3)
        out[pid] = path
    return out


def html_to_markdown(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()
    parts: list[str] = []

    def walk(el) -> None:
        if el.name in ("h1", "h2", "h3", "h4"):
            level = int(el.name[1])
            parts.append("\n" + "#" * level + " " + el.get_text(" ", strip=True) + "\n")
        elif el.name == "p":
            t = el.get_text(" ", strip=True)
            if t:
                parts.append(t + "\n")
        elif el.name == "blockquote":
            for line in el.get_text("\n", strip=True).splitlines():
                if line.strip():
                    parts.append("> " + line.strip() + "\n")
        elif el.name == "li":
            parts.append("- " + el.get_text(" ", strip=True) + "\n")
        elif el.name == "br":
            parts.append("\n")
        elif el.name == "img":
            alt = el.get("alt") or "image"
            src = el.get("src") or ""
            parts.append(f"![{alt}]({src})\n")
        elif el.name is None:
            return
        else:
            for child in el.children:
                walk(child)

    for child in soup.children:
        walk(child)
    text = "".join(parts)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def download_images(
    client: httpx.Client,
    html: str,
    att_dir: Path,
    stem: str,
) -> tuple[str, list[str]]:
    att_dir.mkdir(parents=True, exist_ok=True)
    soup = BeautifulSoup(html or "", "html.parser")
    saved: list[str] = []
    idx = 0
    for img in soup.find_all("img"):
        src = (img.get("src") or "").strip()
        if not src or src.startswith("data:"):
            continue
        url = urljoin(BASE, src)
        ext = Path(urlparse(url).path).suffix or ".jpg"
        if ext.lower() not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
            ext = ".jpg"
        idx += 1
        fname = f"{stem}_{idx:02d}{ext}"
        dest = att_dir / fname
        if not dest.exists() or dest.stat().st_size < 512:
            try:
                r = client.get(url, timeout=30)
                if r.status_code == 200 and len(r.content) > 256:
                    dest.write_bytes(r.content)
            except httpx.HTTPError:
                continue
        if dest.exists():
            img["src"] = f"attachments/{fname}"
            saved.append(fname)
    return str(soup), saved


def _cookie_paths() -> list[Path]:
    paths: list[Path] = []
    for raw in (
        os.environ.get("SPONSR_COOKIES", ""),
        "/etc/empire/sponsr_cookies.json",
        "/etc/empire/sponsr_sess.txt",
        str(COOKIES_PATH),
        str(COOKIES_PATH.with_name("sponsr_sess.txt")),
    ):
        if not raw:
            continue
        p = Path(raw).expanduser()
        if p.is_file() and p not in paths:
            paths.append(p)
    return paths


def _sess_from_text_file(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("пустой файл SESS")
    if text.upper().startswith("SESS="):
        text = text.split("=", 1)[1].split(";", 1)[0].strip()
    return [
        {
            "name": AUTH_COOKIE,
            "value": text,
            "domain": ".sponsr.ru",
            "path": "/",
            "secure": True,
            "httpOnly": True,
            "sameSite": "Lax",
        }
    ]


def _same_site(raw: str) -> str:
    m = {
        "no_restriction": "None",
        "none": "None",
        "lax": "Lax",
        "strict": "Strict",
        "unspecified": "Lax",
    }
    return m.get((raw or "").lower(), "Lax")


def _load_cookie_editor(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("cookies") or data.get("data") or []
    if not isinstance(data, list):
        raise ValueError(f"неожиданный формат cookies: {path}")
    return [c for c in data if isinstance(c, dict) and c.get("name")]


def _to_playwright_cookies(raw: list[dict]) -> list[dict]:
    out: list[dict] = []
    for c in raw:
        name = str(c.get("name") or "").strip()
        if not name:
            continue
        domain = str(c.get("domain") or ".sponsr.ru").strip()
        if "sponsr.ru" not in domain:
            continue
        item: dict = {
            "name": name,
            "value": str(c.get("value") or ""),
            "domain": domain,
            "path": str(c.get("path") or "/"),
            "httpOnly": bool(c.get("httpOnly")),
            "secure": bool(c.get("secure", True)),
            "sameSite": _same_site(str(c.get("sameSite") or "")),
        }
        exp = c.get("expirationDate")
        if exp is not None and not c.get("session"):
            try:
                item["expires"] = float(exp)
            except (TypeError, ValueError):
                pass
        out.append(item)
    return out


def _cookie_names(raw: list[dict]) -> list[str]:
    return [str(c.get("name") or "") for c in raw if c.get("name")]


def _has_auth_cookie(raw: list[dict]) -> bool:
    return AUTH_COOKIE in _cookie_names(raw)


def import_cookies_to_session(path: Path) -> None:
    if path.suffix.lower() == ".txt":
        raw = _sess_from_text_file(path)
    else:
        raw = _load_cookie_editor(path)
    if not _has_auth_cookie(raw):
        names = ", ".join(_cookie_names(raw)[:12])
        print(
            f"В {path} нет cookie {AUTH_COOKIE} (сессия входа). "
            f"Сейчас только: {names}. "
            "Экспортируйте cookies ПОСЛЕ «Войти» и открытия платной статьи в Chrome.",
            file=sys.stderr,
        )
        sys.exit(1)
    pw = _to_playwright_cookies(raw)
    state = {"cookies": pw, "origins": []}
    SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    SESSION_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        os.chmod(SESSION_PATH, 0o600)
    except OSError:
        pass
    print(f"Сессия из cookies: {SESSION_PATH} ← {path} ({len(pw)} cookies, есть {AUTH_COOKIE})")


def login_and_save_session(email: str, password: str) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()
        page.goto(f"{BASE}/auth/signin/", wait_until="networkidle", timeout=90000)
        page.locator('input[placeholder="Email"]').fill(email)
        page.locator('input[type="password"]').fill(password)
        page.get_by_test_id("submit").click()
        page.wait_for_timeout(5000)
        if "signin" in page.url:
            print(
                "Логин не прошёл (часто Yandex SmartCaptcha на VPS). "
                "Экспортируйте сессию с ПК → /etc/empire/sponsr_session.json "
                "(scripts/sponsr_export_session_pc.ps1)",
                file=sys.stderr,
            )
            browser.close()
            sys.exit(1)
        page.goto(f"{BASE}/{PROJECT}/", wait_until="networkidle", timeout=90000)
        data = parse_next_data(page.content())
        subscribed = data.get("props", {}).get("pageProps", {}).get("subscribed")
        if not subscribed:
            print("Предупреждение: subscribed=false — проверьте логин/подписку", file=sys.stderr)
        SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
        context.storage_state(path=str(SESSION_PATH))
        browser.close()
    try:
        os.chmod(SESSION_PATH, 0o600)
    except OSError:
        pass
    print(f"Сессия сохранена: {SESSION_PATH}")


def ensure_session(email: str, password: str, *, refresh: bool) -> None:
    if SESSION_PATH.is_file() and not refresh:
        return
    if SESSION_PATH.is_file() and refresh:
        SESSION_PATH.unlink(missing_ok=True)
    for path in _cookie_paths():
        import_cookies_to_session(path)
        return
    login_and_save_session(email, password)


def fetch_all_post_meta(page_content_fn) -> list[dict]:
    """Собирает метаданные постов со всех страниц ленты."""
    posts: dict[int, dict] = {}
    page_num = 1
    total_pages = 999
    while page_num <= total_pages:
        html = page_content_fn(f"{BASE}/{PROJECT}/?page={page_num}")
        data = parse_next_data(html)
        block = data["props"]["pageProps"]["posts"]
        total = int(block.get("total") or 0)
        total_pages = max(1, (total + 19) // 20)
        urls = post_urls_from_html(html)
        for item in block.get("list") or []:
            pid = int(item["id"])
            posts[pid] = {
                "id": pid,
                "title": (item.get("title") or "").strip(),
                "date": (item.get("date") or item.get("created_at") or "")[:10],
                "tags": [t.get("tag", {}).get("tag_name") for t in (item.get("tags") or []) if t.get("tag")],
                "url_path": urls.get(pid),
                "list_html": (item.get("text") or {}).get("text") if isinstance(item.get("text"), dict) else None,
            }
        print(f"  лента стр. {page_num}/{total_pages} (+{len(block.get('list') or [])})")
        if page_num >= total_pages:
            break
        page_num += 1
        time.sleep(0.4)
    return sorted(posts.values(), key=lambda x: x["date"], reverse=True)


def extract_post_html(html: str, post_id: int) -> str:
    data = parse_next_data(html)
    post = data["props"]["pageProps"].get("post") or {}
    # полный текст может быть в post.text или отдельном ключе после логина
    for key in ("text", "content", "body"):
        val = post.get(key)
        if isinstance(val, dict) and val.get("text"):
            return val["text"]
        if isinstance(val, str) and len(val) > 100:
            return val
    # иногда текст только в pageProps.text
    val = data["props"]["pageProps"].get("text")
    if isinstance(val, dict) and val.get("text"):
        return val["text"]
    return ""


def write_post_md(
    out_root: Path,
    meta: dict,
    body_html: str,
    client: httpx.Client,
    *,
    force: bool,
) -> Path | None:
    if not body_html or len(body_html) < 80:
        return None
    date = meta.get("date") or "unknown"
    year = date[:4] if len(date) >= 4 else "unknown"
    stem = f"{date}_{slugify(meta.get('title') or str(meta['id']))}"
    year_dir = out_root / year
    att_dir = year_dir / "attachments"
    year_dir.mkdir(parents=True, exist_ok=True)
    out_path = year_dir / f"{stem}.md"
    if out_path.exists() and not force and out_path.stat().st_size > 200:
        return out_path

    body_html, images = download_images(client, body_html, att_dir, stem)
    md_body = html_to_markdown(body_html)
    tags = meta.get("tags") or []
    url = urljoin(BASE, meta["url_path"]) if meta.get("url_path") else ""
    front = [
        "---",
        f"id: crimson-{meta['id']}",
        f"title: {json.dumps(meta.get('title') or stem, ensure_ascii=False)}",
        f"date: {date}",
        "source: sponsr",
        "author: crimson",
        f"tags: {json.dumps(['crimson', 'инвестирование'] + tags, ensure_ascii=False)}",
    ]
    if url:
        front.append(f"url: {url}")
    if images:
        front.append(f"cover: attachments/{images[0]}")
    front.append("---\n")

    out_path.write_text("\n".join(front) + md_body + "\n", encoding="utf-8")
    return out_path


def build_moc(out_root: Path, count: int) -> None:
    lines = [
        "# Crimson (Sponsr) — подборка",
        "",
        f"> Архив: {datetime.now().strftime('%Y-%m-%d')} · постов: {count}",
        "",
        "## По годам",
        "",
    ]
    for year_dir in sorted(out_root.glob("20*")):
        if not year_dir.is_dir():
            continue
        n = len(list(year_dir.glob("*.md")))
        lines.append(f"- **{year_dir.name}** ({n}) — `{year_dir.name}/`")
    lines += ["", "## Теги Sponsr", "", "- Заметки · Философское · Новостной дesk · …", ""]
    (out_root / "_MOC Crimson Sponsr.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Архив Crimson (Sponsr) → Obsidian")
    ap.add_argument("--limit", type=int, default=0, help="Только N постов (тест)")
    ap.add_argument("--force", action="store_true", help="Перезаписать существующие")
    ap.add_argument("--refresh-login", action="store_true", help="Новый логин, обновить сессию")
    ap.add_argument("--out", type=Path, default=Path(os.environ.get("SPONSR_VAULT_CRIMSON", str(DEFAULT_OUT))))
    args = ap.parse_args()

    email, password = load_env()
    ensure_session(email, password, refresh=args.refresh_login)

    out_root = args.out.expanduser().resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=str(SESSION_PATH))
        page = context.new_page()

        def get_html(url: str) -> str:
            page.goto(url, wait_until="networkidle", timeout=90000)
            time.sleep(0.3)
            return page.content()

        print("Сбор списка постов…")
        metas = fetch_all_post_meta(get_html)
        if args.limit:
            metas = metas[: args.limit]
        print(f"К скачиванию: {len(metas)}")

        cookies = {c["name"]: c["value"] for c in context.cookies()}
        client = httpx.Client(
            cookies=cookies,
            headers={"User-Agent": "Mozilla/5.0 Empire/SponsrArchiver"},
            follow_redirects=True,
            timeout=60.0,
        )

        saved = 0
        skipped = 0
        for i, meta in enumerate(metas, 1):
            html = meta.get("list_html") or ""
            if len(html or "") < 80:
                path = meta.get("url_path")
                if not path:
                    skipped += 1
                    continue
                html = extract_post_html(get_html(urljoin(BASE, path)), meta["id"])
            out = write_post_md(out_root, meta, html, client, force=args.force)
            if out:
                saved += 1
                if i % 10 == 0 or i == len(metas):
                    print(f"  [{i}/{len(metas)}] ok={saved} skip={skipped} last={out.name[:50]}")
            else:
                skipped += 1
            time.sleep(0.35)

        browser.close()
        client.close()

    build_moc(out_root, saved)
    STATE_PATH.write_text(
        json.dumps(
            {"updated_at": datetime.now().isoformat(), "saved": saved, "skipped": skipped, "total_listed": len(metas)},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Готово: {saved} статей → {out_root}")
    print("На Яндекс.Диск: sudo bash scripts/obsidian_rclone_push_vault.sh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
