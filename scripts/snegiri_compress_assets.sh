#!/usr/bin/env bash
# Сжатие PNG → WebP для static/snegiri/assets/
# Требует: imagemagick, pngquant, webp (cwebp)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ASSETS="$ROOT/static/snegiri/assets"

declare -A TARGETS=(
  ["hero-mockup-screen.png"]="780x1688"
  ["track-01-spine.png"]="800x600"
  ["track-02-kettlebell.png"]="800x600"
  ["trainer-photo.png"]="1200x1600"
  ["og-image.png"]="1200x630"
  ["app-record.png"]="780x1688"
  ["app-analyze.png"]="780x1688"
  ["app-result.png"]="780x1688"
  ["benefit-01-efficiency.png"]="800x600"
  ["benefit-02-safety.png"]="800x600"
  ["benefit-03-validation.png"]="800x600"
  ["trainer-hero.png"]="1200x1600"
  ["footer-bg.png"]="1920x1080"
  ["logo-channel-1024.png"]="512x512"
  ["logo-header.png"]="256x256"
  ["logo-engraved.png"]="800x800"
  ["step-01-camera.png"]="1024x1024"
  ["step-02-ai.png"]="1024x1024"
  ["step-03-plan.png"]="1024x1024"
  ["icon-lock.png"]="128x128"
  ["icon-medical.png"]="128x128"
)

for name in "${!TARGETS[@]}"; do
  src="$ASSETS/$name"
  [[ -f "$src" ]] || continue
  size="${TARGETS[$name]}"
  tmp="$ASSETS/.tmp_$name"
  webp="${name/.png/.webp}"
  convert "$src" -strip -resize "${size}>" "$tmp"
  if [[ "$name" == step-* || "$name" == logo-* ]]; then
    mv "$tmp" "$src"
  else
    pngquant --force --quality 65-85 --output "$src" "$tmp"
    rm -f "$tmp"
  fi
  cwebp -q 82 -m 6 "$src" -o "$ASSETS/$webp"
  echo "OK $name → $webp"
done

echo "Done."
