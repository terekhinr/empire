XKeen + 3X-UI для Keenetic (YouTube ПК + Салют/SmartTube)
=========================================================

Я не могу зайти на твой VPS и роутер. Скрипты в scripts/keenetic-xkeen/ — запускаешь сам.

ПОРЯДОК
-------

ЭТАП 1 — VPS (SSH на сервер)
  bash 01-vps-3xui.sh
  В панели 3X-UI создай VLESS + Reality (порт 443 или 8443).
  Скопируй ссылку vless://...

  Если Amnezia на 443 — Reality на 8443.

ЭТАП 2 — ПК: сгенерировать outbound
  cd scripts/keenetic-xkeen
  python3 vless_to_outbound.py 'vless://ССЫЛКА' 04_outbounds.json

  Альтернатива: https://corvus-malus.github.io/XKeen-Config-Generator

ЭТАП 3 — Роутер SSH (exec sh)
  Скопируй скрипты на роутер или вставь содержимое:
    sh 02-nfqws2-standby.sh
    sh 03-install-xkeen.sh

  Залей outbound:
    scp 04_outbounds.json root@192.168.1.1:/opt/etc/xray/configs/

ЭТАП 4 — Keenetic Web (192.168.1.1)
  1. Приоритеты -> Политики -> создать XKeen
  2. Отметить провайдера (eth3 / МТС)
  3. Применение политик -> добавить ПК + Салют + Wi-Fi
  4. Интернет -> DNS: DoH вкл, игнорировать DNS провайдера
  5. Сетевой ускоритель — ВЫКЛ

ЭТАП 5 — Keenetic CLI (если Xray на 443)
  ip http ssl port 8443
  system configuration save

ЭТАП 6 — Запуск
  sh 04-start-xkeen.sh

ЭТАП 7 — ПК
  netsh interface tcp set global timestamps=enabled
  ipconfig /flushdns
  Chrome: chrome://flags/#enable-quic -> Disabled (по желанию)

ПРОВЕРКА
  YouTube — ролик 1080p
  sberbank.ru / gosuslugi.ru — открываются напрямую
  Салют — SmartTube

NFQWS2
  Выключен (запас). Включить: /opt/etc/init.d/S51nfqws2 start
  Не запускай nfqws2 и XKeen одновременно.

ССЫЛКИ
  XKeen: https://github.com/jameszeroX/XKeen
  3X-UI гайд: https://telegra.ph/Ne-wireguardom-edinym-08-29
  Чат: https://t.me/nfqws
