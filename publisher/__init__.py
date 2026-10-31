"""Издательство / Ops Studio: база, матрица, автопост-бот, алерты.

ИИ только в фабрике базы (админка). Режим по умолчанию — test.
"""

from publisher.catalog import PROJECTS, project_by_id
from publisher.dispatch import tick
from publisher.parse import parse_matrix_text, parse_post_file
from publisher.schedule import assign_next_slots, week_grid
from publisher.store import Store

__all__ = [
    "PROJECTS",
    "Store",
    "assign_next_slots",
    "parse_matrix_text",
    "parse_post_file",
    "project_by_id",
    "tick",
    "week_grid",
]
