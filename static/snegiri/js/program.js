/** Каталог упражнений и генератор программы v2 (offline-first). */
(function (global) {
  const TRACK_DAYS = { S: 84, K: 168 };
  const PHASE_UNLOCK_MIN_SESSIONS = 8;
  const PHASE_UNLOCK_MIN_SCORE = 7;
  const PHASE_UNLOCK_BOSS_MIN = 3;

  const EXERCISES = {
    S1: {
      id: "S1",
      slug: "curl_up",
      track: "S",
      name: "Скручивание Макгилла",
      cv: true,
      camera: "side",
      hint: "Камера сбоку. Поясница нейтральна, подъём грудью.",
    },
    S2: {
      id: "S2",
      slug: "side_plank",
      track: "S",
      name: "Боковая планка",
      cv: true,
      camera: "front",
      hint: "Камера спереди 45°. Прямая линия плечи–таз–колени.",
    },
    S3: {
      id: "S3",
      slug: "bird_dog",
      track: "S",
      name: "Bird-dog",
      cv: true,
      camera: "side",
      hint: "Камера сбоку. Таз не качается при вытягивании.",
    },
    S4: {
      id: "S4",
      slug: "pallof_press",
      track: "S",
      name: "Pallof press",
      cv: false,
      camera: "front",
      hint: "Эспандер или резина. Антиротация — таз не крутится.",
    },
    S5: {
      id: "S5",
      slug: "plank_shoulder_tap",
      track: "S",
      name: "Планка с касанием плеч",
      cv: true,
      camera: "front",
      hint: "Камера спереди. Таз стабилен при переносе веса.",
    },
    S6: {
      id: "S6",
      slug: "suitcase_carry",
      track: "S",
      name: "Suitcase carry",
      cv: true,
      camera: "front",
      hint: "Камера спереди/сзади. Корпус вертикально.",
    },
    S7: {
      id: "S7",
      slug: "farmer_walk",
      track: "S",
      name: "Farmer's walk",
      cv: true,
      camera: "front",
      hint: "Камера спереди. Осанка, шаг без шарканья.",
    },
    K1: {
      id: "K1",
      slug: "hip_hinge",
      track: "K",
      name: "Hip hinge",
      cv: true,
      camera: "side",
      hint: "Камера сбоку 90°. Наклон от таза, спина нейтральна.",
    },
    K2: {
      id: "K2",
      slug: "goblet_squat",
      track: "K",
      name: "Goblet squat",
      cv: true,
      camera: "side",
      hint: "Камера сбоку. Грудь открыта, пятки на полу.",
    },
    K3: {
      id: "K3",
      slug: "swing",
      track: "K",
      name: "Свинг двуручный",
      cv: true,
      camera: "side",
      hint: "Камера сбоку. Хип-хиндж, импульс от бёдер.",
    },
    K4: {
      id: "K4",
      slug: "one_arm_swing",
      track: "K",
      name: "Свинг одноручный",
      cv: true,
      camera: "side",
      hint: "Камера сбоку. Кор не крутится.",
    },
    K5: {
      id: "K5",
      slug: "clean",
      track: "K",
      name: "Заброс (clean)",
      cv: true,
      camera: "front",
      hint: "Камера 45° спереди. Мягкий приём в стойку.",
    },
    K6: {
      id: "K6",
      slug: "press",
      track: "K",
      name: "Жим из стойки",
      cv: true,
      camera: "front",
      hint: "Камера 45° спереди. Корпус вертикально.",
    },
    K7: {
      id: "K7",
      slug: "tgu_partial",
      track: "K",
      name: "Турлиш ½",
      cv: true,
      camera: "side",
      hint: "Камера сбоку. Локоть прямой, взгляд на гирю.",
    },
    K8: {
      id: "K8",
      slug: "tgu_full",
      track: "K",
      name: "Турлиш полный",
      cv: true,
      camera: "side",
      hint: "Камера сбоку. Контроль каждого сегмента.",
    },
    K9: {
      id: "K9",
      slug: "snatch",
      track: "K",
      name: "Рывок",
      cv: true,
      camera: "side",
      hint: "Камера сбоку. Фиксация вверху.",
    },
    K10: {
      id: "K10",
      slug: "jerk",
      track: "K",
      name: "Толчок / push press",
      cv: true,
      camera: "side",
      hint: "Камера сбоку. Чистый цикл.",
    },
    K11: {
      id: "K11",
      slug: "complex",
      track: "K",
      name: "Комplex (свинг→clean→жим)",
      cv: true,
      camera: "front",
      hint: "Камера 45°. Плавные переходы.",
    },
  };

  const PHASES = {
    S: [
      {
        num: 1,
        id: "S-P1",
        name: "База Макгилла",
        dayStart: 1,
        dayEnd: 28,
        bossExerciseId: "S3",
        exerciseIds: ["S1", "S2", "S3"],
        rotation: [
          ["S1", "S2"],
          ["S2", "S3"],
          ["S1", "S3"],
          ["S2", "S3"],
          ["S1", "S2", "S3"],
          ["S2", "S3"],
          ["S1", "S3"],
        ],
      },
      {
        num: 2,
        id: "S-P2",
        name: "Антиротация",
        dayStart: 29,
        dayEnd: 56,
        bossExerciseId: "S5",
        exerciseIds: ["S4", "S2", "S5"],
        rotation: [
          ["S5", "S2"],
          ["S5", "S4"],
          ["S2", "S5"],
          ["S4", "S5"],
          ["S2", "S4", "S5"],
          ["S5"],
          ["S2", "S5"],
        ],
      },
      {
        num: 3,
        id: "S-P3",
        name: "Переноска",
        dayStart: 57,
        dayEnd: 84,
        bossExerciseId: "S6",
        exerciseIds: ["S6", "S7"],
        rotation: [
          ["S6", "S7"],
          ["S6"],
          ["S7", "S6"],
          ["S6", "S7"],
          ["S6"],
          ["S7"],
          ["S6", "S7"],
        ],
      },
    ],
    K: [
      {
        num: 1,
        id: "K-P1",
        name: "Углы без импульса",
        dayStart: 1,
        dayEnd: 28,
        bossExerciseId: "K1",
        exerciseIds: ["K1", "K2"],
        rotation: [
          ["K1"],
          ["K1", "K2"],
          ["K2"],
          ["K1", "K2"],
          ["K1"],
          ["K2"],
          ["K1", "K2"],
        ],
      },
      {
        num: 2,
        id: "K-P2",
        name: "Баллистика",
        dayStart: 29,
        dayEnd: 56,
        bossExerciseId: "K3",
        exerciseIds: ["K3", "K4"],
        rotation: [
          ["K3"],
          ["K3", "K4"],
          ["K3"],
          ["K3", "K4"],
          ["K3"],
          ["K3", "K4"],
          ["K3", "K4"],
        ],
      },
      {
        num: 3,
        id: "K-P3",
        name: "Заброс и жим",
        dayStart: 57,
        dayEnd: 84,
        bossExerciseId: "K5",
        exerciseIds: ["K5", "K6"],
        rotation: [
          ["K5"],
          ["K5", "K6"],
          ["K5"],
          ["K5", "K6"],
          ["K5"],
          ["K5", "K6"],
          ["K5", "K6"],
        ],
      },
      {
        num: 4,
        id: "K-P4",
        name: "Турлиш",
        dayStart: 85,
        dayEnd: 112,
        bossExerciseId: "K8",
        exerciseIds: ["K7", "K8"],
        rotation: [
          ["K7"],
          ["K7", "K8"],
          ["K7"],
          ["K7", "K8"],
          ["K8"],
          ["K7", "K8"],
          ["K8"],
        ],
      },
      {
        num: 5,
        id: "K-P5",
        name: "Рывок и толчок",
        dayStart: 113,
        dayEnd: 140,
        bossExerciseId: "K9",
        exerciseIds: ["K9", "K10"],
        rotation: [
          ["K9"],
          ["K9", "K10"],
          ["K9"],
          ["K9", "K10"],
          ["K9"],
          ["K9", "K10"],
          ["K9", "K10"],
        ],
      },
      {
        num: 6,
        id: "K-P6",
        name: "Комplex / Flow",
        dayStart: 141,
        dayEnd: 168,
        bossExerciseId: "K11",
        exerciseIds: ["K11", "K3", "K5"],
        rotation: [
          ["K11"],
          ["K11", "K3"],
          ["K11"],
          ["K11", "K5"],
          ["K11"],
          ["K11", "K3", "K5"],
          ["K11"],
        ],
      },
    ],
  };

  function calendarPhase(track, day) {
    const phases = PHASES[track];
    for (let i = 0; i < phases.length; i++) {
      const p = phases[i];
      if (day >= p.dayStart && day <= p.dayEnd) return p;
    }
    return phases[phases.length - 1];
  }

  function effectivePhase(track, day, unlockedPhase) {
    const cal = calendarPhase(track, day);
    const cap = Math.min(cal.num, Math.max(1, unlockedPhase || 1));
    return PHASES[track][cap - 1];
  }

  function holdSec(phaseWeek) {
    return Math.min(20, 5 + phaseWeek * 2);
  }
  function sets(phaseWeek) {
    return Math.min(5, 3 + Math.floor((phaseWeek - 1) / 2));
  }
  function kbReps(phaseWeek, base) {
    base = base || 8;
    return Math.min(20, base + phaseWeek * 2);
  }

  function metaForExercise(eid, track, phaseWeek) {
    const st = sets(phaseWeek);
    if (track === "S") {
      if (eid === "S6" || eid === "S7") return st + "×" + (20 + phaseWeek * 5) + " м";
      if (eid === "S4") return st + "×10 повт. / сторона";
      let meta = st + "×" + holdSec(phaseWeek) + " сек";
      if (eid === "S2" || eid === "S3" || eid === "S5") meta += " / сторона";
      return meta;
    }
    const emom = phaseWeek >= 3;
    if (eid === "K1" || eid === "K2") return st + "×" + kbReps(phaseWeek, 6) + " повт.";
    if (eid === "K3" || eid === "K4") {
      return (emom ? "EMOM " : "") + st + "×" + kbReps(phaseWeek, 10) + " повт.";
    }
    if (eid === "K5" || eid === "K6") return st + "×" + (3 + phaseWeek) + " повт.";
    if (eid === "K7" || eid === "K8") return st + "×" + (eid === "K8" ? 1 : 2) + " / сторона";
    if (eid === "K9" || eid === "K10") return st + "×" + (5 + phaseWeek) + " повт.";
    if (eid === "K11") return st + " раундов · 3–5 повт. в связке";
    return st + "×10 повт.";
  }

  function buildDay(day, track, unlockedPhase) {
    track = track || "S";
    unlockedPhase = unlockedPhase == null ? 99 : unlockedPhase;
    const maxDay = TRACK_DAYS[track];
    day = Math.max(1, Math.min(day, maxDay));
    const cal = calendarPhase(track, day);
    const phase = effectivePhase(track, day, unlockedPhase);
    let phaseWeek = Math.floor((day - phase.dayStart) / 7) + 1;
    if (phaseWeek < 1) phaseWeek = 1;
    if (phaseWeek > 4) phaseWeek = 4;
    const dow = (day - 1) % 7;
    const ids = phase.rotation[dow];
    const waiting = cal.num > phase.num;
    const exercises = ids.map(function (eid) {
      const ex = EXERCISES[eid];
      return {
        exerciseId: eid,
        slug: ex.slug,
        name: ex.name,
        cv: ex.cv,
        camera: ex.camera,
        meta: metaForExercise(eid, track, phaseWeek),
        hint: ex.hint,
      };
    });
    const totalPhases = PHASES[track].length;
    return {
      day: day,
      week: Math.ceil(day / 7),
      phase: phase.num,
      phaseId: phase.id,
      phaseName: phase.name,
      phaseWeek: phaseWeek,
      bossExerciseId: phase.bossExerciseId,
      waitingUnlock: waiting,
      track: track,
      title: "День " + day,
      weekLabel: "Фаза " + phase.num + "/" + totalPhases + " · " + phase.name + " · нед " + phaseWeek + "/4",
      exercises: exercises,
    };
  }

  function phaseUnlockStatus(track, phaseNum, analyses) {
    const phases = PHASES[track];
    if (phaseNum >= phases.length) {
      return { ready: true, sessions: 0, bossSessions: 0, bossAvg: null };
    }
    const phase = phases[phaseNum - 1];
    const bossSlug = EXERCISES[phase.bossExerciseId].slug;
    const phaseSlugs = {};
    phase.exerciseIds.forEach(function (eid) {
      phaseSlugs[EXERCISES[eid].slug] = true;
    });
    const good = (analyses || []).filter(function (a) {
      return (a.score || 0) >= PHASE_UNLOCK_MIN_SCORE;
    });
    const inPhase = good.filter(function (a) {
      return phaseSlugs[a.exercise];
    });
    const boss = good.filter(function (a) {
      return a.exercise === bossSlug;
    });
    let bossAvg = null;
    if (boss.length) {
      bossAvg =
        Math.round(
          (boss.reduce(function (s, a) {
            return s + a.score;
          }, 0) /
            boss.length) *
            10
        ) / 10;
    }
    const ready =
      inPhase.length >= PHASE_UNLOCK_MIN_SESSIONS &&
      boss.length >= PHASE_UNLOCK_BOSS_MIN &&
      bossAvg != null &&
      bossAvg >= PHASE_UNLOCK_MIN_SCORE;
    return {
      ready: ready,
      sessions: inPhase.length,
      bossSessions: boss.length,
      bossAvg: bossAvg,
      requiredSessions: PHASE_UNLOCK_MIN_SESSIONS,
      requiredBoss: PHASE_UNLOCK_BOSS_MIN,
      minScore: PHASE_UNLOCK_MIN_SCORE,
      bossExerciseId: phase.bossExerciseId,
      bossName: EXERCISES[phase.bossExerciseId].name,
    };
  }

  function getExercise(id) {
    return EXERCISES[id] || null;
  }

  global.SnegiriProgram = {
    EXERCISES: EXERCISES,
    PHASES: PHASES,
    TRACK_DAYS: TRACK_DAYS,
    buildDay: buildDay,
    getExercise: getExercise,
    calendarPhase: calendarPhase,
    effectivePhase: effectivePhase,
    phaseUnlockStatus: phaseUnlockStatus,
  };
})(typeof window !== "undefined" ? window : globalThis);
