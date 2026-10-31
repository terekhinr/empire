"""Каталог проектов: TG-каналы и сайты. Без ИИ, только куда класть контент."""

from __future__ import annotations

from typing import Any

# kind: telegram | site
PROJECTS: list[dict[str, Any]] = [
    {
        "id": "tg:gdepar",
        "kind": "telegram",
        "persona": "gdepar",
        "label": "Telegram · Где Пар",
        "hint": "Канал бани. Слоты по умолчанию — как в текущей матрице 11/15/21.",
    },
    {
        "id": "tg:pension",
        "kind": "telegram",
        "persona": "pension",
        "label": "Telegram · На пенсию никогда",
        "hint": "Автопост выключен. Слоты задаёте здесь сами.",
    },
    {
        "id": "tg:stern",
        "kind": "telegram",
        "persona": "stern",
        "label": "Telegram · Штерн",
        "hint": "Сейчас в конфиге — Вт/Чт 10:00.",
    },
    {
        "id": "tg:lenin",
        "kind": "telegram",
        "persona": "lenin",
        "label": "Telegram · Ленин",
        "hint": "Сейчас в конфиге — ежедневно 12:00.",
    },
    {
        "id": "tg:garden",
        "kind": "telegram",
        "persona": "garden",
        "label": "Telegram · Сад",
        "hint": "Сейчас в конфиге — 12:00 и 20:00 в отдельные дни.",
    },
    {
        "id": "site:gdepar",
        "kind": "site",
        "persona": "gdepar",
        "label": "Сайт gdepar.ru · журнал",
        "hint": "Публикация на /journal (байки на главной подтягиваются из той же ленты).",
        "public_path": "/journal",
    },
    {
        "id": "site:neverretire",
        "kind": "site",
        "persona": "pension",
        "label": "Сайт neverretire.ru · статьи",
        "hint": "Публикация в ленту /articles.",
        "public_path": "/articles",
    },
]

WEEKDAYS_RU = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")
WEEKDAY_ALIASES = {
    "пн": 0,
    "пон": 0,
    "понедельник": 0,
    "вт": 1,
    "вторник": 1,
    "ср": 2,
    "среда": 2,
    "чт": 3,
    "четверг": 3,
    "пт": 4,
    "пятница": 4,
    "сб": 5,
    "суббота": 5,
    "вс": 6,
    "воскресенье": 6,
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}

PROJECT_ALIASES = {
    "gdepar": "tg:gdepar",
    "гдепар": "tg:gdepar",
    "баня": "tg:gdepar",
    "pension": "tg:pension",
    "пенсия": "tg:pension",
    "neverretire": "site:neverretire",
    "stern": "tg:stern",
    "штерн": "tg:stern",
    "lenin": "tg:lenin",
    "ленин": "tg:lenin",
    "garden": "tg:garden",
    "сад": "tg:garden",
    "site:gdepar": "site:gdepar",
    "сайт:gdepar": "site:gdepar",
    "gdepar.ru": "site:gdepar",
    "site:neverretire": "site:neverretire",
    "сайт:пенсия": "site:neverretire",
    "tg:gdepar": "tg:gdepar",
    "tg:pension": "tg:pension",
    "tg:stern": "tg:stern",
    "tg:lenin": "tg:lenin",
    "tg:garden": "tg:garden",
}


def project_by_id(project_id: str) -> dict[str, Any] | None:
    pid = (project_id or "").strip()
    for p in PROJECTS:
        if p["id"] == pid:
            return p
    return None


def resolve_project_id(raw: str, default: str | None = None) -> str | None:
    key = (raw or "").strip().lower()
    if not key:
        return default
    if key in PROJECT_ALIASES:
        return PROJECT_ALIASES[key]
    for p in PROJECTS:
        if p["id"] == key or p["persona"] == key:
            return p["id"]
        if p["label"].lower() == key:
            return p["id"]
    return default


def parse_weekday(raw: str | int) -> int | None:
    if isinstance(raw, int):
        return raw if 0 <= raw <= 6 else None
    s = str(raw or "").strip().lower()
    if not s:
        return None
    if s.isdigit():
        n = int(s)
        # 0–6 = Пн–Вс; 1–7 = Пн–Вс (если кто пишет «1 = понедельник»)
        if 0 <= n <= 6:
            return n
        if n == 7:
            return 6
        return None
    s = s.replace(".", "").replace(",", "")
    return WEEKDAY_ALIASES.get(s[:12])


def seed_slots_from_content_config(cfg: dict) -> list[dict]:
    """Слоты TG из content_config.json + дефолты для сайтов."""
    slots: list[dict] = []
    n = 0
    for persona, pcfg in (cfg or {}).items():
        if persona.startswith("_") or not isinstance(pcfg, dict):
            continue
        project_id = f"tg:{persona}"
        if project_by_id(project_id) is None:
            continue
        topics = pcfg.get("topics") or {}
        schedule = list(pcfg.get("schedule") or [])
        seen: set[tuple[int, str]] = set()
        if isinstance(topics, dict):
            for day_key, bucket in topics.items():
                try:
                    wd = int(day_key)
                except (TypeError, ValueError):
                    continue
                if not isinstance(bucket, dict):
                    continue
                for time_s in bucket.keys():
                    t = str(time_s).strip()
                    if not t or (wd, t) in seen:
                        continue
                    seen.add((wd, t))
                    n += 1
                    slots.append(
                        {
                            "id": f"slot-{n:03d}",
                            "project_id": project_id,
                            "weekday": wd,
                            "time": t,
                            "label": "",
                            "enabled": True,
                        }
                    )
        for t in schedule:
            ts = str(t).strip()
            if not ts:
                continue
            for wd in range(7):
                if (wd, ts) in seen:
                    continue
                # Не раздуваем пустые дни: слот из schedule без topics — только если topics пуст
                if topics:
                    continue
                seen.add((wd, ts))
                n += 1
                slots.append(
                    {
                        "id": f"slot-{n:03d}",
                        "project_id": project_id,
                        "weekday": wd,
                        "time": ts,
                        "label": "",
                        "enabled": True,
                    }
                )

    site_defaults = [
        ("site:gdepar", [0, 2, 4], "10:00", "Журнал"),
        ("site:neverretire", [1, 3], "10:00", "Статья"),
    ]
    for pid, days, time_s, label in site_defaults:
        for wd in days:
            n += 1
            slots.append(
                {
                    "id": f"slot-{n:03d}",
                    "project_id": pid,
                    "weekday": wd,
                    "time": time_s,
                    "label": label,
                    "enabled": True,
                }
            )
    return slots
