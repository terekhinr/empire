"""Скриншоты главной gdepar.ru: первый экран + ключевые секции, в обоих темах."""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parents[1] / "tools" / "screens"
OUT.mkdir(parents=True, exist_ok=True)

URL = "http://127.0.0.1:8001/"
SHOTS = [
    ("dark",  1366, 860, False),
    ("light", 1366, 860, False),
    ("mobile_dark", 420, 860, True),
]

SECTIONS = [
    ("01_hero_map", None),       # top of page: hero + map feature
    ("02_bayki",    "#bayki"),
    ("03_merch",    "#merch"),
    ("04_contacts", "#contacts"),
]


def shoot() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for theme, w, h, _mob in SHOTS:
            ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=1)
            page = ctx.new_page()
            page.goto(URL, wait_until="networkidle")
            page.evaluate(f"document.documentElement.setAttribute('data-theme', '{theme}')")
            page.wait_for_timeout(700)
            for name, sel in SECTIONS:
                if sel:
                    page.evaluate(f"document.querySelector('{sel}').scrollIntoView({{behavior:'instant',block:'start'}})")
                    page.wait_for_timeout(300)
                else:
                    page.evaluate("window.scrollTo(0,0)")
                    page.wait_for_timeout(300)
                f = OUT / f"{theme}__{name}.png"
                page.screenshot(path=str(f), full_page=False)
                print(f"{f}  ({f.stat().st_size // 1024} KB)")
            ctx.close()
        browser.close()


if __name__ == "__main__":
    shoot()
