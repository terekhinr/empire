#!/usr/bin/env python3
"""E2E gym: login form visible, then SSR app with program/diary/meas."""
from __future__ import annotations

import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, "/root/projects/empire")
from planning_api import PLANNING_API_TOKEN  # noqa: E402


def fail(msg: str) -> None:
    print("FAIL:", msg)
    sys.exit(1)


def main() -> None:
    if not PLANNING_API_TOKEN:
        fail("no token")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(25000)

        page.goto("https://neverretire.ru/gym/?v=fix1", wait_until="domcontentloaded")
        # Must see login (not blank)
        page.wait_for_selector("#auth:not(.hidden), #auth", timeout=10000)
        auth_visible = page.evaluate(
            """() => {
              const a = document.getElementById('auth');
              if (!a) return false;
              const st = getComputedStyle(a);
              return st.display !== 'none' && st.visibility !== 'hidden';
            }"""
        )
        if not auth_visible:
            fail("auth not visible — blank screen risk")
        print("OK auth visible")

        page.fill("#token", PLANNING_API_TOKEN)
        page.click("#auth-form button[type=submit]")
        page.wait_for_function(
            """() => {
              const app = document.getElementById('app');
              const c = document.getElementById('content');
              return app && !app.classList.contains('hidden') && c && c.innerText.trim().length > 5;
            }""",
            timeout=20000,
        )
        text = page.locator("#content").inner_text()
        if "Таймаут" in text or "Не загрузилось" in text:
            fail("program bad: " + text[:180])
        boot_ok = page.evaluate("() => { try { return JSON.parse(document.getElementById('gym-boot').textContent).program_id; } catch(e) { return null; } }")
        if not boot_ok:
            fail("boot missing after login")
        print("OK program", text.splitlines()[0][:60], "boot", boot_ok)

        page.click('button[data-tab="diary"]')
        diary = page.locator("#content").inner_text()
        if not diary.strip():
            fail("empty diary")
        print("OK diary", diary.splitlines()[0][:60])

        page.click('button[data-tab="meas"]')
        meas = page.locator("#content").inner_text()
        if "Новый замер" not in meas:
            fail("meas: " + meas[:180])
        print("OK meas")

        browser.close()
    print("ALL_OK")


if __name__ == "__main__":
    main()
