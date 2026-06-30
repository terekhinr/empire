#!/usr/bin/env python3
"""Replay planning/PWA file edits from agent transcript (one-time recovery)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRANSCRIPT = Path(
    "/root/.cursor/projects/root-projects-empire/agent-transcripts/"
    "c08e5574-24fe-4086-898f-6d6494707e0c/c08e5574-24fe-4086-898f-6d6494707e0c.jsonl"
)

TARGETS = {
    "planning_api.py",
    "planning_db.py",
    "planning_recurrence.py",
    "planning_stats.py",
    "planning_ticktick.py",
    "static/planning/app.js",
    "static/planning/index.html",
    "static/planning/styles.css",
    "static/planning/sw.js",
    "static/planning/manifest.json",
}


def norm(path: str) -> str:
    return path.replace("/root/projects/empire/", "").replace("\\", "/")


def main() -> int:
    if not TRANSCRIPT.is_file():
        print(f"missing transcript: {TRANSCRIPT}", file=sys.stderr)
        return 1
    contents: dict[str, str] = {}
    bases = {
        "planning_db.py": (ROOT / "planning_db.py").read_text(encoding="utf-8")
        if (ROOT / "planning_db.py").is_file()
        else "",
    }
    for line in TRANSCRIPT.read_text(encoding="utf-8").splitlines():
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("role") != "assistant":
            continue
        for part in obj.get("message", {}).get("content", []):
            if part.get("type") != "tool_use":
                continue
            inp = part.get("input") or {}
            path = norm(inp.get("path", ""))
            if path not in TARGETS:
                continue
            name = part.get("name")
            if name == "Write":
                contents[path] = inp.get("contents", "")
            elif name == "StrReplace":
                if path not in contents and path in bases and bases[path]:
                    contents[path] = bases[path]
                if path in contents:
                    old, new = inp.get("old_string"), inp.get("new_string")
                    if old is not None and new is not None and old in contents[path]:
                        contents[path] = contents[path].replace(old, new, 1)
    for path, text in contents.items():
        out = ROOT / path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"wrote {path} ({len(text)} bytes)")
    missing = TARGETS - set(contents)
    if missing:
        print("not recovered:", ", ".join(sorted(missing)), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
