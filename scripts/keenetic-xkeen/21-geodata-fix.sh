#!/bin/sh
# Симлинки geodata для xray (без них Google routing = ERR_FAILED)
# curl -fsSL http://193.233.232.48:8787/21-geodata-fix.sh | sh

set -eu
DAT=/opt/etc/xray/dat
for f in geosite_v2fly.dat geoip_v2fly.dat geosite_zkeen.dat geoip_zkeenip.dat; do
  ln -sf "$DAT/$f" /opt/sbin/$f
done
/opt/sbin/xray run -test -confdir /opt/etc/xray/configs 2>&1 | tail -1
