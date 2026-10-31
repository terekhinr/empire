#!/usr/bin/env python3
"""E2E: /go/ + login /go-learn/ → syllabus with weekly lessons."""
from __future__ import annotations

import http.cookiejar
import ssl
import sys
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
    )
    base = "https://127.0.0.1:9443"
    hdr = {"Host": "neverretire.ru"}

    with opener.open(
        urllib.request.Request(base + "/go/", headers=hdr), timeout=20
    ) as r:
        hub = r.read().decode("utf-8", "replace")
    ok_hub = "/go-tasks/" in hub and "/gym/" in hub and "/go-learn/" in hub

    data = urllib.parse.urlencode({"token": tok}).encode()
    req = urllib.request.Request(
        base + "/go-learn/",
        data=data,
        method="POST",
        headers={**hdr, "Content-Type": "application/x-www-form-urlencoded"},
    )
    with opener.open(req, timeout=30) as r:
        body = r.read().decode("utf-8", "replace")

    ok_path = "B2B Python Developer" in body
    ok_syll = "Силлабус" in body and "Неделя 0" in body
    ok_pct = "%" in body and "шагов" in body
    ok_cont = "Продолжить" in body or "Неделя 1" in body

    report = {
        "ok_hub": ok_hub,
        "ok_path": ok_path,
        "ok_syll": ok_syll,
        "ok_pct": ok_pct,
        "ok_cont": ok_cont,
    }
    print(report)
    if all(report.values()):
        print("PASS_E2E_GO_LEARN")
        return 0
    print("FAIL_E2E_GO_LEARN")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
