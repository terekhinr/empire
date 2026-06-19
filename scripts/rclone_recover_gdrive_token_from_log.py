#!/usr/bin/env python3
"""Recover rclone gdrive token JSON from a terminal log (one-time OAuth recovery)."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

CONF = Path("/root/.config/rclone/rclone.conf")
LOG = Path("/root/.cursor/projects/root-projects-empire/terminals/1.txt")


def extract_token_json(text: str) -> str:
    for marker in ('{\\"access_token', '{"access_token'):
        start = text.find(marker)
        if start < 0:
            continue
        end = text.find("<---End paste", start)
        if end < 0:
            continue
        chunk = text[start:end].rstrip()
        for suffix in ("\\n", "\n", '"', " "):
            while chunk.endswith(suffix):
                chunk = chunk[: -len(suffix)]
        raw = chunk.replace('\\"', '"')
        json.loads(raw)
        return raw
    raise SystemExit("NO_JSON_IN_LOG")


def main() -> int:
    log = Path(sys.argv[1]) if len(sys.argv) > 1 else LOG
    if not log.is_file():
        raise SystemExit(f"log not found: {log}")
    token = extract_token_json(log.read_text(encoding="utf-8", errors="replace"))
    tmp = Path("/tmp/gdrive_token_import.json")
    tmp.write_text(token, encoding="utf-8")
    tmp.chmod(0o600)
    script = Path(__file__).resolve().parents[1] / "scripts" / "rclone_import_gdrive_token.sh"
    subprocess.run(["bash", str(script), str(tmp)], check=True)
    tmp.unlink(missing_ok=True)
    print("GDRIVE_TOKEN_IMPORTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
