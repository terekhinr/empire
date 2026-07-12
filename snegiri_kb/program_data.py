"""Программа v2: трек S (12 нед) + трек K (24 нед), фазы и разблокировки."""

from __future__ import annotations

TRACK_DAYS = {"S": 84, "K": 168}
PHASE_UNLOCK_MIN_SESSIONS = 8
PHASE_UNLOCK_MIN_SCORE = 7.0
PHASE_UNLOCK_BOSS_MIN = 3

EXERCISES: dict[str, dict] = {
    # --- Track S ---
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
    # --- Track K ---
    "K1": {
        "id": "K1",
        "slug": "hip_hinge",
        "track": "K",
        "name": "Hip hinge",
        "cv": True,
        "camera": "side",
        "hint": "Камера сбоку 90°. Наклон от таза, спина нейтральна.",
    },
    "K2": {
        "id": "K2",
        "slug": "goblet_squat",
        "track": "K",
        "name": "Goblet squat",
        "cv": True,
        "camera": "side",
        "hint": "Камера сбоку. Грудь открыта, пятки на полу.",
    },
    "K3": {
        "id": "K3",
        "slug": "swing",
        "track": "K",
        "name": "Свинг двуручный",
        "cv": True,
        "camera": "side",
        "hint": "Камера сбоку. Хип-хиндж, импульс от бёдер.",
    },
    "K4": {
        "id": "K4",
        "slug": "one_arm_swing",
        "track": "K",
        "name": "Свинг одноручный",
        "cv": True,
        "camera": "side",
        "hint": "Камера сбоку. Кор не крутится, мах от таза.",
    },
    "K5": {
        "id": "K5",
        "slug": "clean",
        "track": "K",
        "name": "Заброс (clean)",
        "cv": True,
        "camera": "front",
        "hint": "Камера 45° спереди. Мягкий приём в стойку.",
    },
    "K6": {
        "id": "K6",
        "slug": "press",
        "track": "K",
        "name": "Жим из стойки",
        "cv": True,
        "camera": "front",
        "hint": "Камера 45° спереди. Корпус вертикально, без прогиба.",
    },
    "K7": {
        "id": "K7",
        "slug": "tgu_partial",
        "track": "K",
        "name": "Турлиш ½",
        "cv": True,
        "camera": "side",
        "hint": "Камера сбоку. Локоть прямой, взгляд на гирю.",
    },
    "K8": {
        "id": "K8",
        "slug": "tgu_full",
        "track": "K",
        "name": "Турлиш полный",
        "cv": True,
        "camera": "side",
        "hint": "Камера сбоку. Контроль каждого сегмента.",
    },
    "K9": {
        "id": "K9",
        "slug": "snatch",
        "track": "K",
        "name": "Рывок",
        "cv": True,
        "camera": "side",
        "hint": "Камера сбоку. Фиксация вверху.",
    },
    "K10": {
        "id": "K10",
        "slug": "jerk",
        "track": "K",
        "name": "Толчок / push press",
        "cv": True,
        "camera": "side",
        "hint": "Камера сбоку. Чистый цикл.",
    },
    "K11": {
        "id": "K11",
        "slug": "complex",
        "track": "K",
        "name": "Комplex (свинг→clean→жим)",
        "cv": True,
        "camera": "front",
        "hint": "Камера 45°. Плавные переходы без рывка.",
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
            "name": "Углы без импульса",
            "dayStart": 1,
            "dayEnd": 28,
            "bossExerciseId": "K1",
            "exerciseIds": ["K1", "K2"],
            "rotation": [
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
            "num": 2,
            "id": "K-P2",
            "name": "Баллистика",
            "dayStart": 29,
            "dayEnd": 56,
            "bossExerciseId": "K3",
            "exerciseIds": ["K3", "K4"],
            "rotation": [
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
            "num": 3,
            "id": "K-P3",
            "name": "Заброс и жим",
            "dayStart": 57,
            "dayEnd": 84,
            "bossExerciseId": "K5",
            "exerciseIds": ["K5", "K6"],
            "rotation": [
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
            "num": 4,
            "id": "K-P4",
            "name": "Турлиш",
            "dayStart": 85,
            "dayEnd": 112,
            "bossExerciseId": "K8",
            "exerciseIds": ["K7", "K8"],
            "rotation": [
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
            "num": 5,
            "id": "K-P5",
            "name": "Рывок и толчок",
            "dayStart": 113,
            "dayEnd": 140,
            "bossExerciseId": "K9",
            "exerciseIds": ["K9", "K10"],
            "rotation": [
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
            "num": 6,
            "id": "K-P6",
            "name": "Комplex / Flow",
            "dayStart": 141,
            "dayEnd": 168,
            "bossExerciseId": "K11",
            "exerciseIds": ["K11", "K3", "K5"],
            "rotation": [
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
}


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
    # Track K
    emom = phase_week >= 3
    if eid in ("K1", "K2"):
        return f"{st}×{_kb_reps(phase_week, 6)} повт."
    if eid in ("K3", "K4"):
        reps = _kb_reps(phase_week, 10)
        return f"{'EMOM ' if emom else ''}{st}×{reps} повт."
    if eid in ("K5", "K6"):
        return f"{st}×{3 + phase_week} повт."
    if eid in ("K7", "K8"):
        return f"{st}×{1 if eid == 'K8' else 2} / сторона"
    if eid in ("K9", "K10"):
        return f"{st}×{5 + phase_week} повт."
    if eid == "K11":
        return f"{st} раундов · 3–5 повт. в связке"
    return f"{st}×10 повт."


def build_day(day: int, *, track: str = "S", unlocked_phase: int = 99) -> dict:
    """День программы с учётом разблокированной фазы."""
    track = track.upper()
    max_day = TRACK_DAYS[track]
    day = max(1, min(day, max_day))
    cal = calendar_phase(track, day)
    phase = effective_phase(track, day, unlocked_phase)
    phase_week = (day - phase["dayStart"]) // 7 + 1
    if phase_week < 1:
        phase_week = 1
    if phase_week > 4:
        phase_week = 4
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
                "holdSec": _hold_sec(phase_week) if track == "S" and eid not in ("S4", "S6", "S7") else None,
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
        "bossExerciseId": phase["bossExerciseId"],
        "waitingUnlock": waiting,
        "track": track,
        "title": f"День {day}",
        "weekLabel": f"Фаза {phase['num']}/{total_phases} · {phase['name']} · нед {phase_week}/4",
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
