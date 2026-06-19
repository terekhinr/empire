# Pension: автопост TG → ВК + Дзен RSS

Связь: `docs/TZ_OMNI_MEDIA_EMPIRE_FINAL.md` §14, `docs/sim_accounts_rf_2026.md`.

---

## 1. Что уже работает на VPS

| Шаг | Механизм |
|-----|----------|
| Approve в Telegram | `main.py` → TG канал `@pensiya_nikogda` |
| После approve | `empire_publish` → `vk_wall` + `dzen_rss` (профиль `pension_social`) |
| Дзен RSS | `media/rss_pension.xml` → **https://neverretire.ru/rss/pension.xml** |
| Сайт | Футер + `/about`: ссылка на [Дзен](https://dzen.ru/user/n6syfdkcdr3eki-y_clnwz1c0dk) |

Пенсия **не** участвует в spy (только Gdepar + Stern).

---

## 2. Env (SIM 2 — Иосиф Борода)

```bash
# Уже в .env
PENSION_VK_URL=https://vk.com/id1116951081
PENSION_DZEN_URL=https://dzen.ru/user/n6syfdkcdr3eki-y_clnwz1c0dk

# Для автопоста на личную стену ВК (не группа):
VK_ACCESS_TOKEN=...          # токен с правом wall (SIM 2)
VK_WALL_PERSONAL_PENSION=1
# ID подставится из PENSION_VK_URL; явно:
# VK_OWNER_PENSION=1116951081
```

После `VK_ACCESS_TOKEN` approve pension автоматически дублирует пост на ВК.

---

## 3. Подключение Дзена к RSS

1. Студия Дзена → **Канал** «Пенсия никогда» / аккаунт [n6syfdkcdr3eki…](https://dzen.ru/user/n6syfdkcdr3eki-y_clnwz1c0dk)
2. **Настройки → Импорт RSS** → URL: `https://neverretire.ru/rss/pension.xml`
3. Режим: автозабор новых статей (Дзен подтягивает после обновления RSS при каждом approve)
4. Проверка: `curl -sI https://neverretire.ru/rss/pension.xml` → 200

Пересборка RSS вручную:

```bash
cd /root/projects/empire
EMPIRE_SKIP_EMBEDDINGS=1 ./venv/bin/python -c "import asyncio; from rss_maker import generate_pension_zen_rss; asyncio.run(generate_pension_zen_rss())"
```

---

## 4. Конфиг каналов

`data/publish_channels.json`:

- `persona_profile.pension` = `pension_social` → `["tg", "vk_wall", "dzen_rss"]`
- Без `VK_ACCESS_TOKEN` vk_wall пропускается, dzen_rss остаётся

Остальные персоны — `use_profile: tg_only` до общего решения по VK.

---

## 5. Выкат

```bash
systemctl restart empire_main empire_webapp
```

---

## 6. Чеклист владельца

- [ ] `VK_ACCESS_TOKEN` в `/etc/empire/empire.env` (SIM 2)
- [ ] Тест: approve одного pension-поста → пост в TG + ВК + RSS обновился
- [ ] Дзен: RSS URL привязан в студии
- [ ] `YANDEX_METRIKA_ID` на neverretire + цели (`docs/metrika_goals_setup.md`)
