# Яндекс.Метрика для gdepar.ru — шпаргалка по целям

**Полный гайд (создание счётчика, установка, проверка, воронки, UTM, troubleshooting):**  
→ [`docs/metrika_setup_guide.md`](metrika_setup_guide.md)

Код сайта уже отправляет события через `reachGoal`. Без `YANDEX_METRIKA_ID` в env счётчик не подключается.

## 1. Env на сервере

```bash
sudo nano /etc/empire/gdepar.env
# YANDEX_METRIKA_ID=12345678
sudo systemctl restart empire_gdepar
```

## 2. Цели в интерфейсе Метрики

Тип: **JavaScript-событие**, идентификатор = имя из таблицы (как в `docs/gdepar_ai_assistant_tz.md` §5.1).

Минимальный набор для старта:

| Идентификатор цели |
|--------------------|
| `gdepar_session_start` |
| `gdepar_page_view` |
| `gdepar_popup_open` |
| `gdepar_reviews_open` |
| `gdepar_summary_request` |
| `gdepar_assistant_fab_click` |
| `gdepar_assistant_submit` |
| `gdepar_assistant_reply_ok` |
| `gdepar_assistant_pick_click` |
| `gdepar_phone_click` |

Полный список (22+ события) — в ТЗ §5.1.

## 3. Трафик из Telegram (промо gdepar)

В еженедельных постах канала gdepar ссылки идут с UTM:
`utm_source=telegram&utm_medium=post&utm_campaign=weekly_map`.

В Метрике: **Отчёты → Источники → UTM** или сегмент по `utm_campaign=weekly_map`.
Событие черновика в Empire: `tg_promo_map_draft` в `analytics.db`.

Подробнее: `docs/gdepar_content_diversity_tz.md` §4.

## 4. KPI (решения продукта зафиксированы в ТЗ §7)

- **CR1:** после `gdepar_assistant_submit` — звонок, уход на карты/сайт, карточка бани, клик по рекомендации помощника, попап.
- **CR2:** после `gdepar_popup_open` — звонок / уход / карточка бани.

В отчётах Метрики строить воронки вручную по этим целям.
