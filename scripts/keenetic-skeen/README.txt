Keenetic Giga: XKeen -> SKeen (sing-box)
=========================================

Сделано на роутере (2026-06-14):
- XKeen + Xray полностью удалены (opkg, /opt/etc/xray, init, cron, proxy.sh)
- Установлены SKeen 4.x + sing-box 1.12.12 (hybrid: TCP redirect + UDP tproxy)
- VPS: VLESS Reality 193.233.232.48:8443 (тот же ключ, что был в XKeen)
- Маршрут: только Google/YouTube -> VPS, остальное -> direct

Keenetic Web (сделай руками):
1. Убери политику «XKeen» с Destroy_ и СберТелек (если ещё висит)
2. Создай политику «SKeen» (Интернет -> политики доступа) — опционально
   Без политики сейчас трафик всех устройств идёт через sing-box,
   но google-only routing: ya.ru direct, youtube -> VPS
3. Сетевой ускоритель — ВЫКЛ
4. Перезагрузка роутера — желательно (сброс старых iptables xkeen)

Проверка:
- Zashboard: http://192.168.1.1:9999
- SSH Entware: skeen status
- YouTube в Chrome (инкognito) + SmartTube на Салют

Скрипты (bootstrap http://193.233.232.48:8787/):
  skeen/00-remove-xkeen.sh
  skeen/01-install-skeen.sh

Конфиги: /opt/etc/skeen/skeen.json + /opt/etc/skeen/config/*.json

Переустановка с нуля:
  curl -fsSL http://193.233.232.48:8787/skeen/00-remove-xkeen.sh | sh
  curl -fsSL http://193.233.232.48:8787/skeen/01-install-skeen.sh | sh
