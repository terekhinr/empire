#!/usr/bin/env python3
"""Восстановить папки и пустые списки TickTick в planning.db."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from planning_ticktick_catalog import restore_ticktick_list_catalog  # noqa: E402


def main() -> None:
    result = restore_ticktick_list_catalog(create_shells=True)
    print("restore_ticktick_lists:", result)


if __name__ == "__main__":
    main()
