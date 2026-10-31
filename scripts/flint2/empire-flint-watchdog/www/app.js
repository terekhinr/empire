(() => {
  const API = "/cgi-bin/empire-api";
  const TOKEN_KEY = "empire_flint_ui_token";
  const HTTPS_MIRROR = "https://neverretire.ru/home-ops/";
  const LABELS = {
    podkop: "Podkop / YouTube",
    zapret: "Zapret",
    youtube: "YouTube OK",
    telegram: "Telegram OK",
    torrents: "Трекеры (rutracker)",
    routes: "Маршруты TG",
    awg: "Amnezia",
    usb: "USB download",
    samba: "Samba шара",
    tunnel: "Туннель VPS",
    ha: "Home Assistant",
    ha_healer: "HA хилер (Flint)",
  };

  const $ = (id) => document.getElementById(id);
  const checksEl = $("checks");
  const outEl = $("out");
  const logEl = $("log");
  const metaEl = $("watchdog-meta");
  const gate = $("auth-gate");
  const migrate = $("migrate-banner");
  const haHealChecks = $("ha-healer-checks");
  const haHealMeta = $("ha-healer-meta");
  const haHealLog = $("ha-healer-log");
  const haHealBadge = $("ha-healer-badge");

  function fmtAge(sec) {
    const n = Number(sec) || 0;
    if (n <= 0) return "—";
    if (n < 60) return `${n}с`;
    if (n < 3600) return `${Math.floor(n / 60)}м`;
    return `${Math.floor(n / 3600)}ч`;
  }

  function renderHaHealer(h) {
    if (!haHealChecks || !h) return;
    const rows = [
      ["Установлен", !!h.installed],
      ["Cron */5", !!h.cron],
      ["Ванная присутствие", h.vannaya_presence === "on" || h.vannaya_presence === "off", `ванна ${h.vannaya_presence || "?"} / свет ${h.vannaya_light || "?"}`],
      ["Туалет присутствие", h.tualet_presence === "on" || h.tualet_presence === "off", `туалет ${h.tualet_presence || "?"} / свет ${h.tualet_light || "?"}`],
      ["Домофон IP", !!(h.intercom_ip && h.intercom_ip !== "none"), h.intercom_ip || "нет"],
    ];
    haHealChecks.innerHTML = "";
    rows.forEach(([label, ok, detail]) => {
      const el = document.createElement("div");
      el.className = "check";
      el.innerHTML = `<span class="dot ${ok ? "ok" : "bad"}"></span><span>${label}${detail ? ": " + detail : ""}</span>`;
      haHealChecks.appendChild(el);
    });
    const stuckV = Number(h.vannaya_stuck_age) || 0;
    const stuckT = Number(h.tualet_stuck_age) || 0;
    const th = Number(h.stuck_threshold) || 2700;
    if (haHealMeta) {
      haHealMeta.textContent = [
        h.last_run ? `Прогон: ${h.last_run}` : "Ещё не писал state",
        `залипание ванна ${fmtAge(stuckV)} / туалет ${fmtAge(stuckT)} (порог ${fmtAge(th)})`,
        h.issues ? `issues:${h.issues}` : "issues: нет",
      ].join(" · ");
    }
    if (haHealBadge) {
      const warn = stuckV >= th || stuckT >= th || (h.issues && String(h.issues).trim());
      haHealBadge.textContent = !h.installed ? "нет" : warn ? "внимание" : "ок";
      haHealBadge.className = "badge " + (!h.installed ? "bad" : warn ? "warn" : "ok");
    }
    if (haHealLog && h.log_tail) {
      haHealLog.textContent = String(h.log_tail).split("|").join("\n");
    }
  }

  function isLanOrigin() {
    const h = location.hostname;
    return h === "192.168.1.1" || h === "127.0.0.1" || h.endsWith(".lan");
  }

  function getToken() {
    const q = new URLSearchParams(location.search).get("token");
    if (q) {
      localStorage.setItem(TOKEN_KEY, q);
      try {
        const u = new URL(location.href);
        u.searchParams.delete("token");
        history.replaceState({}, "", u.pathname + u.search + u.hash);
      } catch (_) {}
      return q;
    }
    return localStorage.getItem(TOKEN_KEY) || "";
  }

  function showMigrateBanner() {
    if (!migrate) return;
    if (!isLanOrigin()) {
      migrate.classList.add("hidden");
      return;
    }
    const tok = getToken();
    const href = tok ? `${HTTPS_MIRROR}?token=${encodeURIComponent(tok)}` : HTTPS_MIRROR;
    migrate.classList.remove("hidden");
    const a = $("migrate-link");
    if (a) a.href = href;
  }

  function setBusy(on) {
    document.querySelectorAll(".btn[data-act]").forEach((b) => {
      b.disabled = on;
    });
    $("btn-refresh").disabled = on;
  }

  async function api(action, extra = {}) {
    const token = getToken();
    if (!token) throw new Error("нет токена");
    const params = new URLSearchParams({ action, token, ...extra });
    const method = action === "status" ? "GET" : "POST";
    const url = `${API}?${params}`;
    const opts = {
      method,
      headers: {
        Authorization: `Bearer ${token}`,
        "X-Empire-Token": token,
      },
    };
    if (method === "POST") {
      opts.headers["Content-Type"] = "application/x-www-form-urlencoded";
      opts.body = params.toString();
    }
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 25000);
    opts.signal = ctrl.signal;
    let r;
    try {
      r = await fetch(url, opts);
    } catch (e) {
      if (e && e.name === "AbortError") throw new Error("таймаут — нет связи с роутером");
      throw new Error("сеть недоступна (включи Tailscale или открой neverretire.ru/home-ops)");
    } finally {
      clearTimeout(t);
    }
    let data;
    try {
      data = await r.json();
    } catch (_) {
      throw new Error(`плохой ответ API (${r.status})`);
    }
    if (!data.ok && data.error === "unauthorized") {
      localStorage.removeItem(TOKEN_KEY);
      showGate(true);
      throw new Error("неверный токен");
    }
    if (!r.ok) throw new Error(data.error || `HTTP ${r.status}`);
    return data;
  }

  function showGate(show) {
    gate.classList.toggle("hidden", !show);
  }

  function renderChecks(checks) {
    checksEl.innerHTML = "";
    Object.keys(LABELS).forEach((k) => {
      const ok = !!(checks && checks[k]);
      const el = document.createElement("div");
      el.className = "check";
      el.innerHTML = `<span class="dot ${ok ? "ok" : "bad"}"></span><span>${LABELS[k]}</span>`;
      checksEl.appendChild(el);
    });
  }

  async function refresh() {
    showMigrateBanner();
    if (!getToken()) {
      showGate(true);
      metaEl.textContent = "Введи токен один раз — сохранится здесь";
      checksEl.innerHTML =
        '<p class="hint" style="margin:0">Без токена статус не грузится. Поле «Токен доступа» выше — или открой ссылку с ?token=…</p>';
      if (logEl) logEl.textContent = "";
      return;
    }
    showGate(false);
    setBusy(true);
    try {
      const data = await api("status");
      renderChecks(data.checks || {});
      renderHaHealer(data.ha_healer || {});
      const w = data.watchdog || {};
      metaEl.textContent = w.last_run
        ? `Сторож: ${w.last_run}${data.mode ? " · режим " + data.mode + (data.mode_state && data.mode_state !== data.mode ? "/" + data.mode_state : "") : ""}${w.last_problems ? " · проблемы: " + w.last_problems : " · OK"}${data.usb_detail ? " · USB: " + data.usb_detail : ""}`
        : "Сторож ещё не писал state";
      if (data.log_tail) {
        logEl.textContent = String(data.log_tail).split("|").join("\n");
      }
    } catch (e) {
      metaEl.textContent = "Ошибка: " + (e.message || e);
      renderChecks({});
      renderHaHealer({});
    } finally {
      setBusy(false);
    }
  }

  async function runAction(act, svc) {
    setBusy(true);
    outEl.hidden = false;
    outEl.textContent = "Жди…";
    try {
      const extra = svc ? { svc } : {};
      const data = await api(act, extra);
      outEl.textContent = JSON.stringify(data, null, 2);
      await refresh();
    } catch (e) {
      outEl.textContent = String(e.message || e);
    } finally {
      setBusy(false);
    }
  }

  $("btn-save-token").addEventListener("click", () => {
    const v = ($("token-input").value || "").trim();
    if (!v) return;
    localStorage.setItem(TOKEN_KEY, v);
    refresh();
  });
  $("btn-refresh").addEventListener("click", refresh);
  document.querySelectorAll(".btn[data-act]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const act = btn.getAttribute("data-act");
      const svc = btn.getAttribute("data-svc") || "";
      if (act === "ha_restart" && !confirm("Перезапустить Home Assistant?")) return;
      if (act === "ha_heal" && svc === "force" && !confirm("Принудительный прогон HA хилера (игнор cooldown)?")) return;
      runAction(act, svc);
    });
  });

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("./sw.js", { updateViaCache: "none" }).catch(() => {});
  }

  refresh();
  setInterval(refresh, 60000);
})();
