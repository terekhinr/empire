Flint 2 GL-MT6000 — bootstrap (Empire)
======================================

VPS bootstrap: http://193.233.232.48:8789/

БЫСТРЫЙ СТАРТ (на роутере после vanilla OWRT 24.10)
---------------------------------------------------
  curl -fsSL http://193.233.232.48:8789/00-bootstrap.sh | sh

ПОРЯДОК ВРУЧНУЮ
---------------
  1. Прошить vanilla OpenWrt 24.10.4 sysupgrade (см. docs/FLINT2_SETUP.md)
  2. curl .../00-bootstrap.sh | sh
  3. LuCI → Zapret2 → пресет МТС → Restart
  4. Переключить WAN с Keenetic на Flint 2

VPS (агент)
-----------
  python3 serve_bootstrap.py   # :8789
  ssh -p 6223 root@127.0.0.1   # после туннеля с роутера

VPN
---
  VLESS Reality → 193.233.232.48:8443 (тот же VPS что XKeen)
