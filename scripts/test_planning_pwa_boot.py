#!/usr/bin/env python3
"""Headless Chromium boot test for Задачник PWA. Exit 0 only on verified UI."""
from __future__ import annotations

import asyncio
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get("PLANNING_TEST_URL", "https://neverretire.ru/x/")
TOKEN = (os.environ.get("PLANNING_API_TOKEN") or "").strip()
if not TOKEN:
    env_path = ROOT / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("PLANNING_API_TOKEN="):
                TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

CHROMES = [
    # Prefer Playwright Chrome — snap chromium fails under systemd/capability limits.
    str(Path.home() / ".cache/ms-playwright/chromium-1217/chrome-linux64/chrome"),
    "/usr/bin/google-chrome-stable",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/snap/bin/chromium",
]


def find_chrome() -> str:
    for p in CHROMES:
        if Path(p).exists():
            return p
    raise SystemExit("NO_CHROME")


async def cdp_main() -> int:
    import websockets

    chrome = find_chrome()
    port = 9336
    proc = subprocess.Popen(
        [
            chrome,
            "--headless=new",
            "--no-sandbox",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            f"--remote-debugging-port={port}",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        version = None
        for _ in range(50):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1) as r:
                    version = json.load(r)
                    break
            except Exception:
                time.sleep(0.2)
        if not version:
            print("CDP_PORT_FAIL")
            return 1

        browser_ws = version["webSocketDebuggerUrl"]
        async with websockets.connect(browser_ws, max_size=40_000_000) as bws:
            bid = 0

            async def bsend(method: str, params: dict | None = None):
                nonlocal bid
                bid += 1
                await bws.send(json.dumps({"id": bid, "method": method, "params": params or {}}))
                while True:
                    raw = json.loads(await bws.recv())
                    if raw.get("id") == bid:
                        return raw

            created = await bsend("Target.createTarget", {"url": "about:blank"})
            target_id = created["result"]["targetId"]
            attached = await bsend(
                "Target.attachToTarget", {"targetId": target_id, "flatten": True}
            )
            session_id = attached["result"]["sessionId"]

            sid = 0

            async def send(method: str, params: dict | None = None):
                nonlocal sid
                sid += 1
                msg = {
                    "id": sid,
                    "method": method,
                    "params": params or {},
                    "sessionId": session_id,
                }
                await bws.send(json.dumps(msg))
                while True:
                    raw = json.loads(await bws.recv())
                    if raw.get("method") == "Target.receivedMessageFromTarget":
                        continue
                    if raw.get("sessionId") == session_id and raw.get("id") == sid:
                        return raw
                    if raw.get("id") == sid and "result" in raw:
                        return raw

            async def evaluate(expression: str):
                r = await send(
                    "Runtime.evaluate",
                    {
                        "expression": expression,
                        "returnByValue": True,
                        "awaitPromise": True,
                    },
                )
                if r.get("result", {}).get("exceptionDetails"):
                    raise RuntimeError(json.dumps(r["result"]["exceptionDetails"])[:800])
                return r.get("result", {}).get("result", {}).get("value")

            await send("Runtime.enable")
            await send("Page.enable")
            await send("Network.enable")

            # Inject token BEFORE first document scripts so init() sees it immediately.
            if TOKEN:
                await send(
                    "Page.addScriptToEvaluateOnNewDocument",
                    {
                        "source": f"""
                          try {{
                            localStorage.setItem("empire_planning_token", {json.dumps(TOKEN)});
                            localStorage.setItem("empire_app_ver", "82");
                          }} catch (e) {{}}
                        """
                    },
                )

            await send("Page.navigate", {"url": BASE})
            await asyncio.sleep(2)

            snap = None
            for _ in range(30):
                await asyncio.sleep(1)
                snap = await evaluate(
                    """(() => {
                      const splash = document.getElementById("boot-splash");
                      const auth = document.getElementById("auth-screen");
                      const err = document.getElementById("boot-error");
                      const splashHidden =
                        !splash ||
                        splash.classList.contains("hidden") ||
                        getComputedStyle(splash).display === "none";
                      const authHidden =
                        !auth ||
                        auth.classList.contains("hidden") ||
                        getComputedStyle(auth).display === "none";
                      const errVisible = !!(err && err.style.display === "block" && (err.textContent || "").trim());
                      const diag = window.__empireDiag || null;
                      return {
                        ready: !!window.__empireReady,
                        splashVisible: !splashHidden,
                        splashText: document.querySelector("[data-boot-msg]")?.textContent || null,
                        authVisible: !authHidden,
                        pageTitle: document.getElementById("page-title")?.textContent || null,
                        todayLen: (document.getElementById("view-today")?.innerHTML || "").length,
                        taskCount: diag ? (diag.tasks || 0) : 0,
                        checklistCount: diag ? (diag.checklists || 0) : 0,
                        listsNav: document.getElementById("nav-count-lists")?.textContent || null,
                        errText: errVisible ? (err.textContent || "").trim() : null,
                        hasCareerFM: !!(window.EMPIRE_FINANCE_MODEL && window.EMPIRE_FINANCE_MODEL.career),
                        appVer: diag?.appVer || null,
                        diag,
                        bodyPreview: (document.body?.innerText || "").replace(/\\s+/g, " ").slice(0, 240),
                      };
                    })()"""
                )
                if (
                    snap.get("ready")
                    and not snap.get("splashVisible")
                    and not snap.get("authVisible")
                    and not snap.get("errText")
                    and (snap.get("taskCount") or 0) > 0
                ):
                    break

            api_probe = None
            if TOKEN:
                api_probe = await evaluate(
                    """(async () => {
                      const t = localStorage.getItem("empire_planning_token") || "";
                      const headers = { "X-Planning-Token": t, "Content-Type": "application/json" };
                      const [tasks, lists] = await Promise.all([
                        fetch("/tasks/api/planning/tasks", { headers }).then(async r => ({status:r.status, n:(await r.json()).tasks?.length||0})),
                        fetch("/tasks/api/planning/checklists", { headers }).then(async r => {
                          const j = await r.json();
                          const cls = j.checklists || [];
                          return {status:r.status, n:cls.length, career: cls.filter(c => String(c.title||'').includes('Карьера')).length};
                        }),
                      ]);
                      return { tasks, lists };
                    })()"""
                )

            career_tab = None
            if (
                snap
                and snap.get("ready")
                and not snap.get("splashVisible")
                and not snap.get("authVisible")
                and not snap.get("errText")
            ):
                await evaluate(
                    """(() => { document.querySelector('[data-view="finance-model"]')?.click(); return true; })()"""
                )
                await asyncio.sleep(0.7)
                await evaluate(
                    """(() => { document.querySelector('[data-fm-tab="career"]')?.click(); return true; })()"""
                )
                await asyncio.sleep(0.6)
                career_tab = await evaluate(
                    """(() => {
                      const root = document.getElementById("view-finance-model");
                      const text = root ? root.innerText : "";
                      return {
                        hasCareerTab: !!document.querySelector('[data-fm-tab="career"]'),
                        hasCareerTitle: /Карьера/.test(text) && /B2B/.test(text),
                        hasLms: /go-learn|W0|Практикум|Sem1/.test(text),
                        preview: text.replace(/\\s+/g, " ").slice(0, 260),
                      };
                    })()"""
                )

            out = {"snap": snap, "api_probe": api_probe, "career_tab": career_tab}
            print(json.dumps(out, ensure_ascii=False, indent=2))

            if not TOKEN:
                ok = bool(snap.get("authVisible") or snap.get("ready"))
                print("PASS_NO_TOKEN" if ok else "FAIL_NO_TOKEN")
                return 0 if ok else 1

            ui_ok = bool(
                snap.get("ready")
                and not snap.get("splashVisible")
                and not snap.get("authVisible")
                and not snap.get("errText")
                and (snap.get("taskCount") or 0) > 50
                and (snap.get("checklistCount") or 0) >= 10
                and snap.get("pageTitle") == "Сегодня"
            )
            api_ok = bool(
                api_probe
                and api_probe.get("tasks", {}).get("status") == 200
                and api_probe.get("lists", {}).get("status") == 200
                and (api_probe.get("lists", {}).get("career") or 0) >= 10
            )
            fm_ok = bool(
                snap.get("hasCareerFM")
                and str(snap.get("appVer") or "").isdigit()
                and int(snap.get("appVer")) >= 84
            )
            tab_ok = bool(
                career_tab
                and career_tab.get("hasCareerTab")
                and career_tab.get("hasCareerTitle")
                and (
                    career_tab.get("hasLms")
                    or "W0" in str(career_tab.get("preview") or "")
                    or "go-learn" in str(career_tab.get("preview") or "")
                    or "Sem1" in str(career_tab.get("preview") or "")
                )
            )

            print(
                json.dumps(
                    {"ui_ok": ui_ok, "api_ok": api_ok, "fm_ok": fm_ok, "tab_ok": tab_ok},
                    ensure_ascii=False,
                )
            )
            if ui_ok and api_ok and fm_ok and tab_ok:
                print("PASS_FULL")
                return 0
            print("FAIL")
            return 1
    finally:
        try:
            proc.send_signal(signal.SIGKILL)
        except Exception:
            pass
        try:
            proc.wait(timeout=2)
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(asyncio.run(cdp_main()))
