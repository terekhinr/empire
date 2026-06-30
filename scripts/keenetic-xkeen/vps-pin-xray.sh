#!/bin/sh
# Закрепить xray 24.12.31 (стабильнее 26.x для long-lived VLESS Reality).
set -eu
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
TARGET="v24.12.31"
BIN="/usr/local/bin/xray"
TMP="/tmp/xray-pin"

cur=$(xray version 2>/dev/null | head -1 || echo unknown)
case "$cur" in
  *24.12.31*) echo "xray already $TARGET"; exit 0 ;;
esac

echo "current: $cur -> installing $TARGET"
mkdir -p "$TMP"
cd "$TMP"
url="https://github.com/XTLS/Xray-core/releases/download/${TARGET}/Xray-linux-64.zip"
curl -fsSL -o xray.zip "$url"
unzip -oq xray.zip
install -m 755 xray "$BIN"
rm -rf "$TMP"
xray version | head -1
