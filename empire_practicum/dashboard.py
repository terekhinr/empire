#!/usr/bin/env python3
"""Empire Practicum — консольный дашборд прогресса студента."""

from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table
from rich.text import Text

ROOT = Path(__file__).resolve().parent
PROGRESS_PATH = ROOT / "progress.json"

STATUS_STYLE = {
    "completed": "bold green",
    "in_progress": "bold yellow",
    "not_started": "dim",
    "locked": "red",
}

STATUS_LABEL = {
    "completed": "✓ готово",
    "in_progress": "→ в работе",
    "not_started": "○ не начато",
    "locked": "🔒 закрыто",
}


def load_progress() -> dict:
    with PROGRESS_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def lesson_stats(data: dict) -> tuple[int, int]:
    total = 0
    done = 0
    for module in data["modules"].values():
        for lesson in module["lessons"].values():
            total += 1
            if lesson["status"] == "completed":
                done += 1
    return done, total


def next_lesson(data: dict) -> tuple[str, str, str] | None:
    """Вернуть (module_title, lesson_title, path) следующего незавершённого урока."""
    for module in data["modules"].values():
        if module.get("status") == "locked":
            # Модуль открывается, когда все предыдущие completed —
            # для простоты: пропускаем locked, пока в нём нет in_progress
            has_open = any(
                l["status"] in ("in_progress", "not_started", "completed")
                for l in module["lessons"].values()
            )
            if not has_open:
                continue
        for lesson in module["lessons"].values():
            if lesson["status"] != "completed":
                return module["title"], lesson["title"], lesson["path"]
    return None


def module_percent(module: dict) -> float:
    lessons = list(module["lessons"].values())
    if not lessons:
        return 0.0
    done = sum(1 for l in lessons if l["status"] == "completed")
    return 100.0 * done / len(lessons)


def main() -> None:
    console = Console()
    data = load_progress()
    done, total = lesson_stats(data)
    overall = 100.0 * done / total if total else 0.0

    console.print()
    console.print(
        Panel.fit(
            Text.from_markup(
                f"[bold cyan]Empire Practicum[/bold cyan]\n"
                f"Студент: [white]{data.get('student', '—')}[/white]\n"
                f"Уровень: [magenta]{data.get('current_level', '—')}[/magenta]\n"
                f"Старт: {data.get('started_at', '—')}"
            ),
            title="🎓 Твой прогресс",
            border_style="cyan",
        )
    )
    console.print()

    with Progress(
        TextColumn("[bold]Общий прогресс[/bold]"),
        BarColumn(bar_width=40),
        TextColumn("{task.percentage:>5.1f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("overall", total=100)
        progress.update(task, completed=overall)

    console.print(f"  Уроков завершено: [green]{done}[/green] / {total}\n")

    table = Table(title="Модули и уроки", show_lines=True)
    table.add_column("Модуль", style="cyan", no_wrap=True)
    table.add_column("%", justify="right")
    table.add_column("Урок")
    table.add_column("Статус")

    for module in data["modules"].values():
        pct = module_percent(module)
        lessons = list(module["lessons"].values())
        for i, lesson in enumerate(lessons):
            status = lesson["status"]
            table.add_row(
                module["title"] if i == 0 else "",
                f"{pct:.0f}%" if i == 0 else "",
                lesson["title"],
                Text(STATUS_LABEL.get(status, status), style=STATUS_STYLE.get(status, "")),
            )

    console.print(table)
    console.print()

    nxt = next_lesson(data)
    if nxt is None:
        console.print(
            Panel(
                "[bold green]Все уроки Модулей 1–2 пройдены![/bold green]\n"
                "Модули 3–4 появятся в следующей итерации платформы.",
                title="🏆 Поздравляем",
                border_style="green",
            )
        )
    else:
        mod_title, les_title, path = nxt
        console.print(
            Panel(
                f"Следующий шаг:\n"
                f"[bold]{mod_title}[/bold] → [yellow]{les_title}[/yellow]\n\n"
                f"Открой: [cyan]{path}/task.md[/cyan]\n"
                f"Пиши код в: [cyan]{path}/solution.py[/cyan]\n"
                f"Проверь: [white]pytest {path}/test_task.py -v[/white]",
                title="➡️ Рекомендация",
                border_style="yellow",
            )
        )
    console.print()


if __name__ == "__main__":
    main()
