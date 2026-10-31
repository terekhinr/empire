# Доступ к дашборду из интернета

**Все данные для входа в одном файле:** [`docs/dashboard_access.md`](dashboard_access.md) (на VPS; в git не коммитится).

**Око Саурона** (Streamlit) — с логином и паролем.

## URL (работает сейчас)

**http://193.233.232.48:8503/**

Это отдельный порт только под Streamlit. Корень `https://neverretire.ru/` — публичный сайт книги, не кабинет.

`https://neverretire.ru/hub/` редиректит на порт 8503 (Cloudflare ломал вебсокеты Streamlit на `/hub/`).

HTTPS на IP `https://193.233.232.48/` тоже ведёт в Око; сертификат выписан на neverretire.ru, браузер покажет предупреждение.

## Логин

См. **`docs/dashboard_access.md`** — URL, логин `empire`, пароль, смена пароля.  
Дубликат на VPS: `/etc/empire/dashboard_login.txt`

## Установка / обновление nginx (уже на VPS)

```bash
sudo nginx -t && sudo systemctl reload nginx
sudo cp /root/projects/empire/deploy/empire_dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart empire_dashboard
```

Streamlit слушает `127.0.0.1:8501` (корень); nginx отдаёт его по пути `/hub/`.

## Проверка

```bash
curl -sI https://neverretire.ru/hub/ | head
# Ожидается HTTP/1.1 401 Unauthorized (без логина)
```

В браузере: логин/пароль → боковое меню **«Obsidian · практичный режим»**.

## Альтернатива: поддомен hub.neverretire.ru

Если позже добавите DNS `hub` → IP VPS:

```bash
sudo certbot certonly --webroot -w /var/www/certbot -d hub.neverretire.ru
sudo ln -sf /root/projects/empire/deploy/nginx/empire_dashboard.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Конфиг: `deploy/nginx/empire_dashboard.conf`.

## Без интернета (SSH)

```bash
ssh -L 8501:127.0.0.1:8501 root@VPS
```

Открыть: **http://localhost:8501/** (прямой доступ по SSH-туннелю).

Публичный URL с паролем: **https://neverretire.ru/hub/**.
