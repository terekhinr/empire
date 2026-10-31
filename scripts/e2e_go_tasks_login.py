#!/usr/bin/env python3
"""E2E: POST /go-tasks/ with token → SSR list with open tasks. Exit 0 only on real titles."""
from __future__ import annotations

import http.cookiejar
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _token() -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("PLANNING_API_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("NO_TOKEN")


def main() -> int:
    tok = _token()
    ctx = ssl._create_unverified_context()
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ctx),
        urllib.request.HTTPCookieProcessor(cj),
        urllib.request.HTTPRedirectHandler(),
    )

    base = "https://127.0.0.1:9443"
    hdr = {"Host": "neverretire.ru", "Content-Type": "application/x-www-form-urlencoded"}

    data = urllib.parse.urlencode({"token": tok}).encode()
    req = urllib.request.Request(
        base + "/go-tasks/",
        data=data,
        method="POST",
        headers=hdr,
    )
    with opener.open(req, timeout=25) as resp:
        body = resp.read().decode("utf-8", "replace")
        final = resp.geturl()

    ok_list = "Открытых:" in body and "<ul id=\"list\">" in body
    ok_item = "<li>" in body and "Нет задач" not in body
    ok_full_btn = "/x/?native_token=" in body and ("ПОЛНЫЙ" in body or "/x/" in body)
    cookie_ok = any(c.name == "empire_go_tasks_token" for c in cj)

    # Second GET must still show list
    req2 = urllib.request.Request(base + "/go-tasks/", headers={"Host": "neverretire.ru"})
    with opener.open(req2, timeout=25) as resp2:
        body2 = resp2.read().decode("utf-8", "replace")
    ok_persist = "Открытых:" in body2

    # Full UI handoff URL must load SPA shell
    import re

    m = re.search(r'href="(/x/\?native_token=[^"]+)"', body)
    spa_ok = False
    if m:
        path = m.group(1).replace("&amp;", "&")
        req3 = urllib.request.Request(base + path, headers={"Host": "neverretire.ru"})
        with opener.open(req3, timeout=25) as resp3:
            spa = resp3.read().decode("utf-8", "replace")
        spa_ok = "app.js" in spa and "__TASKS_MOUNT__" in spa and 'id="auth-screen"' in spa

    report = {
        "final_path": urllib.parse.urlparse(final).path,
        "ok_list": ok_list,
        "ok_item": ok_item,
        "ok_full_btn": ok_full_btn,
        "cookie_ok": cookie_ok,
        "ok_persist": ok_persist,
        "spa_ok": spa_ok,
        "open_line": next((ln.strip() for ln in body.splitlines() if "Открытых:" in ln), None),
    }
    print(report)
    if all([ok_list, ok_item, ok_full_btn, cookie_ok, ok_persist, spa_ok]):
        print("PASS_E2E_GO_TASKS")
        return 0
    print("FAIL_E2E_GO_TASKS")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
