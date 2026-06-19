# Почта @gdepar.ru (как у neverretire.ru)

Аналог схемы из `TZ_OMNI_MEDIA_EMPIRE_FINAL.md` § Cloudflare Email Routing.

## Цель

`info@gdepar.ru` (и при необходимости `support@`, `map@`) → ваш Gmail.

## Шаги (Cloudflare, домен gdepar.ru)

1. **DNS** домена в Cloudflare (уже для сайта).
2. **Email Routing** → Enable.
3. **Destination**: `terekhin.r@gmail.com` (или отдельный ящик) — **подтвердить** письмо Cloudflare.
4. **Custom address**: `info` → destination.
5. **MX** (если не автоматически): `route1.mx.cloudflare.net` и др.
6. **SPF** TXT: `v=spf1 include:_spf.mx.cloudflare.net ~all`
7. **DMARC** (опционально): `_dmarc.gdepar.ru` → `v=DMARC1; p=none; rua=mailto:...`

## Проверка

С внешнего ящика → `info@gdepar.ru` → приходит в Gmail за 1–2 мин.

## На сайте

В `gdepar` контактах указать `info@gdepar.ru`; событие Метрики `gdepar_contact_click` с `channel=email` уже в коде.

## Отличие от neverretire

Отдельный домен → отдельные MX/маршруты в Cloudflare для **gdepar.ru**, не смешивать с neverretire.ru.
