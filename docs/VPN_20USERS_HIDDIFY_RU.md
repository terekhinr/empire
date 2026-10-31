# VPN на 20 пользователей: 3 Reality + CDN (без ручного переключения)

## Схема

Каждый `user01`…`user20` получает **одну подписку** из четырёх входов:

1. **CDN** — `vpn.kalitkuprikroy.ru` (Cloudflare WS+TLS) — если вырезали IP VPS  
2. **VDSina** — Reality  
3. **Aeza** — Reality  
4. **JustHost STO1** — Reality  

Клиент (Hiddify / v2rayN / Streisand) в режиме **Авто / urltest** сам уходит на живую ноду.

Домашний Flint (YouTube/TG + AI через Amnezia) — **отльный** контур, эти UUID не использует.

## Где секреты

- Профили: `/root/empire-secrets/profiles/userNN.txt` (+ `.json`, `-sub.txt`)
- URL подписки: `/root/empire-secrets/cdn-kalitka/sub-meta.json`
- Токен пути: `/root/empire-secrets/cdn-kalitka/sub.token`
- Шпаргалка импорта: `/root/empire-secrets/profiles/IMPORT_HIDDIFY.txt`

Не коммитить UUID/токен/ссылки в git. Раздачу людям — только по явной команде владельца.

## Healthcheck

`empire-vpn-healthcheck.timer` — VDSina + Aeza + STO1 + CDN; алерт в Telegram при fail.

## Раздача на телефоны (HTML)

Один файл на человека (QR + все ноды + короткая инструкция):

- Локально: `/root/empire-secrets/profiles/dist/user01.html` … `user20.html`
- Общая инструкция с картинками: `…/dist/guide/index.html`
- Сборка: `python3 scripts/empire_vpn_build_user_dist.py`
- HTTPS-пути (TOKEN в `cdn-kalitka/sub-meta.json`): `base/dist/userNN.html`

Шлите человеку только **его** `userNN.html` (или ссылку на него), не весь `dist/index.html`.
