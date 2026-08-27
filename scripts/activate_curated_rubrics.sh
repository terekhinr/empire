#!/usr/bin/env bash
# Активация рубрик Gdepar «Классическая баня» + Ленин (литература/искусство/био/кино)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="${ROOT}/venv/bin/python"

echo "== Prefetch Gdepar classic =="
"$PY" scripts/prefetch_gdepar_classic_images.py || true

echo "== Seed Lenin portrait pool if empty =="
POOL="$ROOT/media/lenin/pool"
mkdir -p "$POOL"
if [ -z "$(find "$POOL" -maxdepth 1 -type f \( -name '*.jpg' -o -name '*.jpeg' -o -name '*.png' \) 2>/dev/null | head -1)" ]; then
  cp -n "$ROOT/media/lenin/rubrics/_default_lenin.jpg" "$POOL/portrait_default.jpg" || true
  echo "seeded $POOL"
fi

echo "== Prefetch Lenin rubrics =="
"$PY" scripts/prefetch_lenin_rubric_images.py || true

echo "== Prefetch Stern rubrics =="
"$PY" scripts/prefetch_stern_rubric_images.py || true

echo "== Restart empire_main =="
systemctl restart empire_main
systemctl is-active empire_main

echo "OK $(date -u +%Y-%m-%dT%H:%M:%SZ)"
