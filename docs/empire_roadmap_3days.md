# План на 2–3 дня (май 2026)

Связь: `docs/empire_decisions_2026-05.md`, `docs/spy_setup_gdepar_stern.md`.

Легенда: **Вы** — нужны ваши действия (логин, DNS, пароли). **Empire** — код/сервер без вас.

---

## День 1 — инфраструктура и замеры

| # | Задача | Кто | Статус |
|---|--------|-----|--------|
| 1.1 | **Метрика на gdepar.ru** — по `docs/metrika_setup_guide.md` | **Вы** | ⬜ |
| 1.2 | Цели (минимум 10) — таблица в том же гайде §5.2 | **Вы** | ⬜ |
| 1.3 | **Почта gdepar.ru** — Cloudflare Email Routing (как neverretire): `info@gdepar.ru` → Gmail | **Вы** | ⬜ см. `docs/gdepar_email_cloudflare.md` |
| 1.4 | **Дашборд снаружи** — DNS `hub.neverretire.ru`, certbot, htpasswd | **Вы** | ⬜ `docs/dashboard_external_access.md` |
| 1.5 | Обновить список конкурентов spy (без коммерции) | Empire | ✅ `data/spy_competitors.json` |
| 1.6 | Автослот `spy_inspired` вс 10:00 gdepar / вс 11:00 stern | Empire | ✅ код + `content_config` |

---

## День 2 — аккаунты и Telegram

| # | Задача | Кто | Статус |
|---|--------|-----|--------|
| 2.1 | Завести TG **«Empire Spy»** (отдельный номер/eSIM) | **Вы** | ⬜ |
| 2.2 | [my.telegram.org](https://my.telegram.org) → `TELETHON_API_ID` / `HASH` в `.env` | **Вы** | ⬜ |
| 2.3 | `python scripts/telethon_login.py` → файл `.session` на VPS | **Вы** + Empire | ⬜ скрипт |
| 2.4 | Проверить каналы из JSON — удалить мёртвые, дописать свои | **Вы** | ⬜ |
| 2.5 | `restart empire_worker` — live spy вместо dry-run | Empire | после 2.3 |
| 2.6 | **ВК**: сообщества Garden, Gdepar, Stern, Lenin, Pension (оформление, описание) | **Вы** | ⬜ |
| 2.7 | **Дзен**: каналы/студии для тех же персон; Pension — приоритет | **Вы** | ⬜ |

---

## День 3 — Пенсия YouTube + Shorts Stern

| # | Задача | Кто | Статус |
|---|--------|-----|--------|
| 3.1 | Пройти гайд **YouTube для Pension** (канал, монетизация, VPN-аудитория) | **Вы** | ⬜ `docs/pension_youtube_launch_guide.md` |
| 3.2 | Rutube / VK Clips / Дзен Shorts — **только Stern** (пилот 1 ролик/нед) | **Вы** | ⬜ |
| 3.3 | Garden / Gdepar Shorts | — | ❌ не сейчас |
| 3.4 | Gdepar 15-сек обзоры бань | — | ❌ после съёмки |
| 3.5 | Pension: `PENSION_TG_CHAT_ID` в `.env` если есть канал | **Вы** | ⬜ |
| 3.6 | После VK-токена: `publish_channels.json` → `with_vk` | **Вы** | ⬜ |

---

## Что Empire делает без ожидания

- P0 качество постов (gdepar / stern / pension) — по мере деплоя  
- Документация: spy, YouTube, email, dashboard, архитектура  
- `spy_inspired` + обновлённые конкуренты  
- Дашборд: вкладки по персонам (Pension / Gdepar-Stern / Shorts Stern)  

---

## Shorts — политика

| Персона | Shorts |
|---------|--------|
| **Stern** | VK, Дзен, Rutube — да |
| **Garden** | нет |
| **Gdepar** | нет, пока нет 15-сек обзоров бань |
| **Pension** | длинный YouTube — гайд; Shorts — опционально позже |
