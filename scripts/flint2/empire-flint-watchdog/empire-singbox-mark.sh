#!/bin/sh
# Проставить route.default_mark перед стартом sing-box (без restart).
CFG=/etc/sing-box/config.json
[ -f "$CFG" ] || exit 0
command -v jq >/dev/null 2>&1 || exit 0
cur=$(jq -r '.route.default_mark // empty' "$CFG" 2>/dev/null)
[ "$cur" = "2097152" ] && exit 0
jq '.route.default_mark = 2097152' "$CFG" > /tmp/sb-empire-mark.json \
  && mv /tmp/sb-empire-mark.json "$CFG"
