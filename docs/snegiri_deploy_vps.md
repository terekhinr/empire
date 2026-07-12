# snegirinegi.ru на VPS Empire

**Решение:** домен на тот же VPS, что neverretire.ru / gdepar.ru.

## DNS (заказчик)

1. A-запись `snegirinegi.ru` → IP VPS Empire
2. A-запись `www` → тот же IP (или CNAME на apex)
3. Почта: `hello@snegirinegi.ru` — Yandex 360 / Mail.ru для домена

## Nginx (после DNS)

Фрагмент для `/etc/nginx/sites-available/snegirinegi.ru`:

```nginx
server {
    listen 80;
    server_name snegirinegi.ru www.snegirinegi.ru;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name snegirinegi.ru www.snegirinegi.ru;

    # ssl_certificate /etc/letsencrypt/live/snegirinegi.ru/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/snegirinegi.ru/privkey.pem;

    # Фаза 0: лендинг + макет приложения
    location / {
        root /root/projects/empire/static/snegiri;
        try_files $uri $uri/ /index.html;
    }

    location /app {
        alias /root/projects/empire/static/snegiri;
        try_files /mockup.html =404;
    }

    # Фаза 1: API (когда будет empire_snegiri / router в web_app)
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
sudo certbot --nginx -d snegirinegi.ru -d www.snegirinegi.ru
```

## Сейчас (до DNS)

Макет локально на VPS:

```
https://<IP-VPS>/static/snegiri/mockup.html
```

или после nginx root — `https://snegirinegi.ru/`

## Пути в репозитории

| Что | Путь |
|-----|------|
| Макет PWA | `static/snegiri/mockup.html` |
| Стили | `static/snegiri/styles.css` |
| ТЗ | `docs/stern_kettlebell_ai_trainer_tz.md` |
| Письма тренерам | `docs/snegiri_trainers_outreach.md` |
| Промпты Gemini | `docs/snegiri_gemini_prompts.md` |
