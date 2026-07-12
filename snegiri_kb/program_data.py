"""Программа v3.1: трек S (12 нед) + трек K (~27 нед), Блуд / Руднев / Денисов / SF."""

from __future__ import annotations

TRACK_DAYS = {"S": 84, "K": 187}
PHASE_UNLOCK_MIN_SESSIONS = 8
PHASE_UNLOCK_MIN_SCORE = 7.0
PHASE_UNLOCK_BOSS_MIN = 3

EXERCISES: dict[str, dict] = {
    # --- Track S (без изменений) ---
    "S1": {
        "id": "S1",
        "slug": "curl_up",
        "track": "S",
        "name": "Скручивание Макгилла",
        "cv": True,
        "camera": "side",
        "hint": "Камера сбоку. Поясница нейтральна, подъём грудью.",
    },
    "S2": {
        "id": "S2",
        "slug": "side_plank",
        "track": "S",
        "name": "Боковая планка",
        "cv": True,
        "camera": "front",
        "hint": "Камера спереди 45°. Прямая линия плечи–таз–колени.",
    },
    "S3": {
        "id": "S3",
        "slug": "bird_dog",
        "track": "S",
        "name": "Bird-dog",
        "cv": True,
        "camera": "side",
        "hint": "Камера сбоку. Таз не качается при вытягивании.",
    },
    "S4": {
        "id": "S4",
        "slug": "pallof_press",
        "track": "S",
        "name": "Pallof press",
        "cv": False,
        "camera": "front",
        "hint": "Эспандер или резина. Антиротация — таз не крутится.",
    },
    "S5": {
        "id": "S5",
        "slug": "plank_shoulder_tap",
        "track": "S",
        "name": "Планка с касанием плеч",
        "cv": True,
        "camera": "front",
        "hint": "Камера спереди. Таз стабилен при переносе веса.",
    },
    "S6": {
        "id": "S6",
        "slug": "suitcase_carry",
        "track": "S",
        "name": "Suitcase carry",
        "cv": True,
        "camera": "front",
        "hint": "Камера спереди/сзади. Корпус вертикально, без наклона к гире.",
    },
    "S7": {
        "id": "S7",
        "slug": "farmer_walk",
        "track": "S",
        "name": "Farmer's walk",
        "cv": True,
        "camera": "front",
        "hint": "Камера спереди. Осанка, шаг без шарканья.",
    },
    # --- Track K: подводящие → баллистика → стойка → жим → TGU → рывок → толчок ---
    "K1": {
        "id": "K1",
        "slug": "hip_hinge",
        "track": "K",
        "name": "Наклон тазом (hip hinge)",
        "cv": True,
        "camera": "side",
        "hint": "Камера сбоку 90°. Наклон от таза, спина нейтральна. Без маха.",
        "step": 1,
    },
    "K2": {
        "id": "K2",
        "slug": "dead_stop",
        "track": "K",
        "name": "Мёртвая остановка в наклоне",
        "cv": True,
        "camera": "side",
        "hint": "Камера сбоку. Опустились — пауза 2 сек — подъём. Блуд: база до свинга.",
        "step": 2,
    },
    "K3": {
        "id": "K3",
        "slug": "goblet_squat",
        "track": "K",
        "name": "Присед с гирей у груди (goblet)",
        "cv": True,
        "camera": "side",
        "hint": "Камера сбоку. Грудь открыта, пятки на полу.",
        "step": 3,
    },
    "K4": {
        "id": "K4",
        "slug": "halo",
        "track": "K",
        "name": "Кольцо вокруг головы (halo)",
        "cv": False,
        "camera": "front",
        "hint": "Лёгкий вес. Плавное кольцо — мобility плеч перед стойкой.",
        "step": 4,
    },
    "K5": {
        "id": "K5",
        "slug": "rack_hold",
        "track": "K",
        "name": "Удержание в стойке",
        "cv": True,
        "camera": "front",
        "hint": "Камера 45° спереди. Локти на корпус, запястья прямые. Алферова: треугольник локтей.",
        "step": 5,
    },
    "K6": {
        "id": "K6",
        "slug": "swing",
        "track": "K",
        "name": "Свинг двуручный",
        "cv": True,
        "camera": "side",
        "hint": "Камера сбоку. Хип-хиндж, импульс от бёдер.",
        "step": 6,
    },
    "K7": {
        "id": "K7",
        "slug": "one_arm_swing",
        "track": "K",
        "name": "Свинг одноручный",
        "cv": True,
        "camera": "side",
        "hint": "Камера сбоку. Кор не крутится, мах от таза.",
        "step": 7,
    },
    "K8": {
        "id": "K8",
        "slug": "hand_switch",
        "track": "K",
        "name": "Смена рук на махе",
        "cv": True,
        "camera": "side",
        "hint": "Камера сбоку. Смена в верхней «мёртвой точке» — гиря перед собой на уровне пояса. Руднев / классика ФГОС.",
        "step": 8,
    },
    "K9": {
        "id": "K9",
        "slug": "clean",
        "track": "K",
        "name": "Заброс в стойку (clean)",
        "cv": True,
        "camera": "front",
        "hint": "Камера 45° спереди. Мягкий приём, локоть близко.",
        "step": 9,
    },
    "K10": {
        "id": "K10",
        "slug": "front_squat",
        "track": "K",
        "name": "Присед из стойки",
        "cv": True,
        "camera": "side",
        "hint": "Камера сбоку. Локти высоко, корпус вертикален.",
        "step": 10,
    },
    "K11": {
        "id": "K11",
        "slug": "press",
        "track": "K",
        "name": "Жим из стойки",
        "cv": True,
        "camera": "front",
        "hint": "Камера 45° спереди. Корпус вертикально, без прогиба.",
        "step": 11,
    },
    "K12": {
        "id": "K12",
        "slug": "push_press",
        "track": "K",
        "name": "Push press",
        "cv": True,
        "camera": "front",
        "hint": "Камера 45°. Небольшой толчок ногами, затем жим.",
        "step": 12,
    },
    "K13": {
        "id": "K13",
        "slug": "tgu_partial",
        "track": "K",
        "name": "Турлиш до сидения",
        "cv": True,
        "camera": "side",
        "hint": "Камера сбоку. Локоть прямой, взгляд на гирю.",
        "step": 13,
    },
    "K14": {
        "id": "K14",
        "slug": "tgu_full",
        "track": "K",
        "name": "Турлиш полный",
        "cv": True,
        "camera": "side",
        "hint": "Камера сбоку. Контроль каждого сегмента.",
        "step": 14,
    },
    "K15": {
        "id": "K15",
        "slug": "high_pull",
        "track": "K",
        "name": "Высокий подъём (подводка к рывку)",
        "cv": True,
        "camera": "side",
        "hint": "Камера сбоку. Локоть вверх, гиря у груди — без фиксации над головой.",
        "step": 15,
    },
    "K16": {
        "id": "K16",
        "slug": "snatch",
        "track": "K",
        "name": "Рывок",
        "cv": True,
        "camera": "side",
        "hint": "Камера сбоку. Фиксация вверху. Просов кисти — см. подсказку Руднева.",
        "step": 16,
    },
    "K17": {
        "id": "K17",
        "slug": "jerk",
        "track": "K",
        "name": "Толчок",
        "cv": True,
        "camera": "side",
        "hint": "Камера сбоку. Чистый цикл из стойки.",
        "step": 17,
    },
    "K18": {
        "id": "K18",
        "slug": "complex",
        "track": "K",
        "name": "Связка (заброс→жим→присед)",
        "cv": True,
        "camera": "front",
        "hint": "Камера 45°. Плавные переходы. Каширин: круговой комплекс.",
        "step": 18,
    },
}

PHASES: dict[str, list[dict]] = {
    "S": [
        {
            "num": 1,
            "id": "S-P1",
            "name": "База Макгилла",
            "dayStart": 1,
            "dayEnd": 28,
            "bossExerciseId": "S3",
            "exerciseIds": ["S1", "S2", "S3"],
            "rotation": [
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
            "num": 2,
            "id": "S-P2",
            "name": "Антиротация",
            "dayStart": 29,
            "dayEnd": 56,
            "bossExerciseId": "S5",
            "exerciseIds": ["S4", "S2", "S5"],
            "rotation": [
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
            "num": 3,
            "id": "S-P3",
            "name": "Переноска",
            "dayStart": 57,
            "dayEnd": 84,
            "bossExerciseId": "S6",
            "exerciseIds": ["S6", "S7"],
            "rotation": [
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
    "K": [
        {
            "num": 1,
            "id": "K-P1",
            "name": "Наклон",
            "dayStart": 1,
            "dayEnd": 17,
            "bossExerciseId": "K2",
            "exerciseIds": ["K1", "K2"],
            "rotation": [
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
            "num": 2,
            "id": "K-P2",
            "name": "Присед и кольцо",
            "dayStart": 18,
            "dayEnd": 34,
            "bossExerciseId": "K3",
            "exerciseIds": ["K3", "K4", "K1"],
            "rotation": [
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
            "num": 3,
            "id": "K-P3",
            "name": "Стойка",
            "dayStart": 35,
            "dayEnd": 51,
            "bossExerciseId": "K5",
            "exerciseIds": ["K5", "K4", "K1"],
            "rotation": [
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
            "num": 4,
            "id": "K-P4",
            "name": "Свинг двуручный",
            "dayStart": 52,
            "dayEnd": 68,
            "bossExerciseId": "K6",
            "exerciseIds": ["K6", "K2", "K1"],
            "rotation": [
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
            "num": 5,
            "id": "K-P5",
            "name": "Свинг одноручный",
            "dayStart": 69,
            "dayEnd": 85,
            "bossExerciseId": "K7",
            "exerciseIds": ["K7", "K6"],
            "rotation": [
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
            "num": 6,
            "id": "K-P6",
            "name": "Смена рук",
            "dayStart": 86,
            "dayEnd": 102,
            "bossExerciseId": "K8",
            "exerciseIds": ["K8", "K7", "K6"],
            "rotation": [
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
            "num": 7,
            "id": "K-P7",
            "name": "Заброс",
            "dayStart": 103,
            "dayEnd": 119,
            "bossExerciseId": "K9",
            "exerciseIds": ["K9", "K10", "K5"],
            "rotation": [
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
            "num": 8,
            "id": "K-P8",
            "name": "Жим",
            "dayStart": 120,
            "dayEnd": 136,
            "bossExerciseId": "K11",
            "exerciseIds": ["K11", "K12", "K5"],
            "rotation": [
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
            "num": 9,
            "id": "K-P9",
            "name": "Турлиш",
            "dayStart": 137,
            "dayEnd": 153,
            "bossExerciseId": "K14",
            "exerciseIds": ["K13", "K14", "K5"],
            "rotation": [
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
            "num": 10,
            "id": "K-P10",
            "name": "Рывок",
            "dayStart": 154,
            "dayEnd": 170,
            "bossExerciseId": "K16",
            "exerciseIds": ["K15", "K16", "K6"],
            "rotation": [
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
            "num": 11,
            "id": "K-P11",
            "name": "Толчок и связка",
            "dayStart": 171,
            "dayEnd": 187,
            "bossExerciseId": "K18",
            "exerciseIds": ["K17", "K18", "K9", "K11"],
            "rotation": [
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
}


def _phase_week_bounds(phase: dict, day: int) -> tuple[int, int]:
    phase_len = phase["dayEnd"] - phase["dayStart"] + 1
    week_max = max(1, (phase_len + 6) // 7)
    week = (day - phase["dayStart"]) // 7 + 1
    return min(max(1, week), week_max), week_max


def calendar_phase(track: str, day: int) -> dict:
    track = track.upper()
    phases = PHASES[track]
    for p in phases:
        if p["dayStart"] <= day <= p["dayEnd"]:
            return p
    return phases[-1]


def effective_phase(track: str, day: int, unlocked_phase: int) -> dict:
    cal = calendar_phase(track, day)
    cap = min(cal["num"], max(1, unlocked_phase))
    return PHASES[track.upper()][cap - 1]


def phase_for_exercise(exercise_id: str) -> dict | None:
    ex = EXERCISES.get(exercise_id)
    if not ex:
        return None
    track = ex["track"]
    for p in PHASES[track]:
        if exercise_id in p["exerciseIds"]:
            return p
    return None


def _hold_sec(phase_week: int) -> int:
    return min(20, 5 + phase_week * 2)


def _sets(phase_week: int) -> int:
    return min(5, 3 + (phase_week - 1) // 2)


def _kb_reps(phase_week: int, base: int = 8) -> int:
    return min(20, base + phase_week * 2)


def _meta_for_exercise(eid: str, track: str, phase_week: int) -> str:
    st = _sets(phase_week)
    if track == "S":
        if eid in ("S6", "S7"):
            dist = 20 + phase_week * 5
            return f"{st}×{dist} м"
        if eid == "S4":
            return f"{st}×10 повт. / сторона"
        meta = f"{st}×{_hold_sec(phase_week)} сек"
        if eid in ("S2", "S3", "S5"):
            meta += " / сторона"
        return meta

    slug = EXERCISES[eid]["slug"]
    if slug in ("hip_hinge", "dead_stop", "goblet_squat"):
        return f"{st}×{_kb_reps(phase_week, 6)} повт."
    if slug == "halo":
        return f"{st}×{5 + phase_week} повт. · лёгкий вес"
    if slug == "rack_hold":
        return f"{st}×{_hold_sec(phase_week)} сек"
    if slug in ("swing", "one_arm_swing", "hand_switch"):
        emom = "EMOM " if phase_week >= 2 else ""
        base = 8 if slug == "hand_switch" else 10
        return f"{emom}{st}×{_kb_reps(phase_week, base)} повт."
    if slug in ("clean", "front_squat", "press", "push_press", "high_pull"):
        return f"{st}×{3 + phase_week} повт."
    if slug in ("tgu_partial", "tgu_full"):
        reps = 1 if slug == "tgu_full" else 2
        return f"{st}×{reps} / сторона"
    if slug in ("snatch", "jerk"):
        return f"{st}×{5 + phase_week} повт."
    if slug == "complex":
        return f"{st} раундов · 3–5 повт. в связке"
    return f"{st}×10 повт."


def build_day(day: int, *, track: str = "S", unlocked_phase: int = 99) -> dict:
    """День программы с учётом разблокированной фазы."""
    track = track.upper()
    max_day = TRACK_DAYS[track]
    day = max(1, min(day, max_day))
    cal = calendar_phase(track, day)
    phase = effective_phase(track, day, unlocked_phase)
    phase_week, phase_week_max = _phase_week_bounds(phase, day)
    dow = (day - 1) % 7
    ids = phase["rotation"][dow]
    waiting = cal["num"] > phase["num"]
    items = []
    for eid in ids:
        ex = EXERCISES[eid]
        items.append(
            {
                "exerciseId": eid,
                "slug": ex["slug"],
                "name": ex["name"],
                "cv": ex["cv"],
                "camera": ex["camera"],
                "meta": _meta_for_exercise(eid, track, phase_week),
                "hint": ex["hint"],
                "sets": _sets(phase_week),
                "holdSec": _hold_sec(phase_week) if ex["slug"] == "rack_hold" else None,
                "step": ex.get("step"),
            }
        )
    total_phases = len(PHASES[track])
    return {
        "day": day,
        "week": (day - 1) // 7 + 1,
        "phase": phase["num"],
        "phaseId": phase["id"],
        "phaseName": phase["name"],
        "phaseWeek": phase_week,
        "phaseWeekMax": phase_week_max,
        "bossExerciseId": phase["bossExerciseId"],
        "waitingUnlock": waiting,
        "track": track,
        "title": f"День {day}",
        "weekLabel": (
            f"Фаза {phase['num']}/{total_phases} · {phase['name']} · "
            f"нед {phase_week}/{phase_week_max}"
        ),
        "exercises": items,
    }


def full_program(track: str = "S", days: int | None = None, *, unlocked_phase: int = 99) -> list[dict]:
    track = track.upper()
    n = days if days is not None else TRACK_DAYS[track]
    return [build_day(d, track=track, unlocked_phase=unlocked_phase) for d in range(1, n + 1)]


def phase_unlock_status(
    track: str,
    phase_num: int,
    analyses: list[dict],
) -> dict:
    """Проверка готовности к следующей фазе по CV-сессиям."""
    track = track.upper()
    phases = PHASES[track]
    if phase_num >= len(phases):
        return {"ready": True, "sessions": 0, "bossSessions": 0, "bossAvg": None}
    phase = phases[phase_num - 1]
    boss_slug = EXERCISES[phase["bossExerciseId"]]["slug"]
    phase_slugs = {EXERCISES[eid]["slug"] for eid in phase["exerciseIds"]}
    good = [a for a in analyses if float(a.get("score") or 0) >= PHASE_UNLOCK_MIN_SCORE]
    in_phase = [a for a in good if a.get("exercise") in phase_slugs]
    boss = [a for a in good if a.get("exercise") == boss_slug]
    boss_avg = None
    if boss:
        boss_avg = sum(float(a["score"]) for a in boss) / len(boss)
    ready = (
        len(in_phase) >= PHASE_UNLOCK_MIN_SESSIONS
        and len(boss) >= PHASE_UNLOCK_BOSS_MIN
        and boss_avg is not None
        and boss_avg >= PHASE_UNLOCK_MIN_SCORE
    )
    return {
        "ready": ready,
        "sessions": len(in_phase),
        "bossSessions": len(boss),
        "bossAvg": round(boss_avg, 1) if boss_avg is not None else None,
        "requiredSessions": PHASE_UNLOCK_MIN_SESSIONS,
        "requiredBoss": PHASE_UNLOCK_BOSS_MIN,
        "minScore": PHASE_UNLOCK_MIN_SCORE,
        "bossExerciseId": phase["bossExerciseId"],
        "bossName": EXERCISES[phase["bossExerciseId"]]["name"],
    }
