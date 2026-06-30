# Напоминания: gdepar.ru (после выката ИИ-помощника)

**Создано:** май 2026 · **Статус gdepar по ТЗ:** `docs/gdepar_checkpoints.md` (CP-20260520)

> **Общий пайплайн Empire (Pension + gdepar, статусы):** [`docs/EMPIRE_PIPELINE_CHECKLIST.md`](EMPIRE_PIPELINE_CHECKLIST.md) — блок **B**.

> Я (агент в Cursor) **не могу** прислать push в 19:00 — только этот файл и правило в `.cursor/rules/`. Поставьте будильник/событие в телефоне (текст ниже).

---

## Четыре пункта — не забыть

### 1. Сейчас (обязательно)

- [ ] **Яндекс.Метрика:** счётчик → `YANDEX_METRIKA_ID` в `/etc/empire/gdepar.env` → `sudo systemctl restart empire_gdepar`
- [ ] **Цели** в кабинете Метрики — см. `docs/metrika_goals_setup.md`

### 2. Первая неделя после Метрики

- [ ] Сайт: Ctrl+Shift+R, кнопка **«Пар?»** внизу справа, стриминг ответа
- [ ] Раз в 2–3 дня: счёт **OpenRouter**
- [ ] В Метрике: `gdepar_assistant_submit` → звонок / клик по рекомендации

### 3. Через 2–4 недели (по цифрам)

- [ ] Решить про **`GDEPAR_ASSISTANT_LLM_PCT`**: оставить 25% / поднять до 50–100% / выключить LLM
- [ ] При медленных ответах: `journalctl -u empire_gdepar | grep 'timing route='`

### 4. Не срочно

- [ ] p95-алерты на хостинге (опционально)
- [ ] Монетизация / CPL — отдельно от техники
- [ ] **Голосовой бот** (callback, пре-квалификация) — не раньше CPA-депозитов; `docs/gdepar_voice_bot.md`

---

## Следующий крупный шаг по проекту

- [ ] Пройтись по **мастер-ТЗ:** `docs/TZ_OMNI_MEDIA_EMPIRE_FINAL.md`  
  (gdepar — ветка внутри империи; детали помощника — `docs/gdepar_ai_assistant_tz.md`)

---

## Текст для календаря (скопировать)

**Сегодня вечером:**  
«Gdepar: Metrika ID + цели (metrika_goals_setup.md). Проверить Пар? на сайте.»

**Завтра вечером:**  
«Gdepar: OpenRouter + воронка в Метрике. Запланировать разбор TZ_OMNI_MEDIA_EMPIRE_FINAL.»

---

## Проверка одной командой

```bash
curl -s https://gdepar.ru/api/gdepar/health | python3 -m json.tool
```
