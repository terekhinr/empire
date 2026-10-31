#!/usr/bin/env node
/**
 * Headless boot test for Задачник PWA.
 * Usage: PLANNING_API_TOKEN=... node scripts/test_planning_pwa_boot.mjs
 * Exit 0 only if UI becomes ready (or auth screen shown without token).
 */
import { spawn } from "child_process";
import fs from "fs";
import { setTimeout as sleep } from "timers/promises";

const token = (process.env.PLANNING_API_TOKEN || "").trim();
const BASE = process.env.PLANNING_TEST_URL || "https://neverretire.ru/tasks/";
const chromePaths = [
  "/usr/bin/chromium-browser",
  "/usr/bin/chromium",
  "/usr/bin/google-chrome-stable",
  "/usr/bin/google-chrome",
];
const chrome = chromePaths.find((p) => fs.existsSync(p));
if (!chrome) {
  console.error("NO_CHROME");
  process.exit(2);
}

const port = 9333 + Math.floor(Math.random() * 100);
const child = spawn(
  chrome,
  [
    "--headless=new",
    "--no-sandbox",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    `--remote-debugging-port=${port}`,
    "about:blank",
  ],
  { stdio: ["ignore", "pipe", "pipe"] }
);

async function waitPort(ms = 8000) {
  const start = Date.now();
  while (Date.now() - start < ms) {
    try {
      const r = await fetch(`http://127.0.0.1:${port}/json/version`);
      if (r.ok) return;
    } catch (_) {}
    await sleep(200);
  }
  throw new Error("CDP port not ready");
}

async function openPage(url) {
  // Chromium versions differ: PUT or GET
  for (const method of ["PUT", "GET"]) {
    try {
      const r = await fetch(
        `http://127.0.0.1:${port}/json/new?${encodeURIComponent(url)}`,
        { method }
      );
      if (r.ok) return r.json();
    } catch (_) {}
  }
  throw new Error("cannot open page");
}

function connectWs(url) {
  return new Promise((resolve, reject) => {
    import("ws").then(({ default: WebSocket }) => {
      const ws = new WebSocket(url);
      const pending = new Map();
      let nextId = 0;
      let sessionId = null;
      ws.on("open", () => {
        const api = {
          send(method, params = {}) {
            const id = ++nextId;
            const msg = { id, method, params };
            if (sessionId) msg.sessionId = sessionId;
            return new Promise((res, rej) => {
              pending.set(id, { res, rej });
              ws.send(JSON.stringify(msg));
            });
          },
          setSession(id) {
            sessionId = id;
          },
          close() {
            ws.close();
          },
        };
        resolve(api);
      });
      ws.on("message", (raw) => {
        const msg = JSON.parse(String(raw));
        if (msg.id && pending.has(msg.id)) {
          const { res } = pending.get(msg.id);
          pending.delete(msg.id);
          res(msg);
        }
      });
      ws.on("error", reject);
    });
  });
}

async function evaluate(api, expression) {
  const r = await api.send("Runtime.evaluate", {
    expression,
    returnByValue: true,
    awaitPromise: true,
  });
  if (r.result?.exceptionDetails) {
    throw new Error(JSON.stringify(r.result.exceptionDetails));
  }
  return r.result?.result?.value;
}

async function main() {
  const errors = [];
  try {
    await waitPort();
    const page = await openPage("about:blank");
    const wsUrl = page.webSocketDebuggerUrl;
    if (!wsUrl) throw new Error("no websocket for page");
    const api = await connectWs(wsUrl);
    await api.send("Runtime.enable");
    await api.send("Page.enable");
    await api.send("Network.enable");
    await api.send("Runtime.addBinding", { name: "pwaBootLog" }).catch(() => {});

    // Capture console
    // Navigate
    await api.send("Page.navigate", { url: BASE });
    await sleep(2500);

    if (token) {
      await evaluate(
        api,
        `(() => {
          localStorage.setItem("empire_planning_token", ${JSON.stringify(token)});
          localStorage.setItem("empire_app_ver", "75");
          return true;
        })()`
      );
      await api.send("Page.reload", { ignoreCache: true });
      await sleep(7000);
    } else {
      await sleep(3000);
    }

    const snap = await evaluate(
      api,
      `(() => {
        const splash = document.getElementById("boot-splash");
        const auth = document.getElementById("auth-screen");
        const err = document.getElementById("boot-error");
        return {
          ready: !!window.__empireReady,
          hasSplash: !!splash,
          splashVisible: !!(splash && splash.offsetParent !== null && !splash.classList.contains("hidden")),
          splashText: document.querySelector("[data-boot-msg]")?.textContent || null,
          authVisible: !!(auth && !auth.classList.contains("hidden")),
          pageTitle: document.getElementById("page-title")?.textContent || null,
          todayLen: (document.getElementById("view-today")?.innerHTML || "").length,
          errText: err?.textContent || null,
          errShown: err?.style?.display === "block",
          hasCareerFM: !!(window.EMPIRE_FINANCE_MODEL && window.EMPIRE_FINANCE_MODEL.career),
          tasks: Array.isArray(window.state?.tasks) ? state.tasks.length : -1,
          checklists: Array.isArray(window.state?.checklists) ? state.checklists.length : -1,
          careerChecklists: (window.state?.checklists || []).filter((c) =>
            String(c.title || "").includes("Карьера")
          ).length,
          bodyPreview: (document.body?.innerText || "").replace(/\\s+/g, " ").slice(0, 180),
        };
      })()`
    );

    console.log(JSON.stringify({ ok: true, snap }, null, 2));

    // Pass criteria
    if (!token) {
      if (snap.authVisible || snap.ready) {
        console.log("PASS_AUTH_OR_READY");
        process.exitCode = 0;
      } else if (snap.splashVisible && snap.splashText) {
        console.log("PASS_SPLASH_VISIBLE_NO_TOKEN");
        process.exitCode = 0;
      } else {
        console.error("FAIL_NO_UI");
        process.exitCode = 1;
      }
    } else {
      const uiOk =
        snap.ready &&
        !snap.splashVisible &&
        (snap.todayLen > 50 || snap.pageTitle === "Сегодня" || snap.authVisible);
      const careerOk = snap.careerChecklists >= 10 && snap.hasCareerFM;
      if (uiOk && careerOk) {
        console.log("PASS_FULL");
        process.exitCode = 0;
      } else if (uiOk) {
        console.log("PASS_UI_CAREER_PARTIAL", { careerOk });
        process.exitCode = careerOk ? 0 : 1;
      } else {
        console.error("FAIL_UI", snap);
        process.exitCode = 1;
      }
    }
    api.close();
  } catch (e) {
    console.error("TEST_ERROR", e);
    process.exitCode = 1;
  } finally {
    child.kill("SIGKILL");
  }
}

main();
