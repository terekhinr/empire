Flint 2 GL-MT6000 — bootstrap (Empire)
======================================

Полный гайд (два режима, сторож, откуда схемы):
  docs/FLINT2_YOUTUBE_DUAL.md

VPS bootstrap: http://193.233.232.48:8789/

РЕЖИМ A — с VPS (YouTube → VLESS)
---------------------------------
  curl -fsSL http://193.233.232.48:8789/00-bootstrap.sh | sh

РЕЖИМ B — без VPS (YouTube → zapret)
------------------------------------
  На ПК: sh scripts/flint2/pack-usb-novps.sh
  На Flint: sh /mnt/usb/flint-novps-usb/00-bootstrap-novps.sh
  Стратегия DPI: zms  (Zapret-Manager)

ПЕРЕКЛЮЧЕНИЕ
------------
  curl .../20-mode-vps.sh | sh
  curl .../21-mode-novps.sh | sh

СТОРОЖ
------
  С VPS:  bash scripts/flint2/empire-flint-watchdog/install.sh
  На Flint / USB: sh empire-flint-watchdog/install-local.sh

ОБЯЗАТЕЛЬНО
-----------
  vanilla OpenWrt 24.10, flow offloading ВЫКЛ, IPv6 WAN ВЫКЛ
  (делает 19-prereq-dpi.sh)

VPN
---
  VLESS Reality → 193.233.232.48:8443
