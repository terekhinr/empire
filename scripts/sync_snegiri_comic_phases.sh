#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cp "$ROOT/snegiri_kb/comic_phases_data.json" "$ROOT/static/snegiri/data/comic_phases.json"
echo "OK: static/snegiri/data/comic_phases.json"
