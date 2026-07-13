#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cp "$ROOT/snegiri_kb/comic_briefs_data.json" "$ROOT/static/snegiri/data/comic_briefs.json"
echo "OK: static/snegiri/data/comic_briefs.json"
