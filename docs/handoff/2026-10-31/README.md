# Empire — пакет продолжения работы (срез 31 октября 2026)

**Читать первым.** Этот каталог — карта всего ПО, аудит и промпты, чтобы открыть Windsurf, Claude Code, Gemini, Roo или Cursor и продолжить с того места, где остановились.

Секреты сюда не входят: `.env`, токены, UUID VPN, пароли SSH. Их место — `/etc/empire/*.env` и `/root/empire-secrets/` на origin. В чат другому ИИ их не вставлять.

Напоминание по «Где Пар», пока воронка слепая: счётчик `YANDEX_METRIKA_ID` создаёт только владелец (`docs/metrika_goals_setup.md`). Помощник «Пар?» живёт с `GDEPAR_ASSISTANT_LLM_PCT=25`. Решение по проценту — окно 2–4 недели. Мастер-ТЗ: `docs/TZ_OMNI_MEDIA_EMPIRE_FINAL.md`.

---

## За 5 минут

| Вопрос | Файл |
|--------|------|
| Как устроено и куда смотреть в коде | [`01_SCHEMAS.md`](01_SCHEMAS.md) |
| Что живо, что сломано, что на полке | [`02_AUDIT.md`](02_AUDIT.md) |
| Какие задачи шли в Cursor и чем кончились | [`03_CURSOR_HISTORY.md`](03_CURSOR_HISTORY.md) |
| Готовый текст для другого ИИ | [`04_PROMPTS.md`](04_PROMPTS.md) |

Старые пакеты (уже не полный срез): `docs/gemini_handoff/` (21.10), `docs/OPEN_PROBLEMS_FOR_GEMINI_2026-10-22.md` (22.10), `docs/audit/00_INDEX.md` (финмодель R6/R7, сентябрь).

---

## Где лежит код

Отдельного GitHub нет. `git remote -v` пустой.

| Что | Где |
|-----|-----|
| Origin, код, боты, HA-пакеты | Aeza `138.124.90.47`, каталог `/root/projects/empire` |
| Ветка | `main`, последний коммит `282014a` (22.10.2026) «Alert Flint/VPN failures to Telegram after self-heal attempts.» |
| Публичный HTTP | VDSina `109.107.174.17` — nginx-фронт, приложения там не крутятся |
| Дом | Flint Tailscale `http://100.84.251.64/`, HA `192.168.1.41` |
| ПК | Windows, RTX 4060 8 ГБ. Задуманный режим: клон репо на ПК, деплой на origin осознанно. День 1 локального Qwen ещё не закрыт (`docs/LOCAL_AI_PC_SETUP_RU.md`) |
| Бэкап | Яндекс.Диск `VPS-backup/<hostname>/latest/` — `docs/RESTORE_INDEX.md` |

Рабочее дерево на origin сильно разошлось с коммитом: сотни правок и новых файлов не закоммичены, плюс git считает удалёнными ~5913 файлов в `desktop/`. Коммитить пачкой нельзя. Перед любой большой правкой — `git status` и `git diff` по конкретным файлам.

Чаты Cursor на этом VPS: 25 диалогов, примерно 14–31 октября 2026. Всё, что было раньше (июнь–сентябрь: сайты, автопост, книга, карта бань), в этих чатах нет. Оно в `docs/`, снапшотах `vps-snapshot` и чеклисте `docs/EMPIRE_PIPELINE_CHECKLIST.md`.

---

## Как продолжить в другом ИИ

1. Открыть проект как папку `/root/projects/empire` (на VPS) или клон на ПК.
2. Вставить **системный промпт** из [`04_PROMPTS.md`](04_PROMPTS.md) (блок A) в правила проекта: Windsurf → `.windsurfrules`, Claude Code → `CLAUDE.md`, Roo/Continue → уже есть `AGENTS.md` + `docs/LOCAL_AI_RULES.md`.
3. Первым сообщением вставить блок D и приложить этот README + `02_AUDIT.md`.
4. Для конкретной дыры взять узкий промпт из блока E. Один заход — одна дыра.
5. После обрыва связи читать хвост `docs/gdepar_checkpoints.md`, затем этот README.

---

## Что сознательно заморожено

Домашний контур Flint + podkop + Amnezia `awg0` + VLESS для ИИ, YouTube и Telegram. Правило: `.cursor/rules/flint-vpn-freeze.mdc`. Менять маршруты только после прямой фразы владельца «почини X, смени на Y».

Автоканалы Сад / Штерн / Ленин — только автопост, без продаж.

Один комплект empire-сервисов. Второй VPS с теми же ботами не поднимать.

---

## Сейчас (проверка 31.10.2026 ~13:50 МСК)

Локально на origin ответили HTTP 200:

- `http://127.0.0.1:8001/api/gdepar/health` — Где Пар
- `http://127.0.0.1:8000/api/health` — neverretire
- `http://127.0.0.1:8502/api/planning/health` — задачник

Активны: `empire_main`, `empire_gdepar`, `empire_webapp`, `empire_dashboard`, `empire_worker`, `empire_planning`, `empire_sales`, `empire_ha_notify`, `empire-home-ops`, `empire-mtg`.

Выключены по решению «без продаж»: `empire_garden_bot`, `empire_stern_bot`, `empire_donate_bot`.

Свежий красный сигнал: `empire-flint-remote-heal` в 10:46 UTC упал с `smoke fail` (Telegram / YouTube / AI FakeIP на Flint). Таймер каждые 5 минут сам ретраит и шлёт алерт. Маршруты из этого пакета не перестраивались.

---

## Роли проектов (чтобы другой ИИ не раздувал портфель)

| Роль | Проект |
|------|--------|
| Флагман личного бренда | «На пенсию НИКОГДА» — neverretire.ru, книга, YouTube ещё не снят |
| Флагман сервиса | «Где Пар» — gdepar.ru, карта бань, помощник «Пар?» |
| Радио на автомате | Сад (Степаныч), Штерн, Ленин — посты сами, касса выключена |
| Полка | Снегири / сильвер-фитнес, голосовой бот бань, омни-фабрика «везде» |
| Дом | Home Assistant, хилеры, Flint. Это удобство квартиры, не бизнес |
| Инфра | Origin Aeza + front VDSina + бэкап на Я.Диск |
| Учёба | Empire Practicum + задачник PWA + карьерный трек B2B. Окно коммерции после службы: 2027-04 … 2027-10. До этого учёба и портфолио, без серых схем |
