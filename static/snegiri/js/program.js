/** Каталог упражнений и генератор программы v3.1 (offline-first). */
(function (global) {
  const TRACK_DAYS = { S: 84, K: 187 };
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
      name: "Наклон тазом (hip hinge)",
      cv: true,
      camera: "side",
      hint: "Камера сбоку 90°. Наклон от таза, спина нейтральна. Без маха.",
      step: 1,
    },
    K10: {
      id: "K10",
      slug: "front_squat",
      track: "K",
      name: "Присед из стойки",
      cv: true,
      camera: "side",
      hint: "Камера сбоку. Локти высоко, корпус вертикален.",
      step: 10,
    },
    K11: {
      id: "K11",
      slug: "press",
      track: "K",
      name: "Жим из стойки",
      cv: true,
      camera: "front",
      hint: "Камера 45° спереди. Корпус вертикально, без прогиба.",
      step: 11,
    },
    K12: {
      id: "K12",
      slug: "push_press",
      track: "K",
      name: "Push press",
      cv: true,
      camera: "front",
      hint: "Камера 45°. Небольшой толчок ногами, затем жим.",
      step: 12,
    },
    K13: {
      id: "K13",
      slug: "tgu_partial",
      track: "K",
      name: "Турлиш до сидения",
      cv: true,
      camera: "side",
      hint: "Камера сбоку. Локоть прямой, взгляд на гирю.",
      step: 13,
    },
    K14: {
      id: "K14",
      slug: "tgu_full",
      track: "K",
      name: "Турлиш полный",
      cv: true,
      camera: "side",
      hint: "Камера сбоку. Контроль каждого сегмента.",
      step: 14,
    },
    K15: {
      id: "K15",
      slug: "high_pull",
      track: "K",
      name: "Высокий подъём (подводка к рывку)",
      cv: true,
      camera: "side",
      hint: "Камера сбоку. Локоть вверх, гиря у груди — без фиксации над головой.",
      step: 15,
    },
    K16: {
      id: "K16",
      slug: "snatch",
      track: "K",
      name: "Рывок",
      cv: true,
      camera: "side",
      hint: "Камера сбоку. Фиксация вверху. Просов кисти — см. подсказку Руднева.",
      step: 16,
    },
    K17: {
      id: "K17",
      slug: "jerk",
      track: "K",
      name: "Толчок",
      cv: true,
      camera: "side",
      hint: "Камера сбоку. Чистый цикл из стойки.",
      step: 17,
    },
    K18: {
      id: "K18",
      slug: "complex",
      track: "K",
      name: "Связка (заброс→жим→присед)",
      cv: true,
      camera: "front",
      hint: "Камера 45°. Плавные переходы. Каширин: круговой комплекс.",
      step: 18,
    },
    K2: {
      id: "K2",
      slug: "dead_stop",
      track: "K",
      name: "Мёртвая остановка в наклоне",
      cv: true,
      camera: "side",
      hint: "Камера сбоку. Опустились — пауза 2 сек — подъём. Блуд: база до свинга.",
      step: 2,
    },
    K3: {
      id: "K3",
      slug: "goblet_squat",
      track: "K",
      name: "Присед с гирей у груди (goblet)",
      cv: true,
      camera: "side",
      hint: "Камера сбоку. Грудь открыта, пятки на полу.",
      step: 3,
    },
    K4: {
      id: "K4",
      slug: "halo",
      track: "K",
      name: "Кольцо вокруг головы (halo)",
      cv: false,
      camera: "front",
      hint: "Лёгкий вес. Плавное кольцо — мобility плеч перед стойкой.",
      step: 4,
    },
    K5: {
      id: "K5",
      slug: "rack_hold",
      track: "K",
      name: "Удержание в стойке",
      cv: true,
      camera: "front",
      hint: "Камера 45° спереди. Локти на корпус, запястья прямые. Алферова: треугольник локтей.",
      step: 5,
    },
    K6: {
      id: "K6",
      slug: "swing",
      track: "K",
      name: "Свинг двуручный",
      cv: true,
      camera: "side",
      hint: "Камера сбоку. Хип-хиндж, импульс от бёдер.",
      step: 6,
    },
    K7: {
      id: "K7",
      slug: "one_arm_swing",
      track: "K",
      name: "Свинг одноручный",
      cv: true,
      camera: "side",
      hint: "Камера сбоку. Кор не крутится, мах от таза.",
      step: 7,
    },
    K8: {
      id: "K8",
      slug: "hand_switch",
      track: "K",
      name: "Смена рук на махе",
      cv: true,
      camera: "side",
      hint: "Камера сбоку. Смена в верхней «мёртвой точке» — гиря перед собой на уровне пояса. Руднев / классика ФГОС.",
      step: 8,
    },
    K9: {
      id: "K9",
      slug: "clean",
      track: "K",
      name: "Заброс в стойку (clean)",
      cv: true,
      camera: "front",
      hint: "Камера 45° спереди. Мягкий приём, локоть близко.",
      step: 9,
    }
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
        name: "Наклон",
        dayStart: 1,
        dayEnd: 17,
        bossExerciseId: "K2",
        exerciseIds: ["K1", "K2"],
        rotation: [
          ["K1"],
          ["K1"],
          ["K1", "K2"],
          ["K1", "K2"],
          ["K2"],
          ["K1", "K2"],
          ["K2"],
        ],
      },
      {
        num: 2,
        id: "K-P2",
        name: "Присед и кольцо",
        dayStart: 18,
        dayEnd: 34,
        bossExerciseId: "K3",
        exerciseIds: ["K3", "K4", "K1"],
        rotation: [
          ["K3"],
          ["K3", "K4"],
          ["K3"],
          ["K3", "K1"],
          ["K3", "K4"],
          ["K3"],
          ["K3", "K4"],
        ],
      },
      {
        num: 3,
        id: "K-P3",
        name: "Стойка",
        dayStart: 35,
        dayEnd: 51,
        bossExerciseId: "K5",
        exerciseIds: ["K5", "K4", "K1"],
        rotation: [
          ["K5"],
          ["K5", "K4"],
          ["K5"],
          ["K5", "K1"],
          ["K5"],
          ["K5", "K4"],
          ["K5"],
        ],
      },
      {
        num: 4,
        id: "K-P4",
        name: "Свинг двуручный",
        dayStart: 52,
        dayEnd: 68,
        bossExerciseId: "K6",
        exerciseIds: ["K6", "K2", "K1"],
        rotation: [
          ["K6"],
          ["K6", "K2"],
          ["K6"],
          ["K6", "K1"],
          ["K6", "K2"],
          ["K6"],
          ["K6", "K2"],
        ],
      },
      {
        num: 5,
        id: "K-P5",
        name: "Свинг одноручный",
        dayStart: 69,
        dayEnd: 85,
        bossExerciseId: "K7",
        exerciseIds: ["K7", "K6"],
        rotation: [
          ["K7"],
          ["K7", "K6"],
          ["K7"],
          ["K7", "K6"],
          ["K7"],
          ["K7", "K6"],
          ["K7"],
        ],
      },
      {
        num: 6,
        id: "K-P6",
        name: "Смена рук",
        dayStart: 86,
        dayEnd: 102,
        bossExerciseId: "K8",
        exerciseIds: ["K8", "K7", "K6"],
        rotation: [
          ["K8"],
          ["K8", "K7"],
          ["K8"],
          ["K8", "K6"],
          ["K8", "K7"],
          ["K8"],
          ["K8", "K7"],
        ],
      },
      {
        num: 7,
        id: "K-P7",
        name: "Заброс",
        dayStart: 103,
        dayEnd: 119,
        bossExerciseId: "K9",
        exerciseIds: ["K9", "K10", "K5"],
        rotation: [
          ["K9"],
          ["K9", "K5"],
          ["K9"],
          ["K9", "K10"],
          ["K9", "K5"],
          ["K9", "K10"],
          ["K9"],
        ],
      },
      {
        num: 8,
        id: "K-P8",
        name: "Жим",
        dayStart: 120,
        dayEnd: 136,
        bossExerciseId: "K11",
        exerciseIds: ["K11", "K12", "K5"],
        rotation: [
          ["K11"],
          ["K11", "K5"],
          ["K11", "K12"],
          ["K11"],
          ["K11", "K12"],
          ["K11", "K5"],
          ["K11", "K12"],
        ],
      },
      {
        num: 9,
        id: "K-P9",
        name: "Турлиш",
        dayStart: 137,
        dayEnd: 153,
        bossExerciseId: "K14",
        exerciseIds: ["K13", "K14", "K5"],
        rotation: [
          ["K13"],
          ["K13", "K5"],
          ["K13", "K14"],
          ["K14"],
          ["K13", "K14"],
          ["K14"],
          ["K13", "K14"],
        ],
      },
      {
        num: 10,
        id: "K-P10",
        name: "Рывок",
        dayStart: 154,
        dayEnd: 170,
        bossExerciseId: "K16",
        exerciseIds: ["K15", "K16", "K6"],
        rotation: [
          ["K15"],
          ["K15", "K6"],
          ["K15", "K16"],
          ["K16"],
          ["K15", "K16"],
          ["K16"],
          ["K15", "K16"],
        ],
      },
      {
        num: 11,
        id: "K-P11",
        name: "Толчок и связка",
        dayStart: 171,
        dayEnd: 187,
        bossExerciseId: "K18",
        exerciseIds: ["K17", "K18", "K9", "K11"],
        rotation: [
          ["K17"],
          ["K17", "K11"],
          ["K17", "K18"],
          ["K18"],
          ["K17", "K18"],
          ["K18", "K9"],
          ["K18"],
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
    const ex = EXERCISES[eid];
    const slug = ex ? ex.slug : "";
    if (slug === "hip_hinge" || slug === "dead_stop" || slug === "goblet_squat") {
      return st + "×" + kbReps(phaseWeek, 6) + " повт.";
    }
    if (slug === "halo") return st + "×" + (5 + phaseWeek) + " повт. · лёгкий вес";
    if (slug === "rack_hold") return st + "×" + holdSec(phaseWeek) + " сек";
    if (slug === "swing" || slug === "one_arm_swing" || slug === "hand_switch") {
      const emom = phaseWeek >= 2 ? "EMOM " : "";
      const base = slug === "hand_switch" ? 8 : 10;
      return emom + st + "×" + kbReps(phaseWeek, base) + " повт.";
    }
    if (slug === "clean" || slug === "front_squat" || slug === "press" || slug === "push_press" || slug === "high_pull") {
      return st + "×" + (3 + phaseWeek) + " повт.";
    }
    if (slug === "tgu_partial" || slug === "tgu_full") {
      return st + "×" + (slug === "tgu_full" ? 1 : 2) + " / сторона";
    }
    if (slug === "snatch" || slug === "jerk") return st + "×" + (5 + phaseWeek) + " повт.";
    if (slug === "complex") return st + " раундов · 3–5 повт. в связке";
    return st + "×10 повт.";
  }

  function buildDay(day, track, unlockedPhase) {
    track = track || "S";
    unlockedPhase = unlockedPhase == null ? 99 : unlockedPhase;
    const maxDay = TRACK_DAYS[track];
    day = Math.max(1, Math.min(day, maxDay));
    const cal = calendarPhase(track, day);
    const phase = effectivePhase(track, day, unlockedPhase);
    const phaseLen = phase.dayEnd - phase.dayStart + 1;
    const phaseWeekMax = Math.max(1, Math.ceil(phaseLen / 7));
    let phaseWeek = Math.floor((day - phase.dayStart) / 7) + 1;
    if (phaseWeek < 1) phaseWeek = 1;
    if (phaseWeek > phaseWeekMax) phaseWeek = phaseWeekMax;
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
      weekLabel: "Фаза " + phase.num + "/" + totalPhases + " · " + phase.name + " · нед " + phaseWeek + "/" + phaseWeekMax,
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
