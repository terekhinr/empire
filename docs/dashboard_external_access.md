# Доступ к дашборду из интернета

**Все данные для входа в одном файле:** [`docs/dashboard_access.md`](dashboard_access.md) (на VPS; в git не коммитится).

**Око Саурона** (Streamlit) — с логином и паролем.

## URL (работает сейчас)

**https://neverretire.ru/hub/**

Используется сертификат основного домена; отдельный DNS для `hub` не нужен.

Редирект: `https://neverretire.ru/hub` → `/hub/`.

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
