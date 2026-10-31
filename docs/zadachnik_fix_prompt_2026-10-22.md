# Промпт / бриф: починить Задачник (neverretire.ru)

Скопируй блок ниже агенту, если снова сломается. Контекст проверен **2026-10-22**.

---

## Роль

Ты чинишь Empire Tasks PWA («Задачник») на VPS Aeza. Запрещено: трогать Flint/VPN/podkop; заявлять PASS без headless/curl доказательств; править прод «вслепую».

## Архитектура (как есть)

| Путь | Backend | Назначение |
|------|---------|------------|
| `/x/` | nginx → `127.0.0.1:8502` (`planning_api`) | **Рабочий SPA** (вне scope старого SW) |
| `/tasks/` | → 302 `/x/`; assets/api → 8502 | Старый mount; SW часто вешает ПК |
| `/go/` | `web_app` :8000 | Хаб: Задачник / Зал / Практикум / сброс |
| `/go-tasks/` | `web_app` :8000 | Жёлтый SSR-список / логин токена |
| `/go-learn/` | `web_app` :8000 | SSR Практикум (недели, %, Continue) |
| `/gym/` | planning :8502 | Зал (тренировка) |
| `/go-tasks/app/` | 302 → `/x/` | Устаревший mount |
| `/go-reset/` | static `/var/www/empire-tasks-reset/` | Сброс SW → `/go/` |
| `/tasks-reset/` | 302 → `/go-reset/` | Старая закладка |

Auth API: заголовок **`X-Planning-Token`** (= `PLANNING_API_TOKEN`). Не Bearer.

Сервисы: `empire_planning.service` (:8502), `empire_webapp.service` (:8000), nginx + SNI :443→:9443.

## Известные классы багов

1. **Prefix collision:** любой URL `/tasks-*` (кроме exact `location =`) ловится `location /tasks/` → rewrite → FastAPI `{"detail":"Not Found"}`. Канон сброса: **`/go-reset/`**. Старые `/tasks-reset` и `/tasks-fix` → 302 на `/go-reset/`.
2. **Service Worker** на `/tasks/` жрёт fetch → чёрный экран / «Скрипт не стартовал». Обход: `/x/`, `/go-reset/`.
3. **Битый handoff:** кнопка recover → `/go-tasks/app/` → раньше редирект на логин, не на SPA.
4. **Secure cookie** на `/go-tasks` при HTTP ломает сессию; после логина нужен редирект на `/x/?native_token=…`.

## Обязательные проверки (минимум)

```bash
curl -sk -H 'Host: neverretire.ru' https://127.0.0.1:9443/x/ -o /dev/null -w '%{http_code}\n'
curl -sk -H 'Host: neverretire.ru' https://127.0.0.1:9443/go-reset/ | rg 'href="/x/'
curl -sk -H 'Host: neverretire.ru' https://127.0.0.1:9443/go-tasks/app/ -o /dev/null -w '%{redirect_url}\n'
curl -s http://127.0.0.1:8502/api/planning/health
# headless:
PLANNING_TEST_URL=https://neverretire.ru/x/ ./venv/bin/python scripts/test_planning_pwa_boot.py
./venv/bin/python scripts/verify_zadachnik_escape.py
```

PASS только если: UI `ready`, splash скрыт, tasks≫0, career tab открывается, `/go-reset` → кнопка `/x/`, `/go-tasks/app` → `/x/`.

## Канон файлов

- nginx: `deploy/nginx/neverretire_planning.inc`
- SSR вход: `web_app.py` (`/go-tasks`)
- SPA: `static/planning/index.html`, `app.js`
- Тесты: `scripts/test_planning_pwa_boot.py`, `scripts/verify_zadachnik_escape.py`

---

## Вердикт 2026-10-22 (что починено)

- `/go-tasks/app` → `/x/`
- recover → `/x/?reset=1`
- `/go-reset/` вместо мёртвого `/tasks-reset/` (collision)
- POST `/go-tasks` → `/x/?native_token=…`
- APP_VER 86; тесты под Sem1
