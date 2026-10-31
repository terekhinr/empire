"""Боковое меню Ока Саурона — те же разделы, что в dashboard.py."""

from __future__ import annotations

SECTIONS: list[tuple[str, str, list[tuple[str, str]]]] = [
    (
        "invest",
        "Инвестиции",
        [
            ("portfolio", "Портфель"),
            ("finance", "P&L · Финансы"),
            ("sales", "Продажи"),
        ],
    ),
    (
        "system",
        "Система",
        [
            ("monitoring", "Мониторинг"),
            ("flags", "Стоп-переключатели"),
        ],
    ),
    (
        "personal",
        "Личное",
        [
            ("health", "Здоровье"),
            ("planning", "Планирование"),
        ],
    ),
    (
        "content",
        "Контент и постинг",
        [
            ("moderation", "Модерация постов"),
            ("publisher", "Издательство"),
            ("longread", "Лонгриды · Дзен/VK"),
            ("obsidian", "Obsidian · практичный режим"),
            ("pension-news", "Пенсия · новости"),
            ("pension-summary", "Pension · сводка"),
            ("sources", "Источники"),
            ("spy", "Разведка · Gdepar/Stern"),
            ("shorts", "Видео · Shorts"),
            ("neurocomment", "Нейрокомментинг (TG)"),
            ("analytics", "Аналитика"),
            ("ai", "AI Insights"),
        ],
    ),
]

TITLES = {slug: title for _, _, items in SECTIONS for slug, title in items}
DEFAULT_PAGE = "monitoring"


def section_for(page: str) -> str:
    for key, _, items in SECTIONS:
        if any(slug == page for slug, _ in items):
            return key
    return "invest"
