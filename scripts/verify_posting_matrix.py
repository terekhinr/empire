#!/usr/bin/env python3
"""Проверка матрицы постинга на дату (по умолчанию — завтра, MSK)."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("EMPIRE_SKIP_EMBEDDINGS", "1")

_MSK = ZoneInfo("Europe/Moscow")
_WD = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")


def _load_config() -> dict:
    return json.loads((ROOT / "content_config.json").read_text(encoding="utf-8"))


def _slot_label(raw) -> str:
    if isinstance(raw, dict):
        t = raw.get("type") or raw.get("special") or "dict"
        return str(t)
    if isinstance(raw, str):
        return raw[:70] + ("…" if len(raw) > 70 else "")
    return str(raw)


async def _resolve_preview(p_key: str, raw_slot, when: datetime) -> str:
    import main as m

    topic, prebuilt, _img, seed = await m._resolve_scheduled_slot(p_key, raw_slot, when=when)
    kind = (seed or {}).get("_kind", "")
    if prebuilt:
        return f"prebuilt · {topic[:60]}"
    if kind:
        return f"LLM · {kind} · {topic[:50]}"
    return f"LLM · {topic[:60]}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Матрица Empire на день")
    ap.add_argument(
        "--date",
        help="YYYY-MM-DD (MSK), по умолчанию завтра",
    )
    args = ap.parse_args()
    if args.date:
        day = datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=_MSK)
    else:
        day = datetime.now(_MSK) + timedelta(days=1)

    cfg = _load_config()
    wd = day.weekday()
    print(f"=== Матрица на {day.strftime('%Y-%m-%d')} ({_WD[wd]}) ===\n")

    for p_key, pcfg in cfg.items():
        if p_key.startswith("_") or not isinstance(pcfg, dict):
            continue
        schedule = pcfg.get("schedule") or []
        topics = pcfg.get("topics") or {}
        day_bucket = topics.get(str(wd), {})
        if not isinstance(day_bucket, dict):
            day_bucket = {}
        print(f"## {p_key}")
        for t in schedule:
            raw = day_bucket.get(t)
            if raw is None and t in topics and not isinstance(topics.get(t), dict):
                raw = topics.get(t)
            if raw is None:
                # Как main.py sparse matrix: пустой день ≠ LLM «Свободная тема»
                print(f"  {t}  —")
                print("         → skip (нет слота в матрице дня)")
                continue
            preview = asyncio.run(_resolve_preview(p_key, raw, day))
            flag = ""
            if isinstance(raw, dict):
                st = raw.get("type", "")
                if st in ("weekly_plan", "weekly_test", "weekly_recap"):
                    flag = "  ← недельная дуга"
            print(f"  {t}  {_slot_label(raw)}{flag}")
            print(f"         → {preview}")
        print()

    ap_cfg = json.loads((ROOT / "data" / "auto_publish.json").read_text(encoding="utf-8"))
    arc = (ap_cfg.get("rubrics") or {}).get("stern_week_arc") or {}
    print("Автопост stern_week_arc:", "ВКЛ" if arc.get("enabled") else "ВЫКЛ")
    print("Глобальный autopublish:", "ВКЛ" if ap_cfg.get("enabled") else "ВЫКЛ (рубрики могут быть отдельно)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
