# snegirinegiri.ru на VPS Empire

**Решение:** домен на тот же VPS, что neverretire.ru / gdepar.ru (`138.124.90.47`).

Лендинг и PWA отдаёт `web_app.py` по `Host: snegirinegiri.ru`; API — `/api/snegiri`. Nginx: `deploy/nginx/snegirinegiri.ru`.

## DNS (заказчик, Timeweb)

Сейчас A/AAAA смотрят на парковку Timeweb (`vh462.timeweb.ru`). Нужно:

1. A `snegirinegiri.ru` → `138.124.90.47`
2. A `www` → `138.124.90.47` (или CNAME на apex)
3. AAAA удалить или тоже на новый VPS — иначе IPv6 останется на парковке
4. MX/NS/почту Timeweb не трогать, если почта там живая

После A: `sudo certbot --nginx -d snegirinegiri.ru -d www.snegirinegiri.ru`

## Nginx

Сайт: `/etc/nginx/sites-available/snegirinegiri.ru` (прокси на `127.0.0.1:8000`).
Статику nginx из `/root` не отдаёт (www-data не ходит в `/root`) — всё через uvicorn.

## Пути в репозитории

| Что | Путь |
|-----|------|
| Лендинг | `static/snegiri/index.html` |
| PWA | `static/snegiri/app.html` |
| API | `snegiri_kb/routes.py` |
