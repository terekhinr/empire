"""Каталог списков TickTick: папки, порядок, описания."""

from __future__ import annotations

from planning_db import ensure_project, get_connection, init_db

FOLDER_PERSONAL = "ЛИЧНЫЕ ЦЕЛИ"
FOLDER_ARCHIVE = "Архивный список"
FOLDER_EMPIRE = "Empire"

# (название списка, sort_order внутри папки)
PERSONAL_LISTS: list[tuple[str, int]] = [
    ("Инкубатор мыслей", 10),
    ("Чек-листы", 20),
    ("Проекты", 30),
    ("Цели", 40),
    ("Информация", 50),
    ("Когда-нибудь", 60),
]

ARCHIVE_LISTS: list[tuple[str, int]] = [
    ("На этой неделе", 10),
    ("Купить_заказать", 20),
    ("Позже", 30),
]

EMPIRE_PREFIXES = (
    "Empire ·",
    "Bridge ·",
    "Где Пар ·",
    "Пенсия ·",
    "Метрики ·",
    "Инфра ·",
    "Спутники ",
    "Тех ·",
    "Штерн ·",
)

PROJECT_GUIDES: dict[str, str] = {
    "Инкубатор мыслей": (
        "Идеи и гипотезы «на подумать»: бизнес, контент, эксперименты. "
        "Не срочные действия — инкубатор перед переносом в Проекты или Когда-нибудь."
    ),
    "Информация": (
        "Справочник: факты о детях, книги, цитаты, ссылки. "
        "Чаще «помнить», чем «сделать»; при необходимости превращать в задачу с датой."
    ),
    "Когда-нибудь": (
        "Someday/Maybe (GTD): интересно, но без обязательства и срока. "
        "Раз в квартал просматривать — активировать или удалить."
    ),
    "На этой неделе": (
        "Фокус текущей недели. Держать 3–7 пунктов; в конце недели — в Выполнено или перенос."
    ),
    "Проекты": (
        "Многошаговые дела с планом и результатом (диссертация, завещание, запуск). "
        "У каждого — подзадачи или чек-лист этапов."
    ),
    "Цели": (
        "Долгосрочные ориентиры (доход, семья, здоровье, навыки). "
        "Без жёсткого дедлайна; декомпозировать в проекты и задачи."
    ),
    "Чек-листы": (
        "Шаблоны повторяющихся процедур (командировка, сплав, уборка). "
        "В Empire — раздел «Чеклисты»; здесь остаются только ссылки/напоминания при необходимости."
    ),
    "Позже": (
        "Отложенные задачи из TickTick (архивный список). "
        "Разбирать при появлении времени или переносить в активные списки."
    ),
    "Купить_заказать": (
        "Покупки и заказы без срочной даты. "
        "При появлении дедлайна — перенести в «На этой неделе» или Входящие."
    ),
}


def empire_folder_for_title(title: str) -> str | None:
    t = (title or "").strip()
    if any(t.startswith(p) for p in EMPIRE_PREFIXES):
        return FOLDER_EMPIRE
    return None


def catalog_folder_for_list(list_name: str) -> str | None:
    name = (list_name or "").strip()
    if not name:
        return None
    for title, _ in PERSONAL_LISTS:
        if title == name:
            return FOLDER_PERSONAL
    for title, _ in ARCHIVE_LISTS:
        if title == name:
            return FOLDER_ARCHIVE
    ef = empire_folder_for_title(name)
    if ef:
        return ef
    return None


def catalog_sort_for_list(list_name: str) -> int:
    name = (list_name or "").strip()
    for title, order in PERSONAL_LISTS + ARCHIVE_LISTS:
        if title == name:
            return order
    return 500


def restore_ticktick_list_catalog(*, create_shells: bool = True) -> dict[str, int]:
    """Создать пустые списки и проставить папки/порядок как в TickTick."""
    init_db()
    shells = 0
    if create_shells:
        for title, order in PERSONAL_LISTS:
            ensure_project(
                title,
                folder_name=FOLDER_PERSONAL,
                sort_order=order,
                description=PROJECT_GUIDES.get(title),
            )
            shells += 1
        for title, order in ARCHIVE_LISTS:
            ensure_project(
                title,
                folder_name=FOLDER_ARCHIVE,
                sort_order=order,
                description=PROJECT_GUIDES.get(title),
            )
            shells += 1

    conn = get_connection()
    assigned = 0
    for row in conn.execute("SELECT id, title FROM projects").fetchall():
        title = row["title"] or ""
        folder = catalog_folder_for_list(title) or empire_folder_for_title(title)
        if not folder:
            continue
        sort_order = catalog_sort_for_list(title) if folder != FOLDER_EMPIRE else 600 + int(row["id"])
        desc = PROJECT_GUIDES.get(title)
        conn.execute(
            """
            UPDATE projects
            SET folder_name = ?, sort_order = ?,
                description = COALESCE(?, description),
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (folder, sort_order, desc, row["id"]),
        )
        assigned += 1

    conn.commit()
    conn.close()
    return {"shells_ensured": shells, "folders_assigned": assigned}
