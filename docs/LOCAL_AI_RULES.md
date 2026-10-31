# LOCAL_AI_RULES — чеклист перед задачей (Roo / Continue / Aider)

## Перед любой задачей

1. Прочитать хвост `docs/gdepar_checkpoints.md` (текущий статус инфры).
2. Свериться с `docs/empire_decisions_2026-05.md` и портфелем `docs/EMPIRE_PORTFOLIO_AUDIT_2026-07.md`.
3. БД: `empire.db` (контент), `analytics.db` (события), `sales.db` (деньги) — **без JOIN между файлами**.
4. Секреты только в `/etc/empire/*.env` на VPS или локальном `.env` (не в git).
5. Долгие команды на VPS — в `tmux` (сессия `empire`).

## @-attach по типу задачи

| Задача | Файлы |
|--------|--------|
| Сайты / архитектура | `docs/TZ_OMNI_MEDIA_EMPIRE_FINAL.md`, `AGENTS.md` |
| Помощник «Пар?» | `docs/gdepar_ai_assistant_tz.md`, `docs/REMINDERS_gdepar.md` |
| Книга / YT Pension | `docs/pension_book_publish_tz.md` |
| Умный дом | `docs/TZ_HOME_ASSISTANT.md`, `docs/HEALER_ARCHITECTURE.md` |
| VPN / Flint | `docs/gdepar_checkpoints.md` (свежие CP), `docs/RESTORE_INDEX.md` |
| Деплой / SSH | `docs/cursor_vps_ssh_ru.md` (ключи; пароль root не хранить в репо) |
| Пайплайн статусов | `docs/EMPIRE_PIPELINE_CHECKLIST.md` |

## Primary stack (решение 2026-10-21)

| Роль | Выбор |
|------|--------|
| Runtime | Ollama на ПК, `http://localhost:11434` |
| Coding | `qwen2.5-coder:7b` |
| Reasoning | `deepseek-r1:8b` |
| Agent IDE | VS Code + **Roo Code** |
| Autocomplete | Continue + `qwen2.5-coder:1.5b` (опц.) |
| Cloud fallback | Прямой DeepSeek API **или** VSEGPT/ProxyAPI (РФ); OpenRouter — только если трафик через VPN exit |

**Не** править прод напрямую Remote-SSH агентом как основной режим. Клон на ПК → деплой скриптом.

## Деплой (безопасный default)

```text
ПК: правки в локальном клоне empire
  → git commit (только по просьбе) / или rsync изменённых файлов
  → SSH на 138.124.90.47
  → на VPS: git pull ИЛИ принять rsync
  → systemctl restart только нужного unit (empire_gdepar / empire_webapp / …)
```

Front `109.107.174.17` — nginx/прокси; код приложений живёт на origin.

## Анти-бэклог (первая неделя миграции)

Не трогать: мастер-ТЗ как «переписать с нуля»; UUID VPN; второй VPS / смену front-origin; миграцию на Postgres; SSE «Пар?»; live нейрокомменты; авто-рендер видео; смену НПД→ИП.

## Чеклист «Cursor AI выкинут»

- [ ] Ollama служба Windows, `qwen2.5-coder:7b` в VRAM
- [ ] Roo Code пишет код без ошибки авторизации Cursor
- [ ] `AGENTS.md` + этот файл в репо
- [ ] Деплой на origin без ручного копипаста файлов через GUI
- [ ] Подписка Cursor Pro отменена (когда стек стабилен ≥3 дня)
