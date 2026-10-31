#!/usr/bin/env python3
"""Скрапинг Яндекс.Карт через headless Chromium (Playwright).

Два режима работы:

  enrich  — для бани, у которой нет yandex_url, делаем поиск
            "name + city" в yandex.ru/maps и подбираем подходящую карточку
            (по близости к lat/lon); из неё забираем yandex_url, телефон, рейтинг.
            По умолчанию только quality-регионы (MSK/MO/SPB/LO, аудит R7).
            Низкий reviews_total / рейтинг → статус draft.

  reviews — для бани с yandex_url открываем вкладку «Отзывы»
            и снимаем N последних отзывов (автор, рейтинг, дата, текст).
            Пишем в banya_reviews со status='pending', дедуп по стабильному
            source_id (sha1 текста) и по паре баня+текст.
            Только свежие отзывы (BANYA_REVIEW_MAX_AGE_DAYS) и точки с
            reviews_total >= BANYA_MIN_REVIEWS.

  daily   — ночной лимитированный прогон + quality gate (demote).
            Лимиты: env BANYA_DAILY_*; пороги: BANYA_MIN_REVIEWS / BANYA_MIN_RATING.

Запуск:
    python tools/parsers/yandex_scrape.py enrich  --id 12
    python tools/parsers/yandex_scrape.py enrich  --region MO --limit 30
    python tools/parsers/yandex_scrape.py reviews --id 12 --max 10
    python tools/parsers/yandex_scrape.py reviews --status published --max 10
    python tools/parsers/yandex_scrape.py daily
    python tools/parsers/yandex_scrape.py daily --dry
    python tools/parsers/yandex_scrape.py refresh --region MO --limit 80 --need-reviews
    python tools/banya_quality.py --show|--apply
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "empire.db"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.banya_review_dedupe import stable_review_source_id
from tools.banya_quality import (
    flagship_region_sql,
    min_reviews,
    parse_review_date,
    quality_regions,
    review_is_fresh,
    title_is_sauna_only,
    traffic_ok,
)


def _load_dotenv() -> None:
    """Подхватываем ROOT/.env до чтения os.environ (cron/systemd без export)."""
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except Exception:
        pass

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)

# Сколько секунд ждём на каждом этапе.
NAV_TIMEOUT = 30_000     # переход по URL
WAIT_SETTLE = 3.0        # на «дорендер» страницы Я.Карт
WAIT_PER_REQ = 4.0       # пауза между разными банями
MAX_DISTANCE_KM = 1.5    # максимально допустимое расхождение точки и кандидата


def _refresh_cooldown_s() -> float:
    """Пауза между refresh-запросами (анти-CAPTCHA): uniform в [min, max] сек."""
    lo = float(os.environ.get("BANYA_REFRESH_WAIT_MIN", "8"))
    hi = float(os.environ.get("BANYA_REFRESH_WAIT_MAX", "15"))
    if hi < lo:
        lo, hi = hi, lo
    return random.uniform(lo, hi)


def _refresh_cooldown_avg_s() -> float:
    lo = float(os.environ.get("BANYA_REFRESH_WAIT_MIN", "8"))
    hi = float(os.environ.get("BANYA_REFRESH_WAIT_MAX", "15"))
    if hi < lo:
        lo, hi = hi, lo
    return (lo + hi) / 2.0

# ─── вспомогательное ────────────────────────────────────────────────────────


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _to_float(s) -> float | None:
    try:
        return float(s)
    except Exception:
        return None


def _open_db() -> sqlite3.Connection:
    con = sqlite3.connect(str(DB_PATH))
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=30000")
    return con


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


def _parse_sqlite_dt(val) -> datetime | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s[:26], fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00").split("+")[0])
    except ValueError:
        return None


def _select_review_candidates(
    con: sqlite3.Connection, limit: int, refresh_days: int
) -> list[tuple]:
    """Published в quality-регионах с трафиком: без отзывов или fetch старше refresh_days.

    Сортировка: больше reviews_total на Яндексе → раньше (R7: живые бани).
    """
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=refresh_days)
    min_rev = min_reviews()
    reg_sql = flagship_region_sql("region")
    pub = con.execute(
        "SELECT id, slug, title, city, yandex_url, region, "
        "COALESCE(reviews_total, 0) AS rt, rating_avg FROM banya_spots "
        f"WHERE status = 'published' "
        f"AND {reg_sql} "
        "AND yandex_url IS NOT NULL AND TRIM(yandex_url) != '' "
        "AND COALESCE(reviews_total, 0) >= ? "
        "ORDER BY COALESCE(reviews_total, 0) DESC, id",
        (min_rev,),
    ).fetchall()
    out: list[tuple] = []
    for row in pub:
        sid = row[0]
        title = row[2]
        if title_is_sauna_only(title):
            continue
        if not traffic_ok(row[6], row[7]):
            continue
        mx = con.execute(
            "SELECT MAX(fetched_at) FROM banya_reviews "
            "WHERE spot_id = ? AND source = 'yandex'",
            (sid,),
        ).fetchone()[0]
        need = False
        if mx is None:
            need = True
        else:
            dt = _parse_sqlite_dt(mx)
            need = dt is None or dt < cutoff
        if need:
            out.append(row[:5])
        if len(out) >= limit:
            break
    return out

# ─── запуск Playwright ───────────────────────────────────────────────────────


def _new_browser(p):
    # Ubuntu 26.04+ не в списке Playwright — fallback через override.
    os.environ.setdefault("PLAYWRIGHT_HOST_PLATFORM_OVERRIDE", "ubuntu24.04-x64")
    return p.chromium.launch(
        headless=True,
        args=["--disable-blink-features=AutomationControlled"],
    )


def _new_context(browser):
    return browser.new_context(
        user_agent=UA,
        viewport={"width": 1366, "height": 900},
        locale="ru-RU",
        timezone_id="Europe/Moscow",
        extra_http_headers={
            "Accept-Language": "ru,en;q=0.7",
        },
    )


def _is_captcha(page) -> bool:
    try:
        html = page.content()
    except Exception:
        return False
    return ("showcaptcha" in html or "smartcaptcha" in html) and "yandex" in html.lower()


# ─── enrich: поиск карточки и извлечение метаданных ──────────────────────────


def enrich_one(page, spot: dict) -> dict | None:
    """spot: {'title','city','lat','lon', 'existing_url'?}.

    Если задан 'existing_url' — открываем сразу его и обновляем поля
    (refresh-режим), без text-search. Иначе — обычный поиск.
    Возвращает dict с обогащением или None.
    """
    existing_url = (spot.get("existing_url") or "").strip()
    org_url = None
    if existing_url:
        try:
            page.goto(existing_url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
            time.sleep(WAIT_SETTLE)
            if _is_captcha(page):
                print("  ! CAPTCHA", file=sys.stderr)
                return None
            if "/maps/org/" in page.url:
                org_url = page.url.split("?")[0]
        except Exception as e:
            print(f"  ! goto existing fail: {e}", file=sys.stderr)
    if not org_url:
        q = " ".join(filter(None, [spot.get("title"), spot.get("city")])).strip()
        if not q:
            return None
        url = f"https://yandex.ru/maps/?text={q}".replace(" ", "+")
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
        except Exception as e:
            print(f"  ! goto fail: {e}", file=sys.stderr)
            return None
        time.sleep(WAIT_SETTLE)
        if _is_captcha(page):
            print("  ! CAPTCHA", file=sys.stderr)
            return None

        cur_url = page.url
        if "/maps/org/" in cur_url:
            org_url = cur_url.split("?")[0]
        else:
            try:
                link = page.locator(
                    "a[href*='/maps/org/'], a[href*='maps.yandex.ru/org']"
                ).first
                href = link.get_attribute("href", timeout=3000)
                if href:
                    if href.startswith("/"):
                        href = "https://yandex.ru" + href
                    page.goto(href.split("?")[0], wait_until="domcontentloaded",
                              timeout=NAV_TIMEOUT)
                    time.sleep(WAIT_SETTLE)
                    org_url = page.url.split("?")[0]
            except Exception:
                pass

    if not org_url:
        return None

    out = {"yandex_url": org_url}

    # Телефон: на странице организации есть кнопка «Показать номер»; в DOM лежит
    # как `a[href^="tel:"]` после клика. Иногда сразу видим. Пробуем оба варианта.
    try:
        phone_text = None
        # Сначала пробуем <a href="tel:..."> — это всегда чистая ссылка из карточки.
        for el in page.locator("a[href^='tel:']").all():
            href = el.get_attribute("href") or ""
            num = href[4:].strip()
            if num:
                phone_text = num
                break
        # Иначе текст из card-phones-view (только из карточки организации, не из выдачи).
        if not phone_text:
            for el in page.locator("div[class*='card-phones-view']").all():
                txt = (el.text_content() or "").strip()
                if re.search(r"\d", txt):
                    phone_text = txt
                    break
        if phone_text:
            # Чистим типовой мусор из подсказок Яндекса.
            phone_text = re.sub(r"Показать(\s+\w+)?", "", phone_text, flags=re.IGNORECASE)
            digits = re.sub(r"\D", "", phone_text)
            if digits.startswith("8") and len(digits) == 11:
                digits = "7" + digits[1:]
            # Принимаем ТОЛЬКО российские +7XXXXXXXXXX, чтобы не записывать +375/+380.
            if len(digits) == 11 and digits.startswith("7"):
                out["phone"] = f"+7 {digits[1:4]} {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"
            # иначе телефон не записываем — пусть лучше пусто, чем мусор.
    except Exception:
        pass

    # Рейтинг: ищем pattern "4.6" в специфичном aria-label / meta itemprop.
    try:
        meta = page.locator("meta[itemprop='ratingValue']").first
        rating = meta.get_attribute("content", timeout=2000)
        if rating:
            out["rating_avg"] = rating
    except Exception:
        pass
    if "rating_avg" not in out:
        try:
            txt = page.locator(
                "span[class*='business-rating-badge-view__rating-text']"
            ).first.text_content(timeout=2000)
            if txt:
                m = re.search(r"([0-5][.,]\d)", txt)
                if m:
                    out["rating_avg"] = m.group(1).replace(",", ".")
        except Exception:
            pass

    # Количество отзывов: meta itemprop=reviewCount → fallback на видимый текст «N оценок».
    try:
        meta = page.locator("meta[itemprop='reviewCount']").first
        rc = meta.get_attribute("content", timeout=2000)
        if rc and rc.isdigit():
            out["reviews_total"] = int(rc)
    except Exception:
        pass
    if "reviews_total" not in out:
        try:
            for sel in (
                "div[class*='business-header-rating-view__text'] a[class*='business-rating-amount-view']",
                "a[class*='business-rating-amount-view']",
                "div[class*='business-rating-amount-view']",
                "span[class*='business-rating-amount-view']",
            ):
                el = page.locator(sel).first
                txt = el.text_content(timeout=1500)
                if not txt:
                    continue
                m = re.search(r"(\d[\d\s]*)", txt)
                if m:
                    digits = re.sub(r"\D", "", m.group(1))
                    if digits:
                        out["reviews_total"] = int(digits)
                        break
        except Exception:
            pass

    # Сайт (если у бани не было)
    try:
        for sel in ("a[class*='card-feature-view__link'][href^='http']",
                    "a[aria-label*='Сайт']",
                    "a[data-qa='WebSite']"):
            el = page.locator(sel).first
            href = el.get_attribute("href", timeout=2000)
            if href and href.startswith("http") and "yandex." not in href:
                out["site_url"] = href
                break
    except Exception:
        pass

    return out


def run_enrich_rows(con: sqlite3.Connection, rows: list, dry: bool) -> tuple[int, int]:
    """Один браузер, последовательный enrich по списку строк (id, slug, title, city, lat, lon)."""
    from playwright.sync_api import sync_playwright

    if not rows:
        return 0, 0
    commit_every = int(os.environ.get("BANYA_ENRICH_COMMIT_EVERY", "10"))
    success = fail = 0
    pending_writes = 0
    with sync_playwright() as p:
        browser = _new_browser(p)
        ctx = _new_context(browser)
        page = ctx.new_page()
        for sid, slug, title, city, lat, lon in rows:
            if title_is_sauna_only(title):
                print(f"  skip sauna-only #{sid} {title[:40]}")
                fail += 1
                continue
            print(f"  → #{sid:4d} {title[:40]:40s} {city or '?':20s}")
            try:
                data = enrich_one(page, {
                    "title": title, "city": city, "lat": lat, "lon": lon,
                })
            except Exception as e:
                print(f"     ! {e}")
                fail += 1
                time.sleep(WAIT_PER_REQ)
                continue
            if not data:
                fail += 1
                time.sleep(WAIT_PER_REQ)
                continue
            if data.get("yandex_url"):
                success += 1
                tail = []
                if data.get("phone"):
                    tail.append(f"📞 {data['phone']}")
                if data.get("rating_avg"):
                    tail.append(f"★ {data['rating_avg']}")
                if data.get("reviews_total") is not None:
                    tail.append(f"{data['reviews_total']} отз.")
                if data.get("site_url"):
                    tail.append("сайт")
                ok_traffic = True
                if data.get("reviews_total") is not None:
                    ok_traffic = traffic_ok(data.get("reviews_total"), data.get("rating_avg"))
                if not ok_traffic:
                    tail.append("low_traffic→skip_keep_draft")
                print("     " + " · ".join(tail) if tail else "     (только URL)")
                if not dry:
                    sets = {k: v for k, v in data.items() if v not in (None, "")}
                    # низкий трафик: URL оставляем, статус draft
                    if not ok_traffic:
                        sets["status"] = "draft"
                    cols = ", ".join(f"{k} = ?" for k in sets)
                    con.execute(
                        f"UPDATE banya_spots SET {cols}, updated_at = ? WHERE id = ?",
                        list(sets.values()) + [_now_iso(), sid],
                    )
                    pending_writes += 1
                    if pending_writes >= commit_every:
                        con.commit()
                        pending_writes = 0
            time.sleep(WAIT_PER_REQ)
        ctx.close()
        browser.close()
    if not dry and pending_writes:
        con.commit()
    return success, fail


def run_refresh_rows(con: sqlite3.Connection, rows: list, dry: bool) -> tuple[int, int]:
    """Освежает rating_avg/reviews_total/site_url для строк, у которых уже есть yandex_url.

    rows: (id, title, city, yandex_url)
    """
    from playwright.sync_api import sync_playwright

    if not rows:
        return 0, 0
    commit_every = int(os.environ.get("BANYA_ENRICH_COMMIT_EVERY", "10"))
    success = fail = 0
    pending_writes = 0
    with sync_playwright() as p:
        browser = _new_browser(p)
        ctx = _new_context(browser)
        page = ctx.new_page()
        for sid, title, city, yurl in rows:
            print(f"  ↻ #{sid:4d} {title[:40]:40s} {city or '?':20s}")
            try:
                data = enrich_one(page, {
                    "title": title, "city": city, "existing_url": yurl,
                })
            except Exception as e:
                print(f"     ! {e}")
                fail += 1
                time.sleep(_refresh_cooldown_s())
                continue
            if not data:
                fail += 1
                time.sleep(_refresh_cooldown_s())
                continue
            keep = {"rating_avg", "reviews_total", "site_url", "phone"}
            sets = {k: v for k, v in data.items() if k in keep and v not in (None, "")}
            # не затирать известный высокий reviews_total нулём/пустым scrape
            if "reviews_total" in sets:
                try:
                    new_rt = int(sets["reviews_total"])
                except (TypeError, ValueError):
                    new_rt = 0
                if new_rt <= 0:
                    sets.pop("reviews_total", None)
            tail = []
            if "rating_avg" in sets:
                tail.append(f"★ {sets['rating_avg']}")
            if "reviews_total" in sets:
                tail.append(f"{sets['reviews_total']} отз.")
            ok_traffic = True
            if "reviews_total" in sets or data.get("reviews_total") is not None:
                ok_traffic = traffic_ok(
                    sets.get("reviews_total", data.get("reviews_total")),
                    sets.get("rating_avg", data.get("rating_avg")),
                )
            if not ok_traffic:
                sets["status"] = "draft"
                tail.append("low_traffic→draft")
            print("     " + " · ".join(tail) if tail else "     (без изменений)")
            success += 1
            if sets and not dry:
                cols = ", ".join(f"{k} = ?" for k in sets)
                con.execute(
                    f"UPDATE banya_spots SET {cols}, updated_at = ? WHERE id = ?",
                    list(sets.values()) + [_now_iso(), sid],
                )
                pending_writes += 1
                if pending_writes >= commit_every:
                    con.commit()
                    pending_writes = 0
            time.sleep(_refresh_cooldown_s())
        ctx.close()
        browser.close()
    if not dry and pending_writes:
        con.commit()
    return success, fail


def cmd_refresh(args) -> int:
    con = _open_db()
    where = [
        "status != 'hidden'",
        "yandex_url IS NOT NULL AND TRIM(yandex_url) != ''",
    ]
    params: list = []
    if args.id:
        where.append("id = ?")
        params.append(args.id)
    elif args.region:
        where.append("region = ?")
        params.append(args.region.upper())
    if getattr(args, "need_reviews", False):
        where.append("(reviews_total IS NULL OR reviews_total = 0)")
    rows = con.execute(
        f"SELECT id, title, city, yandex_url FROM banya_spots "
        f"WHERE {' AND '.join(where)} ORDER BY updated_at ASC, id ASC LIMIT ?",
        params + [args.limit],
    ).fetchall()
    if not rows:
        print("Нечего обновлять.")
        con.close()
        return 0
    per = WAIT_SETTLE + _refresh_cooldown_avg_s() + 3.0
    print(f"Refresh {len(rows)} бань. Ожидаемое время ≈ {len(rows) * per:.0f} сек. "
          f"(пауза между точками: {_refresh_cooldown_avg_s():.1f} с в среднем, "
          f"env BANYA_REFRESH_WAIT_MIN/MAX)")
    success, fail = run_refresh_rows(con, rows, args.dry)
    con.close()
    print(f"--- refresh done. ok={success}, miss={fail}")
    return 0


def cmd_enrich(args) -> int:
    con = _open_db()
    where = [
        "status != 'hidden'",
        "(yandex_url IS NULL OR TRIM(yandex_url) = '')",
        flagship_region_sql("region") if not args.id else "1=1",
    ]
    params = []
    if args.id:
        where = ["id = ?"]
        params = [args.id]
    elif args.region:
        where = [
            "status != 'hidden'",
            "(yandex_url IS NULL OR TRIM(yandex_url) = '')",
            "region = ?",
        ]
        params = [args.region.upper()]
    # приоритет: в названии «бан», потом остальные
    rows = con.execute(
        f"SELECT id, slug, title, city, lat, lon FROM banya_spots "
        f"WHERE {' AND '.join(where)} "
        f"ORDER BY CASE WHEN LOWER(COALESCE(title,'')) LIKE '%бан%' THEN 0 ELSE 1 END, "
        f"CASE status WHEN 'published' THEN 0 WHEN 'draft' THEN 1 ELSE 2 END, id "
        f"LIMIT ?",
        params + [args.limit],
    ).fetchall()
    # отсечь сауны до браузера
    rows = [r for r in rows if not title_is_sauna_only(r[2])]
    if not rows:
        print("Нечего обогащать (всё уже с yandex_url, не FLAGSHIP, или только сауны).")
        print(f"quality regions={','.join(quality_regions())} min_reviews={min_reviews()}")
        con.close()
        return 0

    print(
        f"Обогащаем {len(rows)} бань (regions={','.join(quality_regions())}, "
        f"min_reviews={min_reviews()}). ≈ "
        f"{len(rows) * (WAIT_SETTLE + WAIT_PER_REQ + 3):.0f} сек."
    )
    success, fail = run_enrich_rows(con, rows, args.dry)
    con.close()
    print(f"--- enrich done. ok={success}, miss={fail}")
    return 0


# ─── reviews ─────────────────────────────────────────────────────────────────


def _find_org_url(page, title: str, city: str | None) -> str | None:
    """Через text-search выясняем canonical org-URL первой подходящей организации.
    Возвращает прямую ссылку вида https://yandex.{ru|com}/maps/org/<slug>/<id>/.
    """
    q = " ".join(filter(None, [title, city])).strip()
    if not q:
        return None
    url = f"https://yandex.ru/maps/?text={q}".replace(" ", "+")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
    except Exception:
        return None
    time.sleep(WAIT_SETTLE)
    if "/maps/org/" in page.url:
        return page.url.split("?")[0]
    try:
        href = page.locator("a[href*='/maps/org/']").first.get_attribute(
            "href", timeout=3000
        )
    except Exception:
        return None
    if not href:
        return None
    if href.startswith("/"):
        href = "https://yandex.ru" + href
    # Обрежем query
    return href.split("?")[0]


def _open_reviews_via_search(page, title: str, city: str | None,
                              stored_org_url: str | None = None) -> bool:
    """Открываем страницу /reviews/ конкретной организации и ждём появления карточек.

    Стратегия: если у нас уже есть org-URL (с прошлого enrich) — используем его,
    добавив /reviews/. Иначе через text-search находим первую org-ссылку.
    """
    org_url = stored_org_url or _find_org_url(page, title, city)
    if not org_url:
        return False
    # Сразу подсунем хвост /reviews/, чтобы Яндекс открыл вкладку отзывов.
    reviews_url = org_url.rstrip("/") + "/reviews/"
    try:
        page.goto(reviews_url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
    except Exception:
        return False
    time.sleep(WAIT_SETTLE)
    if _is_captcha(page):
        return False
    return "/maps/org/" in page.url


def parse_reviews_from_page(page, limit: int) -> list[dict]:
    """Снимаем до `limit` свежих отзывов с открытой страницы организации."""
    # Прокручиваем боковую панель внутри карточки, чтобы догрузить карточки отзывов
    for _ in range(min(10, max(3, limit // 2))):
        try:
            # Скролл основной части
            page.mouse.wheel(0, 1500)
            # Дополнительно — скролл внутри панели отзывов
            page.evaluate(
                "() => { const p = document.querySelector("
                "'.scroll__container, .business-reviews-card-view__reviews'); "
                "if (p) p.scrollTop += 1500; }"
            )
        except Exception:
            break
        time.sleep(0.7)

    # Селекторы Яндекс.Карт меняются. Пробуем несколько вариантов карточек отзыва.
    items = []
    for sel in (
        "div[class*='business-review-view']",
        "div[class*='business-reviews-card-view__review']",
        "li[class*='business-reviews-card-view__review']",
        "div[itemtype*='Review']",
    ):
        found = page.locator(sel).all()
        if found:
            items = found
            break
    out: list[dict] = []
    for el in items:
        author = ""
        try:
            for sel in (
                "a[class*='business-review-view__user']",
                "div[class*='business-review-view__author']",
                "span[itemprop='name']",
            ):
                loc = el.locator(sel).first
                if loc.count() > 0:
                    author = (loc.text_content(timeout=800) or "").strip()
                    if author:
                        break
        except Exception:
            pass
        text = ""
        try:
            for sel in (
                "span[class*='business-review-view__body-text']",
                "span[itemprop='reviewBody']",
                "span[class*='spoiler-view__text-container']",
                "div[class*='business-review-view__body']",
            ):
                loc = el.locator(sel).first
                if loc.count() > 0:
                    text = (loc.text_content(timeout=800) or "").strip()
                    if text:
                        break
        except Exception:
            pass
        try:
            rating_aria = el.locator(
                "div[class*='business-rating-badge-view__stars']"
            ).first.get_attribute("aria-label", timeout=1000) or ""
            m = re.search(r"(\d)\s*из\s*5", rating_aria) or re.search(r"([1-5])", rating_aria)
            rating = int(m.group(1)) if m else None
        except Exception:
            rating = None
        try:
            date_txt = ""
            meta = el.locator("meta[itemprop='datePublished']").first
            if meta.count() > 0:
                date_txt = meta.get_attribute("content", timeout=500) or ""
            if not date_txt:
                date_txt = (
                    el.locator("span[class*='business-review-view__date']")
                    .first.text_content(timeout=500)
                    or ""
                )
        except Exception:
            date_txt = ""
        published_at = parse_review_date(date_txt)
        if not text or len(text) < 8:
            continue
        if not review_is_fresh(published_at):
            # без даты или слишком старый — не тащим в каталог
            continue
        # Чистим хвосты автора: «ИльдарЗнаток города 12 ур.» → «Ильдар».
        if author:
            author = re.split(
                r"(?:Знаток города|Местный знаток|Любитель путешествий|Знаток мест)",
                author,
                maxsplit=1,
            )[0].strip()
            author = author[:60] or None
        # source_id: sha1 текста. Встроенный hash() Python меняется между запусками
        # и из‑за этого ночной парсер записывал те же отзывы снова и снова.
        sid = stable_review_source_id(text)
        if any(o["source_id"] == sid for o in out):
            continue
        out.append({
            "author": author or None,
            "rating": rating,
            "text": text[:1500],
            "date_text": date_txt or None,
            "published_at": published_at.isoformat(timespec="seconds") if published_at else None,
            "source_id": sid,
        })
        if len(out) >= limit:
            break
    return out


def run_reviews_rows(
    con: sqlite3.Connection, rows: list[tuple], max_rv: int, dry: bool,
) -> tuple[int, int, int]:
    """rows: (id, slug, title, city, yandex_url). Возвращает saved, dup, miss."""
    from playwright.sync_api import sync_playwright

    if not rows:
        return 0, 0, 0
    saved = dup = miss = 0
    with sync_playwright() as p:
        browser = _new_browser(p)
        ctx = _new_context(browser)
        page = ctx.new_page()
        for sid, slug, title, city, yurl in rows:
            print(f"\n→ #{sid} {title[:50]}")
            try:
                ok = _open_reviews_via_search(page, title, city, yurl)
                if not ok:
                    print("  ! карточку не открыли")
                    miss += 1
                    time.sleep(WAIT_PER_REQ)
                    continue
                if _is_captcha(page):
                    print("  ! CAPTCHA")
                    miss += 1
                    time.sleep(WAIT_PER_REQ)
                    continue
                reviews = parse_reviews_from_page(page, max_rv)
                if not yurl:
                    base = page.url.split("?")[0]
                    if "/reviews" in base:
                        base = base.split("/reviews")[0] + "/"
                    if "/maps/org/" in base and not dry:
                        con.execute(
                            "UPDATE banya_spots SET yandex_url = ?, updated_at = ? "
                            "WHERE id = ? AND (yandex_url IS NULL OR yandex_url = '')",
                            (base, _now_iso(), sid),
                        )
            except Exception as e:
                print(f"  ! {e}")
                miss += 1
                time.sleep(WAIT_PER_REQ)
                continue
            print(f"  снято: {len(reviews)}")
            for rv in reviews:
                if dry:
                    a = (rv.get("author") or "?")[:25]
                    r = rv.get("rating") or "-"
                    t = (rv.get("text") or "")[:70]
                    d = rv.get("published_at") or "?"
                    print(f"   - {a:25s}  ★{r}  [{d}]  {t}")
                    continue
                existing = con.execute(
                    "SELECT 1 FROM banya_reviews WHERE source = 'yandex' AND ("
                    "  source_id = ? OR (spot_id = ? AND TRIM(text) = TRIM(?))"
                    ")",
                    (rv["source_id"], sid, rv["text"]),
                ).fetchone()
                if existing:
                    dup += 1
                    continue
                con.execute(
                    "INSERT INTO banya_reviews "
                    "(spot_id, source, source_id, author, rating, text, url, "
                    " published_at, fetched_at, status) "
                    "VALUES (?, 'yandex', ?, ?, ?, ?, ?, ?, ?, 'pending')",
                    (
                        sid,
                        rv["source_id"],
                        rv["author"],
                        rv["rating"],
                        rv["text"],
                        yurl,
                        rv.get("published_at"),
                        _now_iso(),
                    ),
                )
                saved += 1
            if not dry:
                # reviews_total = счётчик Яндекса (из enrich/refresh), не затираем
                # локальным COUNT — иначе ломается quality gate по посещаемости.
                con.execute(
                    "UPDATE banya_spots SET updated_at = ? WHERE id = ?",
                    (_now_iso(), sid),
                )
                con.commit()
            time.sleep(WAIT_PER_REQ)
        ctx.close()
        browser.close()
    return saved, dup, miss


def cmd_reviews(args) -> int:
    con = _open_db()
    where = ["title IS NOT NULL", "title != ''"]
    params: list = []
    if args.id:
        where = ["id = ?"]
        params = [args.id]
    else:
        if args.status:
            where.append("status = ?")
            params.append(args.status)
        if getattr(args, "region", None):
            where.append("region = ?")
            params.append(str(args.region).upper())
        else:
            where.append(flagship_region_sql("region"))
        where.append("yandex_url IS NOT NULL AND TRIM(yandex_url) != ''")
        where.append("COALESCE(reviews_total, 0) >= ?")
        params.append(min_reviews())
    rows = con.execute(
        f"SELECT id, slug, title, city, yandex_url FROM banya_spots "
        f"WHERE {' AND '.join(where)} "
        f"ORDER BY COALESCE(reviews_total, 0) DESC, id LIMIT ?",
        params + [args.batch],
    ).fetchall()
    rows = [r for r in rows if not title_is_sauna_only(r[2])]
    if not rows:
        print("Нет бань для отзывов (проверьте фильтр / yandex_url / min_reviews).")
        con.close()
        return 0

    print(f"Отзывы: {len(rows)} точек, max={args.max}, min_reviews={min_reviews()}")
    saved, dup, miss = run_reviews_rows(con, rows, args.max, args.dry)
    con.close()
    print(f"\n--- reviews done. saved={saved}, dup={dup}, miss={miss}")
    return 0


def _run_post_daily_moderate_ai(dry: bool) -> None:
    """После reviews: RAG+LLM модерация pending через OpenRouter.

    По умолчанию включено, если задан OPENROUTER_API_KEY. Отключить: BANYA_DAILY_MODERATE_AI=0.
    """
    if dry:
        print("--- moderate-ai: skip (daily --dry)")
        return
    if not (os.environ.get("OPENROUTER_API_KEY") or "").strip():
        print("--- moderate-ai: skip (нет OPENROUTER_API_KEY)")
        return
    off = os.environ.get("BANYA_DAILY_MODERATE_AI", "1").strip().lower()
    if off in ("0", "false", "no", "off"):
        print("--- moderate-ai: off (BANYA_DAILY_MODERATE_AI=0)")
        return
    script = ROOT / "tools" / "banya_review_moderate_ai.py"
    if not script.is_file():
        print(f"--- moderate-ai: skip (нет файла {script})")
        return
    batch = os.environ.get("BANYA_DAILY_MODERATE_BATCH", "18").strip() or "18"
    max_b = os.environ.get("BANYA_DAILY_MODERATE_MAX_BATCHES", "4").strip() or "4"
    limit = os.environ.get("BANYA_DAILY_MODERATE_LIMIT", "0").strip() or "0"
    src = os.environ.get("BANYA_DAILY_MODERATE_SOURCE", "yandex").strip()
    cmd: list[str] = [
        sys.executable,
        "-u",
        str(script),
        "--apply",
        "--batch-size",
        batch,
        "--max-batches",
        max_b,
    ]
    if limit not in ("", "0"):
        cmd += ["--limit", str(int(limit))]
    if src and src.upper() != "ALL":
        cmd += ["--source", src]
    print(f"--- moderate-ai: {' '.join(cmd[2:])}")
    try:
        r = subprocess.run(cmd, cwd=str(ROOT), timeout=660)
        print(f"--- moderate-ai finished rc={r.returncode}")
    except subprocess.TimeoutExpired:
        print("--- moderate-ai: TIMEOUT 660s")
    except Exception as e:
        print(f"--- moderate-ai: {e}")


def cmd_daily(args) -> int:
    """Малый ночной прогон: enrich без URL, затем reviews для published.

    Лимиты через env (разумные по умолчанию, чтобы не ловить капчу):
      BANYA_DAILY_ENRICH_LIMIT=12
      BANYA_DAILY_REVIEWS_SPOTS=4
      BANYA_DAILY_REVIEWS_MAX=6
      BANYA_DAILY_REVIEWS_REFRESH_DAYS=7
      BANYA_DAILY_SKIP_ENRICH=1 | BANYA_DAILY_SKIP_REVIEWS=1

    После reviews (если не --dry), по умолчанию ИИ-модерация pending→approve/hide (OpenRouter):
      OPENROUTER_API_KEY           — обязательно для фазы moderate-ai
      BANYA_DAILY_MODERATE_AI=0    — выключить (по умолчанию включено при наличии ключа)
      BANYA_DAILY_MODERATE_BATCH=18
      BANYA_DAILY_MODERATE_MAX_BATCHES=4
      BANYA_DAILY_MODERATE_LIMIT=0
      BANYA_DAILY_MODERATE_SOURCE=yandex — только этот source; ALL = все источники
    """
    con = _open_db()
    dry = args.dry
    print("=== banya daily job ===", "DRY" if dry else "")

    if os.environ.get("BANYA_DAILY_SKIP_ENRICH", "").lower() not in ("1", "true", "yes"):
        lim_e = int(os.environ.get("BANYA_DAILY_ENRICH_LIMIT", "12"))
        reg_sql = flagship_region_sql("region")
        rows_e = con.execute(
            "SELECT id, slug, title, city, lat, lon FROM banya_spots "
            "WHERE status != 'hidden' "
            f"  AND {reg_sql} "
            "  AND (yandex_url IS NULL OR TRIM(yandex_url) = '') "
            "ORDER BY CASE WHEN LOWER(COALESCE(title,'')) LIKE '%бан%' THEN 0 ELSE 1 END, id "
            "LIMIT ?",
            (lim_e * 3,),  # с запасом под отсев саун
        ).fetchall()
        rows_e = [r for r in rows_e if not title_is_sauna_only(r[2])][:lim_e]
        if rows_e:
            est = len(rows_e) * (WAIT_SETTLE + WAIT_PER_REQ + 3)
            print(
                f"--- enrich phase: {len(rows_e)} spots (~{est:.0f}s) "
                f"regions={','.join(quality_regions())} min_rev={min_reviews()}"
            )
            s, f = run_enrich_rows(con, rows_e, dry)
            print(f"--- enrich done ok={s} miss={f}")
        else:
            print("--- enrich phase: skip (nothing missing yandex_url)")
    else:
        print("--- enrich phase: skipped (BANYA_DAILY_SKIP_ENRICH)")

    if os.environ.get("BANYA_DAILY_SKIP_REVIEWS", "").lower() not in ("1", "true", "yes"):
        lim_r = int(os.environ.get("BANYA_DAILY_REVIEWS_SPOTS", "4"))
        max_rv = int(os.environ.get("BANYA_DAILY_REVIEWS_MAX", "6"))
        days = int(os.environ.get("BANYA_DAILY_REVIEWS_REFRESH_DAYS", "7"))
        rows_r = _select_review_candidates(con, lim_r, days)
        if rows_r:
            est = len(rows_r) * (WAIT_SETTLE + WAIT_PER_REQ + 2) * max_rv / 6
            print(
                f"--- reviews phase: {len(rows_r)} spots (~{est:.0f}s), "
                f"refresh>{days}d, only fresh reviews + min_rev={min_reviews()}"
            )
            sv, dp, ms = run_reviews_rows(con, rows_r, max_rv, dry)
            print(f"--- reviews done saved={sv} dup={dp} miss={ms}")
        else:
            print("--- reviews phase: skip (no candidates)")
    else:
        print("--- reviews phase: skipped (BANYA_DAILY_SKIP_REVIEWS)")

    if not dry:
        try:
            from tools.banya_quality import apply_demote, low_quality_published

            low = low_quality_published(con)
            if low:
                n = apply_demote(con, low)
                print(f"--- quality gate: demoted {n}/{len(low)} low-traffic published → draft")
            else:
                print("--- quality gate: ok")
        except Exception as e:
            print(f"--- quality gate: {e}")

    con.close()
    _run_post_daily_moderate_ai(dry)
    print("=== banya daily finished ===")
    return 0


def main(argv: list[str]) -> int:
    _load_dotenv()
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    pe = sub.add_parser("enrich", help="наполнить yandex_url/phone/rating")
    pe.add_argument("--id", type=int)
    pe.add_argument("--region")
    pe.add_argument("--limit", type=int, default=30)
    pe.add_argument("--dry", action="store_true")
    pe.set_defaults(func=cmd_enrich)

    pr = sub.add_parser("reviews", help="снять отзывы")
    pr.add_argument("--id", type=int)
    pr.add_argument("--status", help="published|draft|hidden")
    pr.add_argument("--region", help="MSK|MO|SPB|LO|…")
    pr.add_argument("--batch", type=int, default=20, help="максимум бань за прогон")
    pr.add_argument("--max", type=int, default=10, help="отзывов на баню")
    pr.add_argument("--dry", action="store_true")
    pr.set_defaults(func=cmd_reviews)

    pd = sub.add_parser(
        "daily",
        help="ночной лимитированный enrich+reviews (см. env BANYA_DAILY_*)",
    )
    pd.add_argument("--dry", action="store_true")
    pd.set_defaults(func=cmd_daily)

    pf = sub.add_parser(
        "refresh",
        help="освежить rating_avg/reviews_total/site_url для уже привязанных к Яндексу",
    )
    pf.add_argument("--id", type=int)
    pf.add_argument("--region")
    pf.add_argument("--limit", type=int, default=50)
    pf.add_argument(
        "--need-reviews",
        action="store_true",
        help="только точки с reviews_total IS NULL или 0 (не гонять уже обновлённые)",
    )
    pf.add_argument("--dry", action="store_true")
    pf.set_defaults(func=cmd_refresh)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
