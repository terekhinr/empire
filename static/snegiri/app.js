/**
 * snegirinegi.ru — интерактивный макет v0.2
 * Навигация: data-goto="screen-id" · localStorage для онбординга
 */
(function () {
  const STORAGE = "snegiri_mock_v02";
  const screens = document.querySelectorAll(".screen");
  const dots = document.querySelectorAll(".screen-dots .dot");
  const history = [];
  let analyzeTimer = null;

  function loadState() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE) || "{}");
    } catch {
      return {};
    }
  }

  function saveState(patch) {
    const next = { ...loadState(), ...patch };
    localStorage.setItem(STORAGE, JSON.stringify(next));
    return next;
  }

  function show(id, push = true) {
    const el = document.getElementById("screen-" + id);
    if (!el) return;
    const cur = document.querySelector(".screen.active");
    if (push && cur && cur.id !== "screen-" + id) {
      history.push(cur.id.replace("screen-", ""));
    }
    if (analyzeTimer) {
      clearInterval(analyzeTimer);
      analyzeTimer = null;
    }
    screens.forEach((s) => s.classList.remove("active"));
    el.classList.add("active");
    const idx = Array.from(screens).indexOf(el);
    dots.forEach((d, i) => d.classList.toggle("active", i === idx));
    window.scrollTo(0, 0);

    if (id === "analyzing") startAnalyzeDemo();
    if (id === "disclaimer") saveState({ lastScreen: "disclaimer" });
    if (id === "home") saveState({ onboarded: true });
  }

  function back() {
    const prev = history.pop();
    if (prev) show(prev, false);
    else show("home", false);
  }

  function startAnalyzeDemo() {
    const fill = document.querySelector(".analyzing-fill");
    const status = document.querySelector(".analyzing-status");
    if (!fill) {
      setTimeout(() => show("result", false), 2200);
      return;
    }
    let pct = 0;
    fill.style.width = "0%";
    analyzeTimer = setInterval(() => {
      pct = Math.min(100, pct + 4 + Math.random() * 6);
      fill.style.width = pct + "%";
      if (status) {
        if (pct < 40) status.textContent = "Очередь · ~25 сек";
        else if (pct < 75) status.textContent = "Скелет · углы таза";
        else status.textContent = "Сводка ошибок…";
      }
      if (pct >= 100) {
        clearInterval(analyzeTimer);
        analyzeTimer = null;
        setTimeout(() => show("result", false), 400);
      }
    }, 120);
  }

  document.querySelectorAll("[data-goto]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.goto;
      if (target === "disclaimer") saveState({ splashSeen: true });
      if (target === "goal") saveState({ disclaimerOk: true });
      show(target);
    });
  });

  document.querySelectorAll("[data-back]").forEach((btn) => {
    btn.addEventListener("click", back);
  });

  document.querySelectorAll(".card-select[data-track]").forEach((card) => {
    card.addEventListener("click", () => {
      document.querySelectorAll(".card-select[data-track]").forEach((c) => c.classList.remove("selected"));
      card.classList.add("selected");
      saveState({ track: card.dataset.track });
    });
  });

  dots.forEach((dot, i) => {
    dot.addEventListener("click", () => {
      const id = screens[i]?.id?.replace("screen-", "");
      if (id) show(id, false);
    });
  });

  const state = loadState();
  if (state.track) {
    document.querySelectorAll(".card-select[data-track]").forEach((c) => {
      c.classList.toggle("selected", c.dataset.track === state.track);
    });
  }

  let start = "splash";
  if (state.onboarded) start = "home";
  else if (state.disclaimerOk) start = "goal";
  else if (state.splashSeen) start = "disclaimer";

  show(start, false);
})();
