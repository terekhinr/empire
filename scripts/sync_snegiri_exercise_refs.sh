#!/usr/bin/env bash
# Синхронизация exercise_refs_data.json → static для лендинга (offline JSON).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cp "$ROOT/snegiri_kb/exercise_refs_data.json" "$ROOT/static/snegiri/data/exercise_refs.json"
echo "OK: static/snegiri/data/exercise_refs.json"
