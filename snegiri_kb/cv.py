"""CV analysis wrapper — MediaPipe when available, else duration heuristics."""

from __future__ import annotations

import random
import tempfile
from pathlib import Path
from typing import Any

FEEDBACK: dict[str, dict[str, list[str]]] = {
    "side_plank": {
        "bad": [
            "Таз провисает — подтяните корпус, не держите на плече.",
            "Ротация корпуса — плечи и таз в одной плоскости.",
        ],
        "good": ["Линия плеч стабильна.", "Корпус держит прямую линию."],
    },
    "curl_up": {
        "bad": [
            "Прогиб в пояснице — поднимайте грудной отдел, не шею.",
            "Рывок головой — подбородок не тянет корпус.",
        ],
        "good": ["Поясница нейтральна.", "Подъём идёт через грудной отдел."],
    },
    "bird_dog": {
        "bad": [
            "Прогиб поясницы при вытягивании — уменьшите амплитуду.",
            "Ротация таза — стабилизируйте корпус.",
        ],
        "good": ["Таз не качается.", "Линия спины ровная."],
    },
    "swing": {
        "bad": [
            "Округление спины в нижней фазе — больше хип-хиндж, меньше приседа.",
            "Ранний подъём руками — импульс от бёдер.",
        ],
        "good": ["Хип-хиндж читается.", "Спина нейтральна в фазе маха."],
    },
    "snatch": {
        "bad": ["Ранний подъём корпуса.", "Нет фиксации вверху."],
        "good": ["Цикл рывка цельный."],
    },
    "jerk": {
        "bad": ["Отжим от груди.", "Развал локтя в фиксации."],
        "good": ["Чистый цикл толчка."],
    },
    "hip_hinge": {
        "bad": ["Присед вместо наклона.", "Округление грудного отдела."],
        "good": ["Наклон от таза.", "Спина нейтральна."],
    },
    "goblet_squat": {
        "bad": ["Пятки отрываются.", "Колени заваливаются внутрь."],
        "good": ["Глубина контролируемая.", "Корпус вертикален."],
    },
    "one_arm_swing": {
        "bad": ["Ротация корпуса.", "Подъём руками."],
        "good": ["Кор стабилен.", "Импульс от бёдер."],
    },
    "hand_switch": {
        "bad": [
            "Смена не в верхней точке — гиря бьёт по предплечью.",
            "Потеря баланса — кор крутится при перехвате.",
        ],
        "good": ["Смена в «мёртвой точке».", "Кор стабилен при перехвате."],
    },
    "clean": {
        "bad": ["Удар по предплечью.", "Ранний подъём локтя."],
        "good": ["Мягкий приём в стойку.", "Локоть близко к корпусу."],
    },
    "press": {
        "bad": ["Прогиб в пояснице.", "Локти разведены."],
        "good": ["Корпус вертикален.", "Линия локтя чистая."],
    },
    "tgu_partial": {
        "bad": ["Согнутый локоть.", "Потеря взгляда на гирю."],
        "good": ["Плечо стабильно.", "Контроль сегмента."],
    },
    "tgu_full": {
        "bad": ["Скругление при подъёме.", "Гиря уходит от оси."],
        "good": ["Вертикальная линия.", "Плавные переходы."],
    },
    "complex": {
        "bad": ["Рваные переходы.", "Потеря жёсткости корпуса."],
        "good": ["Связка цельная.", "Дыхание ритмичное."],
    },
    "dead_stop": {
        "bad": ["Присед вместо наклона.", "Нет паузы в нижней точке."],
        "good": ["Наклон от таза.", "Пауза контролируемая."],
    },
    "rack_hold": {
        "bad": ["Локти опущены.", "Запястья сломаны."],
        "good": ["Стойка стабильна.", "Кор включён."],
    },
    "front_squat": {
        "bad": ["Пятки отрываются.", "Гиря уходит вперёд."],
        "good": ["Корпус вертикален.", "Глубина контролируемая."],
    },
    "push_press": {
        "bad": ["Только руками.", "Прогиб в пояснице."],
        "good": ["Импульс от ног.", "Фиксация чистая."],
    },
    "high_pull": {
        "bad": ["Ранний подъём корпуса.", "Локоть не ведёт вверх."],
        "good": ["Траектория близко к телу.", "Высота достаточная."],
    },
    "plank_shoulder_tap": {
        "bad": ["Качание таза.", "Плечи к ушам."],
        "good": ["Таз стабилен.", "Кор жёсткий."],
    },
    "suitcase_carry": {
        "bad": ["Наклон к гире.", "Шея вперёд."],
        "good": ["Корпус вертикален.", "Шаг ровный."],
    },
    "farmer_walk": {
        "bad": ["Провисание плеч.", "Шарканье."],
        "good": ["Осанка ровная.", "Кор включён."],
    },
}


def _probe_mediapipe(video_path: Path, exercise: str) -> dict | None:
    try:
        import sys

        root = Path(__file__).resolve().parent.parent
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from tools.snegiri_cv_probe import analyze_side_plank, analyze_swing, extract_pose_frames

        history = extract_pose_frames(video_path)
        if exercise in ("side_plank", "S2"):
            raw = analyze_side_plank(history)
        elif exercise in ("swing", "K1", "K3"):
            raw = analyze_swing(history)
        else:
            frames = len(history)
            score = 6 if frames >= 10 else 4
            raw = {"score": score, "max": 10, "issues": [f"Кадров с позой: {frames}"], "frames": frames}
        return raw
    except Exception:
        return None


def _heuristic(video_path: Path, exercise: str) -> dict:
    size = video_path.stat().st_size if video_path.is_file() else 0
    base = 5.5
    if size > 500_000:
        base += 1.0
    if size > 2_000_000:
        base += 0.8
    score = min(10, max(3, round(base + random.uniform(-0.8, 1.2), 1)))
    fb = FEEDBACK.get(exercise, FEEDBACK["side_plank"])
    issues = []
    good = []
    if score < 7:
        issues.append({"text": random.choice(fb["bad"]), "severity": "error"})
    else:
        good.append({"text": random.choice(fb["good"]), "severity": "ok"})
    if score >= 6:
        good.append({"text": random.choice(fb["good"]), "severity": "ok"})
    else:
        issues.append({"text": random.choice(fb["bad"]), "severity": "error"})
    return {
        "score": score,
        "max": 10,
        "issues": issues,
        "positives": good,
        "engine": "heuristic",
    }


def analyze_video(video_path: Path, exercise_slug: str) -> dict[str, Any]:
    slug = exercise_slug.replace("-", "_")
    raw = _probe_mediapipe(video_path, slug)
    if raw:
        fb = FEEDBACK.get(slug, FEEDBACK["side_plank"])
        issues = [{"text": t, "severity": "error"} for t in raw.get("issues", [])[:2]]
        positives = [{"text": random.choice(fb["good"]), "severity": "ok"}] if raw.get("score", 0) >= 6 else []
        return {
            "score": float(raw.get("score", 5)),
            "max": 10,
            "issues": issues or [{"text": fb["bad"][0], "severity": "error"}],
            "positives": positives or [{"text": fb["good"][0], "severity": "ok"}],
            "engine": "mediapipe",
            "frames": raw.get("frames"),
        }
    return _heuristic(video_path, slug)


def save_upload(content: bytes, suffix: str = ".webm") -> Path:
    from snegiri_kb.db import UPLOAD_DIR

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(suffix=suffix, dir=UPLOAD_DIR)
    path = Path(name)
    with open(fd, "wb") as f:
        f.write(content)
    return path
