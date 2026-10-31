"""CLI: python -m publisher demo|tick|seed."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from publisher.dispatch import tick
from publisher.parse import parse_matrix_text, parse_post_file
from publisher.schedule import assign_next_slots
from publisher.store import Store, new_id, utc_now_iso

MSK = ZoneInfo("Europe/Moscow")
ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "data" / "publisher" / "examples"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Empire Ops Studio: tick / demo / status")
    p.add_argument("--store", default="", help="Путь к store.json")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("tick", help="Обработать наступившие слоты")
    demo = sub.add_parser("demo", help="Тестовый прогон на примерах")
    demo.add_argument("--keep", action="store_true", help="Писать в data/publisher/store.json")
    sub.add_parser("status", help="Краткая сводка очереди")
    args = p.parse_args(argv)

    store = Store(Path(args.store) if args.store else None)
    if args.cmd == "tick":
        result = tick(store)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "status":
        data = store.load()
        print(f"режим: {data.get('mode', 'test')}")
        print(f"слотов: {len(data.get('slots') or [])}")
        print(f"постов: {len(data.get('posts') or [])}")
        for p_item in (data.get("posts") or [])[:20]:
            print(
                f"  {p_item.get('status'):12}  {p_item.get('scheduled_at')}  "
                f"{p_item.get('project_id')}  {p_item.get('title', '')[:50]}"
            )
        return 0
    if args.cmd == "demo":
        return run_demo(store if args.keep else Store(_demo_store_path(store)))
    return 1


def _demo_store_path(store: Store) -> Path:
    return store.path.parent / "demo_store.json"


def run_demo(store: Store) -> int:
    """Залить примеры, назначить слоты, тикнуть «как будто время наступило»."""
    store.path.parent.mkdir(parents=True, exist_ok=True)
    if store.path.exists():
        store.path.unlink()
    data = store.load()
    data["mode"] = "test"
    data["posts"] = []
    data["outbox"] = []
    store.save(data)

    files = sorted(EXAMPLES.glob("*.md")) + sorted(EXAMPLES.glob("*.txt"))
    matrix_path = EXAMPLES / "matrix.csv"
    entries = []
    for f in files:
        entries.append(parse_post_file(f.name, f.read_text(encoding="utf-8"), default_project="tg:gdepar"))
    if matrix_path.is_file():
        entries.extend(parse_matrix_text(matrix_path.read_text(encoding="utf-8"), default_project="tg:gdepar"))

    data = store.load()
    placed = assign_next_slots(entries, data["slots"], data["posts"], after=datetime.now(MSK))
    created = 0
    errors = 0
    for item in placed:
        if item.get("error"):
            errors += 1
            print(f"  skip: {item.get('title')} ({item['error']})")
            continue
        data["posts"].append(
            {
                "id": new_id("post"),
                "project_id": item["project_id"],
                "title": item.get("title"),
                "body": item.get("body") or "",
                "source_filename": item.get("source_filename"),
                "slot_id": item.get("slot_id"),
                "scheduled_at": item.get("scheduled_at"),
                "status": "scheduled",
                "created_at": utc_now_iso(),
            }
        )
        created += 1
        print(f"  + {item['scheduled_at']}  {item['project_id']}  {item.get('title')}")
    store.save(data)

    future = datetime.now(MSK) + timedelta(days=21)
    result = tick(store, now=future)
    sent = result.get("sent") or []
    print(f"\nзалито: {created}, ошибок слота: {errors}")
    print(f"тест-отправка: {len(sent)} (режим {result.get('mode')})")
    for rec in sent:
        print(f"  [{rec.get('detail')}] {rec.get('scheduled_at')} {rec.get('project_id')} — {rec.get('title')}")
    outbox = store.path.parent / "demo_outbox.json"
    outbox.write_text(json.dumps(sent, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nstore: {store.path}")
    print(f"outbox: {outbox}")
    return 0 if sent else 1


if __name__ == "__main__":
    raise SystemExit(main())
