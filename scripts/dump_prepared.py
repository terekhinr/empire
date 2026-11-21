#!/usr/bin/env python3
"""Dump deterministic TTS preparation for a line-oriented corpus."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from prepare_md_for_tts import prepare_for_tts  # noqa: E402


def rows(path: Path) -> list[str]:
    result = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if path.name == "tts_gold_phrases.txt" and len(parts) < 2:
            continue
        result.append(parts[0].strip())
    return result


def main() -> int:
    path = Path(sys.argv[1])
    inputs = rows(path)
    if path.name == "tts_gold_phrases.txt" and len(inputs) != 45:
        print(f"expected 45 gold phrases, got {len(inputs)}", file=sys.stderr)
        return 2
    for source in inputs:
        prepared = prepare_for_tts(source).strip().replace("\n", " ")
        print(f"{source}\t{prepared}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
