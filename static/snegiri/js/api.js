/** API client — same origin /api/snegiri */
(function (global) {
  const BASE = (function () {
    const p = window.location.pathname;
    if (p.includes("/static/snegiri")) return "/api/snegiri";
    return "/api/snegiri";
  })();

  async function req(path, opts) {
    opts = opts || {};
    const headers = Object.assign({}, opts.headers || {});
    const sid = global.SnegiriStore && global.SnegiriStore.getSessionId();
    if (sid) headers["X-Session-Id"] = sid;
    const res = await fetch(BASE + path, Object.assign({}, opts, { headers }));
    if (!res.ok) {
      const err = new Error("api_" + res.status);
      err.status = res.status;
      try {
        err.body = await res.json();
      } catch (_) {}
      throw err;
    }
    return res.json();
  }

  async function health() {
    return req("/health");
  }

  async function ensureSession() {
    let sid = global.SnegiriStore.getSessionId();
    if (sid) {
      try {
        await req("/session/" + sid);
        return sid;
      } catch (_) {
        global.SnegiriStore.clearSessionId();
      }
    }
    const s = await req("/session", { method: "POST" });
    global.SnegiriStore.setSessionId(s.id);
    return s.id;
  }

  async function syncProfile(profile) {
    await ensureSession();
    return req("/session/" + global.SnegiriStore.getSessionId() + "/profile", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(profile),
    });
  }

  async function syncState(state) {
    await ensureSession();
    return req("/session/" + global.SnegiriStore.getSessionId() + "/state", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(state),
    });
  }

  async function analyze(exerciseSlug, blob) {
    await ensureSession();
    const fd = new FormData();
    fd.append("exercise", exerciseSlug);
    fd.append("session_id", global.SnegiriStore.getSessionId());
    fd.append("video", blob, "set.webm");
    const res = await fetch(BASE + "/analyze", {
      method: "POST",
      headers: { "X-Session-Id": global.SnegiriStore.getSessionId() },
      body: fd,
    });
    if (!res.ok) throw new Error("analyze_" + res.status);
    return res.json();
  }

  global.SnegiriApi = {
    health,
    ensureSession,
    syncProfile,
    syncState,
    analyze,
  };
})(window);
