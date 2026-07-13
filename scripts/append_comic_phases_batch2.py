#!/usr/bin/env python3
"""Append comic_phases_data.json entries for remaining catalog slugs."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASES = ROOT / "snegiri_kb" / "comic_phases_data.json"

NEW = {
    "pallof_press": {
        "name": "Pallof press",
        "panels": 3,
        "phases": [
            ("Стойка", "Резина на уровне груди. Стоим боком к якорю.", "hips", "McGill"),
            ("Жмём", "Руки вперёд — анти-ротация. Таз не крутится.", "core", "McGill"),
            ("Ошибка: таз", "Таз поворачивается к якорю резины.", "error", "CV-разбор"),
        ],
    },
    "plank_shoulder_tap": {
        "name": "Планка с касанием плеч",
        "panels": 4,
        "phases": [
            ("Планка", "Высокая планка. Ладони под плечами.", "core", "McGill"),
            ("Касание", "Касаем противоположного плеча. Медленно.", "shoulder", "McGill"),
            ("Стабильно", "Таз не качается. Корпус как доска.", "hips", "McGill"),
            ("Ошибка: таз", "Качание таза при касании.", "error", "CV-разбор"),
        ],
    },
    "suitcase_carry": {
        "name": "Suitcase carry",
        "panels": 3,
        "phases": [
            ("Стоя", "Гиря в одной руке. Корпус вертикален.", "core", "StrongFirst"),
            ("Шаг", "Идём ровно. Плечи на одном уровне.", "hips", "StrongFirst"),
            ("Ошибка: наклон", "Наклон к гире — lateral flexion.", "error", "CV-разбор"),
        ],
    },
    "farmer_walk": {
        "name": "Farmer's walk",
        "panels": 3,
        "phases": [
            ("Старт", "Две гири. Плечи опущены, грудь открыта.", "shoulder", "StrongFirst"),
            ("Шаг", "Короткие уверенные шаги. Взгляд вперёд.", "core", "StrongFirst"),
            ("Ошибка: плечи", "Провисание плеч, шарканье.", "error", "CV-разбор"),
        ],
    },
    "halo": {
        "name": "Кольцо (halo)",
        "panels": 3,
        "phases": [
            ("Старт", "Лёгкая гиря у подбородка. Локти вниз.", "grip", "StrongFirst"),
            ("Кольцо", "Гиря описывает круг вокруг головы.", "core", "StrongFirst"),
            ("Ошибка: дуга", "Гиря далеко от головы — лишняя нагрузка.", "error", "CV-разбор"),
        ],
    },
    "rack_hold": {
        "name": "Удержание в стойке",
        "panels": 3,
        "phases": [
            ("Стойка", "Гиря на груди. Локти на корпусе.", "elbows", "Алферова"),
            ("Треугольник", "Локти и запястья — треугольник. Кисть прямая.", "grip", "Алферова"),
            ("Ошибка: локти", "Опущенные локти — гиря давит вперёд.", "error", "CV-разбор"),
        ],
    },
    "one_arm_swing": {
        "name": "Свинг одноручный",
        "panels": 5,
        "phases": [
            ("Замах", "Таз назад. Одна рука с гирей.", "hips", "Руднев"),
            ("Подрыв", "Импульс таза. Анти-ротация корпуса.", "hips", "Руднев"),
            ("Маятник", "Гиря по дуге. Корпус жёсткий.", "core", "Руднев"),
            ("Верхняя точка", "Гиря на уровне груди. Корпус вертикален.", "lumbar", "StrongFirst"),
            ("Ошибка: кручение", "Ротация корпуса — компенсация.", "error", "CV-разбор"),
        ],
    },
    "clean": {
        "name": "Заброс в стойку",
        "panels": 5,
        "phases": [
            ("Замах", "Hinge назад. Гиря между ног.", "hips", "Денисов"),
            ("Подрыв", "Импульс таза. Рука проводит гирю.", "hips", "Денисов"),
            ("Заброс", "Мягкий заброс на грудь.", "elbows", "Денисов"),
            ("Фиксация", "Стойка: локти на корпусе, кисть прямая.", "core", "StrongFirst"),
            ("Ошибка: удар", "Удар гири по предплечью.", "error", "CV-разбор"),
        ],
    },
    "front_squat": {
        "name": "Присед из стойки",
        "panels": 4,
        "phases": [
            ("Стойка", "Гиря в стойке. Локти высоко.", "elbows", "StrongFirst"),
            ("Вниз", "Присед. Колени в сторону носков.", "knees", "Руднев"),
            ("Низ", "Глубина под контролем. Пятки на полу.", "hips", "StrongFirst"),
            ("Ошибка: локти", "Локти опущены — гиря уезжает вперёд.", "error", "CV-разбор"),
        ],
    },
    "press": {
        "name": "Жим из стойки",
        "panels": 4,
        "phases": [
            ("Стойка", "Гиря на груди. Корпус вертикален.", "core", "StrongFirst"),
            ("Жмём", "Строгий жим вверх. Без отклонения назад.", "shoulder", "StrongFirst"),
            ("Верх", "Фиксация над головой. Локти выпрямлены.", "grip", "StrongFirst"),
            ("Ошибка: прогиб", "Прогиб в пояснице при жиме.", "error", "CV-разбор"),
        ],
    },
    "push_press": {
        "name": "Push press",
        "panels": 4,
        "phases": [
            ("Присед", "Лёгкий dip коленей из стойки.", "knees", "StrongFirst"),
            ("Подрыв", "Разгибание ног — импульс в гирю.", "hips", "StrongFirst"),
            ("Жим", "Дожимаем руками до фиксации.", "shoulder", "StrongFirst"),
            ("Ошибка: только руки", "Жим без ног — гиря не взлетает.", "error", "CV-разбор"),
        ],
    },
    "tgu_partial": {
        "name": "Турлиш до сидения",
        "panels": 5,
        "phases": [
            ("Лёжа", "Гиря над плечом. Прямая рука. Взгляд на гирю.", "grip", "StrongFirst"),
            ("На локоть", "Переход на локоть опорной руки.", "shoulder", "StrongFirst"),
            ("Сел", "Подъём в сидение. Гиря вертикальна.", "core", "StrongFirst"),
            ("Фиксация", "Пауза в сидении. Контроль баланса.", "core", "StrongFirst"),
            ("Ошибка: локоть", "Согнутый локоть / гиря уезжает.", "error", "CV-разбор"),
        ],
    },
    "tgu_full": {
        "name": "Турлиш полный",
        "panels": 6,
        "phases": [
            ("Лёжа", "Старт. Гиря над грудью.", "grip", "StrongFirst"),
            ("Локоть", "На локоть. Взгляд на гирю.", "shoulder", "StrongFirst"),
            ("Сед", "Подъём в сидение.", "core", "StrongFirst"),
            ("Мост", "Мост из бедра. Прямая линия.", "hips", "StrongFirst"),
            ("Встал", "Вставание. Гиря над головой.", "core", "StrongFirst"),
            ("Ошибка: дрейф", "Гиря уезжает в сторону.", "error", "CV-разбор"),
        ],
    },
    "high_pull": {
        "name": "Высокий подъём",
        "panels": 4,
        "phases": [
            ("Замах", "Hinge назад. Гиря между ног.", "hips", "Руднев"),
            ("Подрыв", "Импульс таза. Локоть высоко.", "hips", "Руднев"),
            ("Локоть", "Гиря у груди, локоть вверх. Не над головой.", "elbows", "Денисов"),
            ("Ошибка: корпус", "Ранний отклон корпуса назад.", "error", "CV-разбор"),
        ],
    },
    "snatch": {
        "name": "Рывок",
        "panels": 5,
        "phases": [
            ("Замах", "Hinge. Одна рука с гирей.", "hips", "Руднев"),
            ("Подрыв", "Импульс таза. Высокий локоть.", "hips", "Денисов"),
            ("Просов кисти", "Просов кисти под гирей.", "grip", "Руднев"),
            ("Фиксация", "Рука прямая над головой. Пауза.", "shoulder", "ФГОС"),
            ("Ошибка: локоть", "Согнутый локоть в фиксации.", "error", "CV-разбор"),
        ],
    },
    "jerk": {
        "name": "Толчок",
        "panels": 5,
        "phases": [
            ("Стойка", "Гиря в стойке. Корпус вертикален.", "core", "Денисов"),
            ("Присед", "Dip — лёгкое сгибание коленей.", "knees", "Денисов"),
            ("Подрыв", "Разгибание ног. Гиря взлетает.", "hips", "Денисов"),
            ("Фиксация", "Руки прямые. Пауза над головой.", "shoulder", "ФГОС"),
            ("Ошибка: отжим", "Отжим от груди — локти сгибаются снова.", "error", "CV-разбор"),
        ],
    },
    "complex": {
        "name": "Связка clean→press→squat",
        "panels": 6,
        "phases": [
            ("Заброс", "Clean в стойку.", "elbows", "StrongFirst"),
            ("Жим", "Press над головой.", "shoulder", "StrongFirst"),
            ("Присед", "Front squat из стойки.", "knees", "StrongFirst"),
            ("Стойка", "Возврат гири в стойку.", "core", "StrongFirst"),
            ("Связка", "Плавный переход без паузы.", "core", "StrongFirst"),
            ("Ошибка: стойка", "Сломанная стойка между элементами.", "error", "CV-разбор"),
        ],
    },
}


def phase_entry(i: int, term: str, cue: str, highlight: str, source: str, panels: int) -> dict:
    is_err = highlight == "error"
    return {
        "index": i,
        "term": term,
        **({"term_alt": "ERROR"} if is_err else {}),
        "source": source,
        "hold_ms": 3200 if is_err else 2200 + (i % 3) * 200,
        "fade_ms": 400 if is_err else 450,
        "cue": cue,
        "watch": "Красная линия CV — зона ошибки." if is_err else "Сверь с эталоном перед съёмкой.",
        "highlight": highlight,
        **({"is_error": True} if is_err else {}),
    }


def main() -> None:
    data = json.loads(PHASES.read_text(encoding="utf-8"))
    for slug, spec in NEW.items():
        panels = spec["panels"]
        data[slug] = {
            "name": spec["name"],
            "panels": panels,
            "strip": {
                "m": f"assets/comics/{slug}_m.webp",
                "f": f"assets/comics/{slug}_f.webp",
            },
            "frame_dir": f"assets/comics/frames/{slug}",
            "phases": [
                phase_entry(i + 1, term, cue, hl, src, panels)
                for i, (term, cue, hl, src) in enumerate(spec["phases"])
            ],
        }
    PHASES.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: added {len(NEW)} slugs → {PHASES}")


if __name__ == "__main__":
    main()
