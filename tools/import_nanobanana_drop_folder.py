#!/usr/bin/env python3
"""Импорт картинок из папки-дропа (после ручной генерации в Gemini UI).

Имена файлов: GDP-PR-001.jpg, STR-EV-001.jpg, stern_0930_ankles_13.jpg

  ./venv/bin/python tools/import_nanobanana_drop_folder.py
  ./venv/bin/python tools/import_nanobanana_drop_folder.py --src ~/Downloads/nanobanana

Копирует в пути из manifest → apply_curated_images.py
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "curated_topic_images_manifest.json"
DEFAULT_SRC = ROOT / "media" / "_nanobanana_drop"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not MANIFEST.is_file():
        print("Сначала build_nanobanana_image_manifest.py")
        return 1
    if not args.src.is_dir():
        print(f"Нет папки {args.src}")
        return 1

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_name: dict[str, dict] = {}
    for it in manifest.get("items") or []:
        if it.get("skip_nanobanana"):
            continue
        by_name[Path(it["output_file"]).name] = it
        by_name[f"{it['topic_id']}.jpg"] = it
        by_name[f"{it['topic_id']}.png"] = it
        for pid in it.get("post_ids") or []:
            by_name[f"{pid}.jpg"] = it
            by_name[f"{pid}.png"] = it

    copied = 0
    for fp in sorted(args.src.iterdir()):
        if not fp.is_file() or fp.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
            continue
        it = by_name.get(fp.name)
        if not it:
            print(f"SKIP unknown {fp.name}")
            continue
        dest = ROOT / it["output_file"]
        if args.dry_run:
            print(f"would copy {fp.name} → {dest}")
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(fp, dest)
            print(f"OK {fp.name} → {dest}")
        copied += 1

    print(f"imported {copied}")
    if copied and not args.dry_run:
        import subprocess

        subprocess.run(
            [str(ROOT / "venv" / "bin" / "python"), str(ROOT / "tools" / "apply_curated_images.py")],
            cwd=str(ROOT),
            check=False,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
