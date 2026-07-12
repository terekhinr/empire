/**
 * Снегири не гири — PWA v1.0
 */
(function () {
  const screens = document.querySelectorAll(".screen");
  const history = [];
  let activeExerciseId = null;
  let analyzeAbort = false;

  function $(sel, root) {
    return (root || document).querySelector(sel);
  }

  function show(id, push) {
    if (push !== false) {
      const cur = document.querySelector(".screen.active");
      if (cur && cur.id !== "screen-" + id) history.push(cur.id.replace("screen-", ""));
    }
    screens.forEach(function (s) {
      s.classList.toggle("active", s.id === "screen-" + id);
    });
    document.body.dataset.screen = id;
    window.scrollTo(0, 0);
    refreshScreen(id);
  }

  function back() {
    if (document.body.dataset.screen === "record") SnegiriCamera.stopPreview();
    const prev = history.pop();
    show(prev || "home", false);
  }

  function refreshScreen(id) {
    if (id === "home") SnegiriUi.renderHome($("#home-root"));
    if (id === "workout" && activeExerciseId) SnegiriUi.renderWorkout($("#workout-root"), activeExerciseId);
    if (id === "result") {
      const r = SnegiriStore.get().lastResult;
      if (r) SnegiriUi.renderResult($("#result-root"), r.data, r.exerciseId);
    }
    if (id === "progress") SnegiriUi.renderProgress($("#progress-root"));
    if (id === "subscribe") SnegiriUi.renderSubscribe($("#subscribe-root"));
    if (id === "settings") SnegiriUi.renderSettings($("#settings-root"));
    const plan = SnegiriUi.currentDayPlan();
    const badge = $("#home-week-badge");
    if (badge) badge.textContent = plan.weekLabel;
  }

  function bindNav() {
    document.querySelectorAll("[data-goto]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        show(btn.dataset.goto);
      });
    });
    document.querySelectorAll("[data-back]").forEach(function (btn) {
      btn.addEventListener("click", back);
    });
    document.querySelectorAll(".nav-item[data-goto]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        document.querySelectorAll(".nav-item").forEach(function (n) {
          n.classList.toggle("active", n === btn);
        });
      });
    });
  }

  function bindForms() {
    $("#disclaimer-form").addEventListener("submit", function (e) {
      e.preventDefault();
      SnegiriStore.patchProfile({ disclaimerOk: true });
      show("profile");
    });
    $("#profile-form").addEventListener("submit", function (e) {
      e.preventDefault();
      const fd = new FormData(e.target);
      SnegiriStore.patchProfile({
        weightKg: parseFloat(fd.get("weight")),
        waistCm: parseFloat(fd.get("waist")),
        experience: fd.get("experience"),
        kettleKg: parseInt(fd.get("kettle"), 10),
      });
      show("consent");
    });
    $("#consent-form").addEventListener("submit", function (e) {
      e.preventDefault();
      if (!e.target.querySelector('[name="consent"]').checked) return;
      SnegiriStore.patchProfile({ videoConsent: true });
      show("goal");
    });
    $("#goal-form").addEventListener("submit", function (e) {
      e.preventDefault();
      const fd = new FormData(e.target);
      const goal = fd.get("goal");
      const spineOk = fd.get("spineOk") === "on";
      SnegiriStore.patchProfile({ goal: goal, spineOk: spineOk });
      SnegiriStore.patch({ onboarding: "done" });
      if (goal === "kettle" && spineOk) {
        SnegiriStore.unlockTrackK("self");
        SnegiriStore.patch({ activeTrackMode: "K" });
      }
      SnegiriStore.startTrial();
      show("home");
    });
  }

  function bindDelegated() {
    document.body.addEventListener("click", function (e) {
      const row = e.target.closest("[data-action]");
      if (!row) return;
      const action = row.dataset.action;
      if (action === "workout") {
        activeExerciseId = row.dataset.exerciseId;
        show("workout");
      }
      if (action === "record") startRecordFlow();
      if (action === "mark-done") {
        const id = $("#workout-root").dataset.exerciseId || activeExerciseId;
        const track = SnegiriUi.activeTrack();
        const plan = SnegiriUi.currentDayPlan();
        SnegiriStore.markExerciseDone(plan.day, id, track);
        SnegiriStore.advanceDayIfComplete(plan, track);
        show("home");
      }
      if (action === "home") show("home");
      if (action === "switch-k") {
        SnegiriStore.patch({ activeTrackMode: "K", trackKUnlocked: true });
        show("home");
      }
      if (action === "trial") {
        SnegiriStore.startTrial();
        alert("Пробный период 7 дней активирован. Оплата ЮKassa — после DNS.");
        refreshScreen("subscribe");
      }
      if (action === "edit-profile") show("profile");
      if (action === "reset") {
        if (confirm("Сбросить прогресс и разборы?")) {
          SnegiriStore.resetProgress();
          show("home");
        }
      }
    });

    document.body.addEventListener("submit", function (e) {
      if (e.target.matches("[data-action=metric-form]")) {
        e.preventDefault();
        const fd = new FormData(e.target);
        SnegiriStore.addMetric(parseFloat(fd.get("weight")), parseFloat(fd.get("waist")));
        refreshScreen("progress");
      }
    });

    document.querySelectorAll(".card-select[data-goal]").forEach(function (card) {
      card.addEventListener("click", function () {
        document.querySelectorAll(".card-select[data-goal]").forEach(function (c) {
          c.classList.remove("selected");
        });
        card.classList.add("selected");
        $("#goal-input").value = card.dataset.goal;
        $("#spine-ok-row").hidden = card.dataset.goal !== "kettle";
      });
    });
  }

  async function startRecordFlow() {
    if (!SnegiriStore.canAnalyze()) {
      show("subscribe");
      return;
    }
    activeExerciseId = $("#workout-root").dataset.exerciseId || activeExerciseId;
    const ex = SnegiriProgram.getExercise(activeExerciseId);
    show("record");
    const video = $("#camera-live");
    const hint = $("#record-hint");
    const timer = $("#record-timer");
    const btn = $("#record-stop");
    hint.textContent = ex ? ex.name : "Запись";

    if (!SnegiriCamera.hasCamera()) {
      $("#camera-fallback").hidden = false;
      video.hidden = true;
      return;
    }
    $("#camera-fallback").hidden = true;
    video.hidden = false;
    try {
      await SnegiriCamera.startPreview(video);
    } catch (err) {
      $("#camera-fallback").hidden = false;
      video.hidden = true;
      return;
    }
    SnegiriCamera.setCallbacks(
      function (sec) {
        timer.textContent = SnegiriCamera.formatTime(sec);
      },
      function (blob) {
        submitVideo(blob, ex);
      }
    );
    btn.onclick = function () {
      SnegiriCamera.stopRecording();
      btn.disabled = true;
    };
    btn.disabled = false;
    SnegiriCamera.startRecording(60);
  }

  $("#upload-input").addEventListener("change", function (e) {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    const ex = SnegiriProgram.getExercise(activeExerciseId);
    submitVideo(file, ex);
  });

  async function submitVideo(blob, ex) {
    SnegiriCamera.stopPreview();
    show("analyzing");
    const fill = $(".analyzing-fill");
    const status = $(".analyzing-status");
    let pct = 0;
    analyzeAbort = false;
    const tick = setInterval(function () {
      pct = Math.min(92, pct + 5);
      if (fill) fill.style.width = pct + "%";
      if (status) status.textContent = pct < 40 ? "Загрузка…" : pct < 75 ? "Скелет · углы" : "Сводка…";
    }, 150);

    let result;
    try {
      result = await SnegiriApi.analyze(ex.slug, blob);
    } catch (_) {
      result = localAnalyze(ex);
    }
    clearInterval(tick);
    if (fill) fill.style.width = "100%";
    if (!SnegiriStore.get().subscription) SnegiriStore.useFreeAnalysis();
    const track = SnegiriUi.activeTrack();
    const plan = SnegiriUi.currentDayPlan();
    SnegiriStore.addAnalysis({
      score: result.score,
      exercise: ex.slug,
      exerciseId: ex.id,
      track: track,
      at: new Date().toISOString(),
    });
    SnegiriStore.markExerciseDone(plan.day, ex.id, track);
    SnegiriStore.advanceDayIfComplete(plan, track);
    SnegiriStore.checkUnlockK();
    SnegiriStore.checkPhaseUnlock(track);
    SnegiriStore.patch({
      lastResult: { data: result, exerciseId: ex.id },
    });
    setTimeout(function () {
      show("result");
    }, 400);
  }

  function localAnalyze(ex) {
    const score = 5 + Math.random() * 4;
    return {
      score: Math.round(score * 10) / 10,
      max: 10,
      engine: "offline",
      issues: [{ text: "Офлайн-режим: подключите API для точного разбора.", severity: "error" }],
      positives: [{ text: "Видео принято.", severity: "ok" }],
      exercise: ex.slug,
    };
  }

  async function boot() {
    bindNav();
    bindForms();
    bindDelegated();
    try {
      await SnegiriApi.health();
      await SnegiriApi.ensureSession();
    } catch (_) {}
    const start = SnegiriStore.onboardingScreen();
    show(start, false);
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("sw.js?v=9").catch(function () {});
    }
  }

  boot();
})();
