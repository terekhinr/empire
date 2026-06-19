#!/usr/bin/env python3
"""Разовая уборка Obsidian vault на VPS: тематические папки + MOC + canvas-карта."""
from __future__ import annotations

import json
import re
import shutil
from collections import defaultdict
from datetime import date
from pathlib import Path

VAULT = Path(__file__).resolve().parents[1] / "data" / "obsidian_vault"
LOG = VAULT / "_MOC" / "reorganize-log.md"

SKIP_DIRS = {
    ".gemini",
    ".obsidian",
    "_MOC",
    "_canvas",
    "attachments",
    "Archive",
    "_archive",
    "Empire",
    "Life",
    "Проекты",
    "Контент",
    "Здоровье",
    "Личное",
    "Рецепты",
    "Культура",
}

# (relative folder, filename/content regexes)
RULES: list[tuple[str, list[str]]] = [
    ("Проекты/Медиаимперия", [
        r"Медиаимпер", r"Мастер.?ТЗ", r"Империя мультимедиа", r"Омни.?Медиа",
        r"ПЛАН блогинг", r"ПЛАН на 3 месяца", r"План и чек", r"Ближайшие цели",
        r"^Направления", r"Грубая финансовая модель", r"^growth-rf",
    ]),
    ("База знаний/Инвестирование", [
        r"Русский список", r"Индексные фонд", r"Философск", r"Корпорация Бессмертие",
        r"рассуждал.*денег", r"Большие российские", r"куда вложить",
        r"Простые и надёжные", r"[Кк]онкурент.*пенсион", r"^Индексные фонды",
        r"^оборона", r"^статью оборона",
    ]),
    ("Контент/Сценарии", [
        r"^Сценарий", r"День шакала", r"пенсию НИКОГДА", r"Повесть",
    ]),
    ("Контент/Статьи", [
        r"^Статья", r"^статью", r"соц.? ?сет", r"^ФилоСофочки",
        r"^Что делать", r"^Для ТГ", r"^Страдания",
    ]),
    ("Контент/Идеи-каналов", [
        r"^ТГ ", r"ТГ канал", r"^Канал", r"[Yy]utub", r"Ютуб", r"Дзен",
        r"неСКУФ", r"Сетка ТГ", r"Контент план", r"разоблачени", r"Один на двоих",
        r"Тонны креатива", r"именин сердца", r"Военпред", r"^Название канала",
        r"^МЦК", r"^Полезное про ТГ",
    ]),
    ("Здоровье/Бег-и-кардио", [r"^[Бб]егит", r"бегать", r"\bбег\b"]),
    ("Здоровье/Силовые", [
        r"Гиря", r"отжаться", r"присесть", r"Копьё", r"Нормативы",
        r"грыжи спины", r"[Тт]ренировки для детей",
    ]),
    ("Рецепты", [
        r"[Рр]ецепт", r"^рецепт", r"блинчик", r"рулет", r"лаваш", r"вафел",
        r"овсянка", r"Еда для Ютуб",
    ]),
    ("Проекты/Карьера", [r"Аналитик данных", r"Яндекс ЖПТ"]),
    ("Личное/Истории", [
        r"[Мм]айор", r"Кулон", r"Ильф и Петров", r"Трамвай", r"Липкие",
        r"Антресоли", r"Экологическ", r"^Рассказы майора",
    ]),
    ("Личное", [
        r"жена", r"Прага", r"Олегыч", r"деревн", r"Терёхин", r"медицин",
        r"^[Вв]стреча", r"Прозвища", r"что мне нравится", r"^Коммунизм",
        r"^Креатив", r"^Она умная", r"^Я в деревне",
    ]),
    ("Культура/Кино-книги", [
        r"фильм", r"кино", r"обзорщик", r"Одноэтажная", r"Книга автостоп",
        r"видео салон", r"Борода и Пьётр",
    ]),
]


def slug_title(text: str, max_len: int = 60) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    text = re.sub(r'[<>:"/\\|?*]', "", text)
    return (text[:max_len].rstrip(" .") or "note") + ".md"


def first_heading(body: str) -> str | None:
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("#"):
            return re.sub(r"^#+\s*", "", line).strip()
    return None


def classify(name: str, body: str = "") -> str | None:
    hay = f"{name}\n{body[:2000]}"
    for folder, patterns in RULES:
        for pat in patterns:
            if re.search(pat, hay, re.I):
                return folder
    return None


def safe_move(src: Path, dest_dir: Path, log: list[str]) -> Path | None:
    if not src.is_file():
        return None
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    if dest.resolve() == src.resolve():
        return dest
    if dest.exists():
        dup_dir = VAULT / "Archive" / "duplicates"
        dup_dir.mkdir(parents=True, exist_ok=True)
        dup = dup_dir / f"{src.stem} (dup-{date.today().isoformat()}){src.suffix}"
        shutil.move(str(src), str(dup))
        log.append(f"- dup `{src.relative_to(VAULT)}` → `{dup.relative_to(VAULT)}`")
        return None
    shutil.move(str(src), str(dest))
    log.append(f"- `{src.relative_to(VAULT)}` → `{dest.relative_to(VAULT)}`")
    return dest


def collect_md() -> list[Path]:
    out: list[Path] = []
    for p in VAULT.rglob("*.md"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.name.lower() == "readme.md":
            continue
        rel = p.relative_to(VAULT)
        if rel.parts[0] in ("Обработанные", "База знаний", "new_obsidian_2026", "_archive"):
            continue
        if rel.parts[0] == "Входящие" or len(rel.parts) == 1:
            out.append(p)
    return sorted(out)


def move_attachments(log: list[str]) -> None:
    att = VAULT / "attachments"
    att.mkdir(exist_ok=True)
    for p in list(VAULT.iterdir()):
        if p.is_file() and (
            p.name.startswith("Pasted image")
            or p.name.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))
            and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif"}
        ):
            safe_move(p, att, log)


def move_canvases(log: list[str]) -> None:
    canvas_dir = VAULT / "_canvas"
    canvas_dir.mkdir(exist_ok=True)
    renames = {
        "Планы на жисть.canvas": "карьера-планы-жизни.canvas",
        "Что и как делать начиная с понедельника.canvas": "empire-старт-понедельник.canvas",
        "ЮТУБ ПЛАН (+ТГ ПЛАН).canvas": "контент-ютуб-тг-план.canvas",
        "Ютуб  канал без лица кулинария.canvas": "контент-ютуб-кулинария.canvas",
    }
    for p in list(VAULT.rglob("*.canvas")):
        if "_canvas" in p.parts:
            continue
        name = renames.get(p.name, p.name)
        dest = canvas_dir / name
        if dest.exists() and dest != p:
            dest = canvas_dir / f"{p.stem} ({date.today().isoformat()}).canvas"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(p), str(dest))
        log.append(f"- canvas `{p.relative_to(VAULT)}` → `{dest.relative_to(VAULT)}`")


def process_inbox_and_root(log: list[str]) -> None:
    for src in collect_md():
        body = src.read_text(encoding="utf-8", errors="replace")
        name = src.name
        if name.startswith("Без названия"):
            h = first_heading(body)
            if h and len(h) > 3:
                name = slug_title(h)
            elif len(body.strip()) < 20:
                safe_move(src, VAULT / "Archive" / "empty-notes", log)
                continue
        folder = classify(name, body)
        if not folder:
            if src.parent.name == "Входящие":
                folder = "Входящие/_разобрать"
            else:
                folder = "Личное/_разобрать"
        if name != src.name:
            tmp = src.parent / name
            if not tmp.exists():
                src.rename(tmp)
                src = tmp
        safe_move(src, VAULT / folder, log)


def special_empire(log: list[str]) -> None:
    """Только файлы в корне vault — не трогаем уже лежащие в Empire/."""
    for name in ("obsidian_empire_post.md", "growth-rf-2026.md"):
        src = VAULT / name
        if src.is_file() and "Empire" not in src.parts:
            safe_move(src, VAULT / "Empire" / "_templates", log)
    inbox_growth = VAULT / "Входящие" / "growth-rf-2026.md"
    if inbox_growth.is_file():
        safe_move(inbox_growth, VAULT / "Empire" / "_scenarios", log)


def build_mocs() -> None:
    moc = VAULT / "_MOC"
    moc.mkdir(exist_ok=True)
    sections: dict[str, list[str]] = defaultdict(list)

    for p in sorted(VAULT.rglob("*.md")):
        if any(x in p.parts for x in (".gemini", "_MOC", "Archive")):
            continue
        if p.name.lower() == "readme.md":
            continue
        rel = p.relative_to(VAULT)
        top = rel.parts[0]
        link = f"[[{p.stem}|{p.stem}]]"
        if top not in sections:
            sections[top] = []
        if len(sections[top]) < 200:
            sections[top].append(link)

    home = moc.parent / "HOME.md"
    lines = [
        "# Vault — главная",
        "",
        f"> Обновлено: {date.today().isoformat()} · карта: [[_MOC/vault-map.canvas]]",
        "",
        "## Разделы",
        "",
        "| Раздел | MOC |",
        "|--------|-----|",
        "| Empire (бот, посты) | [[_MOC/Empire]] |",
        "| Life (задачи, голос) | [[_MOC/Life]] |",
        "| База знаний | [[_MOC/Knowledge]] |",
        "| Проекты | [[_MOC/Projects]] |",
        "| Контент | [[_MOC/Content]] |",
        "| Здоровье | [[_MOC/Health]] |",
        "| Личное | [[_MOC/Personal]] |",
        "| Рецепты | [[_MOC/Recipes]] |",
        "| Canvas | [[_MOC/Canvas-Index]] |",
        "",
        "```mermaid",
        "flowchart TB",
        "  HOME[HOME]",
        "  HOME --> Empire",
        "  HOME --> Life",
        "  HOME --> Knowledge[База знаний]",
        "  HOME --> Projects[Проекты]",
        "  HOME --> Content[Контент]",
        "  HOME --> Health[Здоровье]",
        "  HOME --> Personal[Личное]",
        "  Empire --> pension[pension queue]",
        "  Empire --> gdepar",
        "  Empire --> stern",
        "  Projects --> Media[Медиаимперия]",
        "  Content --> Scripts[Сценарии]",
        "  Content --> Articles[Статьи]",
        "  Knowledge --> Invest[Инвестирование]",
        "```",
        "",
    ]
    home.write_text("\n".join(lines), encoding="utf-8")

    mapping = {
        "Empire": "Empire",
        "Life": "Life",
        "База знаний": "Knowledge",
        "Проекты": "Projects",
        "Контент": "Content",
        "Здоровье": "Health",
        "Личное": "Personal",
        "Рецепты": "Recipes",
        "Обработанные": "Processed",
        "Культура": "Culture",
        "Входящие": "Inbox",
    }

    for top, title in mapping.items():
        folder = VAULT / top
        if not folder.exists():
            continue
        items: list[str] = []
        for p in sorted(folder.rglob("*.md")):
            if p.name.lower() == "readme.md" or "_MOC" in p.parts:
                continue
            rel = p.relative_to(folder)
            if len(rel.parts) > 1:
                sub = rel.parts[0]
                items.append(f"- {sub}: [[{p.stem}|{p.stem}]]")
            else:
                items.append(f"- [[{p.stem}|{p.stem}]]")
        (moc / f"{title}.md").write_text(
            f"# {top}\n\n" + "\n".join(items[:150]) + ("\n\n…" if len(items) > 150 else "") + "\n",
            encoding="utf-8",
        )

    canvas_items = []
    for p in sorted((VAULT / "_canvas").glob("*.canvas")):
        canvas_items.append(f"- [[_canvas/{p.name}|{p.stem}]]")
    (moc / "Canvas-Index.md").write_text(
        "# Canvas — карты\n\n" + "\n".join(canvas_items) + "\n",
        encoding="utf-8",
    )

    (VAULT / "Входящие" / "README.md").write_text(
        "# Входящие\n\n"
        "Сюда — быстрые заметки. Агент/VPS разносит по папкам.\n\n"
        "Не разобрано: [[Входящие/_разобрать/]]\n\n"
        "Главная: [[HOME]]\n",
        encoding="utf-8",
    )


def build_vault_canvas() -> None:
    canvas_dir = VAULT / "_canvas"
    canvas_dir.mkdir(exist_ok=True)
    nodes = [
        ("home", "text", "[[HOME|🏠 Vault HOME]]", 0, 0, 220, 60),
        ("empire", "text", "[[_MOC/Empire|Empire · бот]]", -320, 120, 200, 60),
        ("life", "text", "[[_MOC/Life|Life · задачи]]", -80, 120, 180, 60),
        ("know", "text", "[[_MOC/Knowledge|База знаний]]", 160, 120, 200, 60),
        ("proj", "text", "[[_MOC/Projects|Проекты]]", -320, 240, 200, 60),
        ("cont", "text", "[[_MOC/Content|Контент]]", -80, 240, 180, 60),
        ("health", "text", "[[_MOC/Health|Здоровье]]", 160, 240, 180, 60),
        ("pers", "text", "[[_MOC/Personal|Личное]]", -200, 360, 180, 60),
        ("rec", "text", "[[_MOC/Recipes|Рецепты]]", 40, 360, 160, 60),
        ("growth", "text", "[[Empire/_scenarios/growth-rf-2026|Рост 2026]]", 240, 360, 200, 60),
    ]
    edges = [
        ("home", "empire"), ("home", "life"), ("home", "know"),
        ("home", "proj"), ("home", "cont"), ("home", "health"),
        ("proj", "pers"), ("cont", "rec"), ("empire", "growth"),
    ]
    out_nodes = [
        {
            "id": nid,
            "type": ntype,
            "text": text,
            "x": x,
            "y": y,
            "width": w,
            "height": h,
        }
        for nid, ntype, text, x, y, w, h in nodes
    ]
    out_edges = [
        {
            "id": f"e{i}",
            "fromNode": a,
            "fromSide": "bottom",
            "toNode": b,
            "toSide": "top",
        }
        for i, (a, b) in enumerate(edges)
    ]
    path = canvas_dir / "vault-map.canvas"
    path.write_text(
        json.dumps({"nodes": out_nodes, "edges": out_edges}, ensure_ascii=False, indent="\t"),
        encoding="utf-8",
    )


def main() -> int:
    log: list[str] = [f"# Reorganize log {date.today().isoformat()}", ""]
    (VAULT / "_MOC").mkdir(parents=True, exist_ok=True)
    (VAULT / "Archive").mkdir(exist_ok=True)
    special_empire(log)
    move_attachments(log)
    process_inbox_and_root(log)
    move_canvases(log)
    build_mocs()
    build_vault_canvas()
    LOG.write_text("\n".join(log) + "\n", encoding="utf-8")
    print(f"OK: {len(log)-2} moves → {LOG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
