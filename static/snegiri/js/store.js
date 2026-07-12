/** Persistent app state (localStorage + optional server sync). */
(function (global) {
  const KEY = "snegiri_app_v1";
  const SID_KEY = "snegiri_session_id";

  const DEFAULT = {
    version: 2,
    onboarding: "splash",
    profile: {
      weightKg: null,
      waistCm: null,
      experience: "beginner",
      kettleKg: 16,
      goal: "both",
      performer: "m",
      disclaimerOk: false,
      videoConsent: false,
      spineOk: false,
    },
    currentDay: 1,
    activeTrackMode: "S",
    trackKUnlocked: false,
    kDay: 1,
    unlockedPhaseS: 1,
    unlockedPhaseK: 1,
    completedExercises: {},
    analyses: [],
    metrics: [],
    subscription: null,
    trialStartedAt: null,
    freeAnalysesUsed: 0,
    activeExercise: null,
    lastResult: null,
  };

  function load() {
    try {
      const raw = localStorage.getItem(KEY);
      if (!raw) return structuredClone(DEFAULT);
      const merged = Object.assign(structuredClone(DEFAULT), JSON.parse(raw));
      if (!merged.unlockedPhaseS) merged.unlockedPhaseS = 1;
      if (!merged.unlockedPhaseK) merged.unlockedPhaseK = 1;
      return merged;
    } catch {
      return structuredClone(DEFAULT);
    }
  }

  let state = load();

  function save() {
    localStorage.setItem(KEY, JSON.stringify(state));
    queueSync();
  }

  let syncTimer = null;
  function queueSync() {
    if (!global.SnegiriApi) return;
    clearTimeout(syncTimer);
    syncTimer = setTimeout(function () {
      global.SnegiriApi.syncProfile(state.profile).catch(function () {});
      global.SnegiriApi.syncState({
        currentDay: state.currentDay,
        trackKUnlocked: state.trackKUnlocked,
        subscription: state.subscription,
        freeAnalysesUsed: state.freeAnalysesUsed,
        metrics: state.metrics,
      }).catch(function () {});
    }, 800);
  }

  function get() {
    return state;
  }

  function patch(partial) {
    state = Object.assign(state, partial);
    save();
    return state;
  }

  function patchProfile(p) {
    state.profile = Object.assign(state.profile, p);
    save();
    return state.profile;
  }

  function dayKey(day, track) {
    return (track || "S") + ":" + day;
  }

  function isExerciseDone(day, exerciseId, track) {
    const k = dayKey(day, track);
    return (state.completedExercises[k] || []).includes(exerciseId);
  }

  function markExerciseDone(day, exerciseId, track) {
    const k = dayKey(day, track);
    if (!state.completedExercises[k]) state.completedExercises[k] = [];
    if (!state.completedExercises[k].includes(exerciseId)) {
      state.completedExercises[k].push(exerciseId);
    }
    save();
  }

  function addAnalysis(entry) {
    state.analyses.unshift(entry);
    if (state.analyses.length > 100) state.analyses.length = 100;
    save();
  }

  function avgScore(lastN) {
    const items = state.analyses.slice(0, lastN || 20);
    if (!items.length) return null;
    const sum = items.reduce(function (a, b) {
      return a + (b.score || 0);
    }, 0);
    return Math.round((sum / items.length) * 10) / 10;
  }

  function canAnalyze() {
    if (state.subscription === "active" || state.subscription === "trial") return true;
    return state.freeAnalysesUsed < 1;
  }

  function useFreeAnalysis() {
    if (state.subscription) return;
    state.freeAnalysesUsed += 1;
    save();
  }

  function startTrial() {
    if (state.subscription) return;
    state.subscription = "trial";
    state.trialStartedAt = new Date().toISOString();
    save();
  }

  function unlockedPhase(track) {
    return track === "K" ? state.unlockedPhaseK || 1 : state.unlockedPhaseS || 1;
  }

  function checkPhaseUnlock(track) {
    if (!global.SnegiriProgram) return false;
    const t = track || "S";
    const key = t === "K" ? "unlockedPhaseK" : "unlockedPhaseS";
    const maxPhases = global.SnegiriProgram.PHASES[t].length;
    let current = state[key] || 1;
    let changed = false;
    while (current < maxPhases) {
      const st = global.SnegiriProgram.phaseUnlockStatus(t, current, state.analyses);
      if (!st.ready) break;
      current += 1;
      changed = true;
    }
    if (changed) {
      state[key] = current;
      save();
    }
    return changed;
  }

  function phaseUnlockHint(track) {
    if (!global.SnegiriProgram) return null;
    const t = track || "S";
    const phaseNum = unlockedPhase(t);
    const maxPhases = global.SnegiriProgram.PHASES[t].length;
    if (phaseNum >= maxPhases) return null;
    return global.SnegiriProgram.phaseUnlockStatus(t, phaseNum, state.analyses);
  }
  function unlockTrackK(reason) {
    state.trackKUnlocked = true;
    state.kDay = state.kDay || 1;
    save();
    return reason;
  }

  function checkUnlockK() {
    if (state.trackKUnlocked) return true;
    const goal = state.profile.goal;
    if (goal === "kettle" && state.profile.spineOk) return unlockTrackK("self");
    if (state.unlockedPhaseS >= 1 && state.currentDay >= 21) return unlockTrackK("day21");
    if (state.unlockedPhaseS >= 2) return unlockTrackK("phaseS2");
    const good = state.analyses.filter(function (a) {
      return a.score >= 7;
    });
    if (good.length >= 12) return unlockTrackK("scores");
    return false;
  }

  function advanceDayIfComplete(dayPlan, track) {
    const maxDay = global.SnegiriProgram ? global.SnegiriProgram.TRACK_DAYS[track] : track === "S" ? 84 : 187;
    const all = dayPlan.exercises.every(function (ex) {
      return isExerciseDone(dayPlan.day, ex.exerciseId, track);
    });
    if (!all) return false;
    if (track === "S" && state.currentDay === dayPlan.day && state.currentDay < maxDay) {
      state.currentDay += 1;
      save();
      checkUnlockK();
      return true;
    }
    if (track === "K" && state.kDay === dayPlan.day && state.kDay < maxDay) {
      state.kDay += 1;
      save();
      return true;
    }
    return false;
  }

  function addMetric(weightKg, waistCm) {
    state.metrics.unshift({
      at: new Date().toISOString(),
      weightKg: weightKg,
      waistCm: waistCm,
    });
    if (state.metrics.length > 60) state.metrics.length = 60;
    if (weightKg) state.profile.weightKg = weightKg;
    if (waistCm) state.profile.waistCm = waistCm;
    save();
  }

  function resetProgress() {
    state.currentDay = 1;
    state.kDay = 1;
    state.trackKUnlocked = false;
    state.unlockedPhaseS = 1;
    state.unlockedPhaseK = 1;
    state.completedExercises = {};
    state.analyses = [];
    save();
  }

  function getSessionId() {
    return localStorage.getItem(SID_KEY);
  }
  function setSessionId(id) {
    localStorage.setItem(SID_KEY, id);
  }
  function clearSessionId() {
    localStorage.removeItem(SID_KEY);
  }

  function onboardingScreen() {
    const p = state.profile;
    if (state.onboarding === "done") return "home";
    if (state.onboarding === "splash") return "splash";
    if (!p.disclaimerOk) return "disclaimer";
    if (!p.weightKg || !p.waistCm) return "profile";
    if (!p.videoConsent) return "consent";
    if (!p.goal) return "goal";
    state.onboarding = "done";
    save();
    return "home";
  }

  function activeTrackMode() {
    const s = state;
    if (s.profile.goal === "kettle" && s.profile.spineOk) return "K";
    if (s.activeTrackMode === "K" && s.trackKUnlocked) return "K";
    return "S";
  }

  global.SnegiriStore = {
    get,
    patch,
    patchProfile,
    save,
    isExerciseDone,
    markExerciseDone,
    addAnalysis,
    avgScore,
    canAnalyze,
    useFreeAnalysis,
    startTrial,
    unlockTrackK,
    checkUnlockK,
    checkPhaseUnlock,
    phaseUnlockHint,
    unlockedPhase,
    advanceDayIfComplete,
    addMetric,
    resetProgress,
    getSessionId,
    setSessionId,
    clearSessionId,
    onboardingScreen,
    activeTrackMode,
  };
})(window);
