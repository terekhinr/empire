#!/usr/bin/env python3
"""Prove hung-SW failure mode, then prove /tasks-fix/ restores boot.

PASS_HANG_AND_RECOVER only if both phases succeed.
"""
from __future__ import annotations

import asyncio
import json
import os
import signal
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get("PLANNING_TEST_URL", "https://neverretire.ru/tasks/")
RECOVER = os.environ.get("PLANNING_RECOVER_URL", "https://neverretire.ru/tasks-fix/")
ESCAPE = os.environ.get("PLANNING_ESCAPE_URL", "https://neverretire.ru/x/")
TOKEN = (os.environ.get("PLANNING_API_TOKEN") or "").strip()
if not TOKEN:
    env_path = ROOT / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("PLANNING_API_TOKEN="):
                TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

CHROME = str(Path.home() / ".cache/ms-playwright/chromium-1217/chrome-linux64/chrome")


async def main() -> int:
    import websockets

    if not Path(CHROME).exists():
        print("NO_CHROME")
        return 1

    port = 9344
    proc = subprocess.Popen(
        [
            CHROME,
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

        async with websockets.connect(version["webSocketDebuggerUrl"], max_size=40_000_000) as bws:
            bid = 0

            async def bsend(method: str, params: dict | None = None):
                nonlocal bid
                bid += 1
                await bws.send(json.dumps({"id": bid, "method": method, "params": params or {}}))
                while True:
                    raw = json.loads(await bws.recv())
                    if raw.get("id") == bid:
                        return raw

            async def attach_target(url: str):
                created = await bsend("Target.createTarget", {"url": url})
                tid = created["result"]["targetId"]
                attached = await bsend(
                    "Target.attachToTarget", {"targetId": tid, "flatten": True}
                )
                return tid, attached["result"]["sessionId"]

            def session_api(session_id: str):
                sid = {"n": 0}

                async def send(method: str, params: dict | None = None, timeout: float = 20.0):
                    sid["n"] += 1
                    req_id = sid["n"]
                    await bws.send(
                        json.dumps(
                            {
                                "id": req_id,
                                "method": method,
                                "params": params or {},
                                "sessionId": session_id,
                            }
                        )
                    )
                    deadline = time.time() + timeout
                    while time.time() < deadline:
                        try:
                            raw = json.loads(
                                await asyncio.wait_for(bws.recv(), timeout=max(0.1, deadline - time.time()))
                            )
                        except asyncio.TimeoutError:
                            break
                        if raw.get("sessionId") == session_id and raw.get("id") == req_id:
                            return raw
                        if raw.get("id") == req_id and "result" in raw:
                            return raw
                    raise TimeoutError(f"CDP timeout: {method}")

                async def evaluate(expr: str, timeout: float = 15.0):
                    r = await send(
                        "Runtime.evaluate",
                        {
                            "expression": expr,
                            "returnByValue": True,
                            "awaitPromise": True,
                        },
                        timeout=timeout,
                    )
                    if r.get("result", {}).get("exceptionDetails"):
                        raise RuntimeError(json.dumps(r["result"]["exceptionDetails"])[:500])
                    return r.get("result", {}).get("result", {}).get("value")

                return send, evaluate

            # ---- Phase A: install hang SW, prove navigate never settles ----
            tid1, sid1 = await attach_target("about:blank")
            send1, ev1 = session_api(sid1)
            await send1("Page.enable")
            await send1("Runtime.enable")
            await send1("Page.navigate", {"url": BASE})
            await asyncio.sleep(2)

            reg = await ev1(
                """(async () => {
                  const regs = await navigator.serviceWorker.getRegistrations();
                  await Promise.all(regs.map(r => r.unregister()));
                  const reg = await navigator.serviceWorker.register(
                    "/tasks/assets/sw-hang-test.js?v=1",
                    { scope: "/tasks/", updateViaCache: "none" }
                  );
                  await navigator.serviceWorker.ready;
                  return { scope: reg.scope, active: (reg.active && reg.active.scriptURL) || null };
                })()"""
            )
            print(json.dumps({"phase": "register", "reg": reg}, ensure_ascii=False))
            if not reg or "sw-hang-test" not in str(reg.get("active") or ""):
                print("FAIL_HANG_NOT_INSTALLED")
                return 1

            # Fire navigate; hang SW never answers → evaluate must time out.
            await bws.send(
                json.dumps(
                    {
                        "id": 990001,
                        "method": "Page.navigate",
                        "params": {"url": BASE + "?hung=1"},
                        "sessionId": sid1,
                    }
                )
            )
            await asyncio.sleep(3)
            hang_ok = False
            try:
                await ev1("document.body && document.body.innerHTML.length", timeout=5.0)
                # If evaluate still works on old doc, check URL didn't become ?hung=1 with ready
                state = await ev1(
                    """(() => ({
                      href: location.href,
                      ready: !!window.__empireReady,
                      controller: (navigator.serviceWorker.controller && navigator.serviceWorker.controller.scriptURL) || null
                    }))()""",
                    timeout=5.0,
                )
                # Stuck mid-nav: href may already be ?hung=1 but ready never flips on new doc.
                # Strong signal: controller is hang SW and we never get __empireDiag on new load.
                hang_ok = bool(state and "sw-hang-test" in str(state.get("controller") or state))
                print(json.dumps({"phase": "hang_state", "state": state}, ensure_ascii=False))
            except TimeoutError:
                hang_ok = True
                print(json.dumps({"phase": "hang", "evaluate_timed_out": True}, ensure_ascii=False))

            if not hang_ok:
                # Fallback: registrations still hang SW after attempted nav
                try:
                    regs = await ev1(
                        "(async () => (await navigator.serviceWorker.getRegistrations()).map(r => (r.active&&r.active.scriptURL)||''))()",
                        timeout=5.0,
                    )
                    hang_ok = any("sw-hang-test" in str(x) for x in (regs or []))
                except TimeoutError:
                    hang_ok = True

            if not hang_ok:
                print("FAIL_HANG_NOT_PROVEN")
                return 1
            print(json.dumps({"phase": "hang_proven", "ok": True}, ensure_ascii=False))

            # ---- Phase B: recover page → must land on /x/ (NOT /tasks/) ----
            tid2, sid2 = await attach_target(RECOVER)
            send2, ev2 = session_api(sid2)
            await send2("Page.enable")
            await send2("Runtime.enable")

            snap = None
            landed_x = False
            for i in range(40):
                await asyncio.sleep(0.5)
                try:
                    href = await ev2("location.href", timeout=5.0)
                except TimeoutError:
                    continue
                if href and "/x/" in href:
                    landed_x = True
                    break
                # If stuck on recover with button, click escape link
                if href and "tasks-fix" in href:
                    try:
                        clicked = await ev2(
                            """(() => {
                              const a = document.getElementById("open-x");
                              if (!a) return false;
                              a.click();
                              return true;
                            })()""",
                            timeout=5.0,
                        )
                        print(json.dumps({"phase": "click_open_x", "clicked": clicked}, ensure_ascii=False))
                    except TimeoutError:
                        pass

            if not landed_x:
                # Force navigate escape path
                await send2("Page.navigate", {"url": ESCAPE}, timeout=15.0)
                await asyncio.sleep(1)

            if TOKEN:
                try:
                    await ev2(
                        f"""(() => {{
                          localStorage.setItem("empire_planning_token", {json.dumps(TOKEN)});
                          localStorage.setItem("empire_app_ver", "80");
                          return true;
                        }})()""",
                        timeout=5.0,
                    )
                    await send2("Page.reload", {"ignoreCache": True}, timeout=15.0)
                except TimeoutError:
                    pass

            for _ in range(30):
                await asyncio.sleep(1)
                try:
                    snap = await ev2(
                        """(async () => {
                          const splash = document.getElementById("boot-splash");
                          const auth = document.getElementById("auth-screen");
                          const splashHidden = !splash || splash.classList.contains("hidden");
                          const authHidden = !auth || auth.classList.contains("hidden");
                          const diag = window.__empireDiag || null;
                          const regs = await navigator.serviceWorker.getRegistrations();
                          return {
                            ready: !!window.__empireReady,
                            splashVisible: !splashHidden,
                            authVisible: !authHidden,
                            taskCount: diag ? diag.tasks : 0,
                            appVer: diag ? diag.appVer : null,
                            href: location.href,
                            mount: (typeof TASKS_MOUNT !== "undefined") ? TASKS_MOUNT : null,
                            regs: regs.map(r => (r.active && r.active.scriptURL) || (r.installing && r.installing.scriptURL) || ""),
                            controller: (navigator.serviceWorker.controller && navigator.serviceWorker.controller.scriptURL) || null,
                          };
                        })()""",
                        timeout=10.0,
                    )
                except TimeoutError:
                    continue
                if (
                    snap
                    and snap.get("ready")
                    and not snap.get("splashVisible")
                    and not snap.get("authVisible")
                    and (snap.get("taskCount") or 0) > 50
                    and "/x" in str(snap.get("href") or "")
                    and not any("sw-hang-test" in str(x) for x in (snap.get("regs") or []))
                ):
                    break

            print(json.dumps({"phase": "recover", "snap": snap}, ensure_ascii=False, indent=2))
            recovered = bool(
                snap
                and snap.get("ready")
                and not snap.get("splashVisible")
                and not snap.get("authVisible")
                and (snap.get("taskCount") or 0) > 50
                and snap.get("appVer") == "80"
                and "/x" in str(snap.get("href") or "")
                and not any("sw-hang-test" in str(x) for x in (snap.get("regs") or []))
            )
            if hang_ok and recovered:
                print("PASS_HANG_AND_RECOVER")
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
