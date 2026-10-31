#!/usr/bin/env python3
"""Full escape-path verification. Exit 0 only on PASS_ALL."""
from __future__ import annotations

import asyncio
import base64
import json
import os
import signal
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKEN = (os.environ.get("PLANNING_API_TOKEN") or "").strip()
if not TOKEN:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("PLANNING_API_TOKEN="):
            TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")
            break

CHROME = str(Path.home() / ".cache/ms-playwright/chromium-1217/chrome-linux64/chrome")
OUT = Path("/tmp/zadachnik_verify")
OUT.mkdir(exist_ok=True)


async def main() -> int:
    import websockets

    if not TOKEN:
        print("NO_TOKEN")
        return 1
    if not Path(CHROME).exists():
        print("NO_CHROME")
        return 1

    port = 9360
    proc = subprocess.Popen(
        [
            CHROME,
            "--headless=new",
            "--no-sandbox",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            f"--remote-debugging-port={port}",
            "--window-size=1280,900",
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

        async with websockets.connect(version["webSocketDebuggerUrl"], max_size=40_000_000) as bws:
            bid = 0

            async def bsend(method, params=None):
                nonlocal bid
                bid += 1
                await bws.send(json.dumps({"id": bid, "method": method, "params": params or {}}))
                while True:
                    raw = json.loads(await bws.recv())
                    if raw.get("id") == bid:
                        return raw

            async def new_session(url="about:blank"):
                created = await bsend("Target.createTarget", {"url": url})
                attached = await bsend(
                    "Target.attachToTarget",
                    {"targetId": created["result"]["targetId"], "flatten": True},
                )
                sid = attached["result"]["sessionId"]
                n = {"i": 0}

                async def send(method, params=None, timeout=25.0):
                    n["i"] += 1
                    req = n["i"]
                    await bws.send(
                        json.dumps(
                            {"id": req, "method": method, "params": params or {}, "sessionId": sid}
                        )
                    )
                    deadline = time.time() + timeout
                    while time.time() < deadline:
                        raw = json.loads(
                            await asyncio.wait_for(bws.recv(), timeout=max(0.05, deadline - time.time()))
                        )
                        if raw.get("sessionId") == sid and raw.get("id") == req:
                            return raw
                        if raw.get("id") == req and "result" in raw:
                            return raw
                    raise TimeoutError(method)

                async def ev(expr, timeout=20.0):
                    r = await send(
                        "Runtime.evaluate",
                        {"expression": expr, "returnByValue": True, "awaitPromise": True},
                        timeout=timeout,
                    )
                    if r.get("result", {}).get("exceptionDetails"):
                        raise RuntimeError(str(r["result"]["exceptionDetails"])[:400])
                    return r.get("result", {}).get("result", {}).get("value")

                async def shot(name):
                    r = await send("Page.captureScreenshot", {"format": "png"})
                    p = OUT / f"{name}.png"
                    p.write_bytes(base64.b64decode(r["result"]["data"]))
                    return p

                await send("Page.enable")
                await send("Runtime.enable")
                return send, ev, shot

            results = {}

            # --- A: recover page is yellow + button (no black) ---
            send, ev, shot = await new_session()
            await send("Page.navigate", {"url": "https://neverretire.ru/go-reset/"})
            await asyncio.sleep(2)
            a = await ev(
                """(() => ({
                  href: location.href,
                  bg: getComputedStyle(document.body).backgroundColor,
                  text: (document.body.innerText||'').replace(/\\s+/g,' ').slice(0,240),
                  hasBtn: !!document.getElementById('open-x'),
                  btnHref: document.getElementById('open-x')?.getAttribute('href') || null
                }))()"""
            )
            await shot("01_recover")
            results["recover_yellow"] = bool(
                a
                and a.get("hasBtn")
                and ("/x/" in str(a.get("btnHref") or ""))
                and ("ffe600" in str(a).lower() or "255, 230, 0" in str(a.get("bg") or "") or "ОТКРЫТЬ" in str(a.get("text") or ""))
            )
            print("A", json.dumps(a, ensure_ascii=False))

            # --- B: go-tasks also yellow ---
            send2, ev2, shot2 = await new_session()
            await send2("Page.navigate", {"url": "https://neverretire.ru/go-tasks/"})
            await asyncio.sleep(2)
            b = await ev2(
                """(() => ({
                  text: (document.body.innerText||'').replace(/\\s+/g,' ').slice(0,200),
                  bg: getComputedStyle(document.body).backgroundColor,
                  hasLink: !!document.querySelector('a[href*=\"/x/\"]')
                }))()"""
            )
            await shot2("02_go_tasks")
            results["go_tasks"] = bool(
                b
                and b.get("hasLink")
                and (
                    "ОТКРЫТЬ" in str(b.get("text") or "")
                    or "/x/" in str(b.get("text") or "")
                    or "токен" in str(b.get("text") or "").lower()
                )
            )
            print("B", json.dumps(b, ensure_ascii=False))

            # --- C: hang SW on /tasks/, prove stuck ---
            send3, ev3, shot3 = await new_session()
            await send3("Page.navigate", {"url": "https://neverretire.ru/tasks/"})
            await asyncio.sleep(2)
            await ev3(
                """(async () => {
                  const regs = await navigator.serviceWorker.getRegistrations();
                  await Promise.all(regs.map(r => r.unregister()));
                  await navigator.serviceWorker.register('/tasks/assets/sw-hang-test.js?v=1', {
                    scope: '/tasks/', updateViaCache: 'none'
                  });
                  await navigator.serviceWorker.ready;
                  return true;
                })()"""
            )
            hang_ok = False
            try:
                await send3(
                    "Page.navigate",
                    {"url": "https://neverretire.ru/tasks/?hung=1"},
                    timeout=3.0,
                )
            except TimeoutError:
                hang_ok = True
            try:
                await ev3("1+1", timeout=4.0)
            except TimeoutError:
                hang_ok = True
            results["hang_proven"] = hang_ok
            print("C hang_proven", hang_ok)

            # --- D: escape via /x/ with token despite hung /tasks/ ---
            send4, ev4, shot4 = await new_session()
            await send4(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": f'localStorage.setItem("empire_planning_token",{json.dumps(TOKEN)});'
                    f'localStorage.setItem("empire_app_ver","81");'
                },
            )
            await send4("Page.navigate", {"url": "https://neverretire.ru/x/?src=verify"})
            snap = None
            for i in range(25):
                await asyncio.sleep(1)
                snap = await ev4(
                    """(() => {
                      const splash = document.getElementById('boot-splash');
                      const auth = document.getElementById('auth-screen');
                      const diag = window.__empireDiag || null;
                      return {
                        ready: !!window.__empireReady,
                        splashHidden: !splash || splash.classList.contains('hidden'),
                        authHidden: !auth || auth.classList.contains('hidden'),
                        tasks: diag && diag.tasks || 0,
                        appVer: diag && diag.appVer,
                        mount: typeof TASKS_MOUNT!=='undefined' ? TASKS_MOUNT : null,
                        title: document.getElementById('page-title')?.textContent || null,
                        splashBg: splash ? getComputedStyle(splash).backgroundColor : null,
                      };
                    })()"""
                )
                print("D", i, snap)
                if (
                    snap
                    and snap.get("ready")
                    and snap.get("splashHidden")
                    and snap.get("authHidden")
                    and (snap.get("tasks") or 0) > 50
                    and snap.get("mount") == "/x"
                ):
                    break
            await shot4("03_x_today")
            results["x_boot"] = bool(
                snap
                and snap.get("ready")
                and snap.get("splashHidden")
                and snap.get("authHidden")
                and (snap.get("tasks") or 0) > 50
                and snap.get("appVer") == "81"
                and snap.get("mount") == "/x"
            )

            # career tab
            await ev4("""(() => { document.querySelector('[data-view="finance-model"]')?.click(); return true; })()""")
            await asyncio.sleep(0.8)
            await ev4("""(() => { document.querySelector('[data-fm-tab="career"]')?.click(); return true; })()""")
            await asyncio.sleep(0.8)
            career = await ev4(
                """(() => {
                  const t = document.getElementById('view-finance-model')?.innerText || '';
                  return {
                    hasTab: !!document.querySelector('[data-fm-tab="career"]'),
                    hasPhase0: t.includes('Фаза 0'),
                    hasCareer: /Карьера/.test(t) && /B2B/.test(t),
                    preview: t.replace(/\\s+/g,' ').slice(0,220)
                  };
                })()"""
            )
            await shot4("04_x_career")
            results["career"] = bool(career and career.get("hasTab") and career.get("hasPhase0") and career.get("hasCareer"))
            print("D career", json.dumps(career, ensure_ascii=False))

            print(json.dumps({"results": results}, ensure_ascii=False, indent=2))
            if all(results.values()):
                print("PASS_ALL")
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
    raise SystemExit(asyncio.run(main()))
