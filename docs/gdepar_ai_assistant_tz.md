# ТЗ: ИИ-помощник «подобрать баню» на gdepar.ru (и разделение «отзывы» / «саммари»)

## 1. Контекст и цели

**Продуктовая цель:** снизить когнитивную нагрузку при выборе бани из каталога, увеличить долю сессий с переходом на карточку/контакт владельца и повторные визиты.

**Техническая цель:** не смешивать в одном UI-действии полный список отзывов и текстовую сводку — отзывы по кнопке «Отзывы», сводка по отдельному действию «Дай саммари» (см. API `include_summary`).

**ИИ-помощник** — отдельный канал: диалог по свободному запросу пользователя с опорой на данные каталога (город, тип нагрева, теги, отзывы, описание). На этапе внедрения возможна заглушка + постепенное подключение LLM.

---

## 2. Пользовательские сценарии

### 2.1. Карта / попап бани

1. Пользователь открывает попап точки.
2. **«Показать отзывы»** — запрос только списка одобренных отзывов (без сводки).
3. **«Дай саммари»** — отдельный запрос; показывается эвристическая или LLM-сводка по тем же одобренным отзывам (политика модерации не меняется).

При первом открытии **«Показать отзывы»** в попапе (главная / карта) тело блока открывается сразу: слот списка получает **`aria-busy`**, **`aria-label`** «Загрузка отзывов», **`is-loading`** и тот же визуальный скелетон, что у саммари; при ошибке сети — короткое сообщение в слоте.

### 2.2. Плавающий помощник (глобально на страницах gdepar)

1. Кнопка «Пар?» открывает панель.
2. Пользователь вводит текст (город, пожелания, бюджет/формат если известны).
3. Ответ: список 3–7 рекомендованных `spot_id` с кратким обоснованием + ссылки «открыть на карте» / «страница бани» (когда появятся). **При заглушке (без LLM для клиента):** в JSON поле **`recommendations`** — точки из того же каталога и с теми же фильтрами `city` / `heat`, что у карты; обоснование в **`reason`** помечает подбор без ИИ; если в каталоге по фильтрам **≥3** опубликованных точек, в ответ попадает **не меньше трёх** рекомендаций (до семи).

**Ограничения UX:** не подменять карту; помощник дополняет фильтры, а не дублирует их полностью.

---

## 3. Функциональные требования (MVP → v1)

### MVP (без платного LLM)

- Заглушка `POST /api/gdepar/assistant` с понятным текстом и отсылкой к карте/фильтрам. Пустой текст после `strip` — короткий ответ без списания RL и без записи в лог запроса.
- Логирование запросов (анонимный `session_id` cookie или hash IP+UA — по решению GDPR/политики сайта). **Реализовано:** cookie **`gdepar_asst_sid`** (HttpOnly, 30 дней) на HTML-страницах; логгер `gdepar.assistant`, строки `stub query` / `timing` с `client_fp` (16 hex SHA256 `IP|User-Agent`) и **`session_id`**; IP из `X-Forwarded-For`. Текст сообщения **не** пишется. Отключение: `GDEPAR_ASSISTANT_LOG=0`.

### v1 (с LLM)

- **Вход:** `message` + опционально `city`, `heat` (если известны из UI).
- **RAG / контекст:** только опубликованные сущности каталога + одобренные отзывы; не подмешивать непроверенные источники. **Реализовано:** в промпт LLM попадают строки каталога и одобренные отзывы (`status=approved`) по точкам из той же выборки; объём — **`GDEPAR_ASSISTANT_REVIEW_SNIPPETS_PER_SPOT`** (0–8 на точку, по умолчанию 2; `0` отключает отзывы), **`GDEPAR_ASSISTANT_REVIEW_FETCH_CAP`** (верхняя граница строк из БД до усечения, 20–500, по умолчанию 150).
- **Выход:** структурированный JSON (для фронта) + человекочитаемый `reply`: массив `{ spot_id, title, reason, score? }`.
- **Защита:** лимиты по IP/сессии, длина промпта, таймаут, отказ при токсичности/спаме. **Частично (stub):** скользящее окно 60 с, лимит запросов на `client_fp` (см. логирование) — `GDEPAR_ASSISTANT_RL_PER_MIN` (по умолчанию 24/мин), `GDEPAR_ASSISTANT_RL_DISABLE=1` отключает; при превышении — HTTP 429 и JSON с `rate_limited: true`. **Дополнительно:** грубая эвристика «мусорного» текста (повтор символов, много URL) — ответ-заглушка с **`spam_blocked: true`** без LLM и без записи в кэш; запрос учитывается в RL. **Токсичность (опционально):** если задан непустой **`GDEPAR_ASSISTANT_TOXIC_REGEX`** (Python `re`, флаг `IGNORECASE|UNICODE`), при совпадении с текстом запроса — заглушка с **`toxic_blocked: true`** без LLM и кэша; при невалидном выражении — в лог предупреждение, фильтр не применяется. **LLM:** текст роли user ужимается до **`GDEPAR_ASSISTANT_PROMPT_MAX_CHARS`** (по умолчанию 48000, диапазон 8000–100000 символов Unicode): сначала сокращается число строк каталога в промпте, затем блок одобренных отзывов; при необходимости — жёсткое усечение хвоста (редкий случай).
- **Кэш:** нормализованный запрос → кэш ответа на 1–24 ч (снижает стоимость при популярных формулировках). **Реализовано:** `GDEPAR_ASSISTANT_CACHE_SECONDS` — `0` / пусто / `off` = кэш выключен; иначе TTL в секундах, фактически **60–86400** (1 мин … 24 ч). Попадание в кэш не списывает RL; в JSON добавляется **`cached: true`**. Ключ включает флаг LLM, чтобы ответы заглушки и модели не смешивались.
- **LLM (опционально):** при заданном **`OPENROUTER_API_KEY`** и **`GDEPAR_ASSISTANT_LLM`** в `1|true|yes|on` ответ *может* строиться через OpenRouter (`chat/completions`), если клиент попал в долю трафика: **`GDEPAR_ASSISTANT_LLM_PCT`** (0–100, по умолчанию 100) — детерминированный бакет от **`client_fp`** (как в логах) и даты UTC; при `0` LLM для помощника выключен для всех, при `100` — для всех при включённом флаге. Модель — **`GDEPAR_ASSISTANT_MODEL`** (по умолчанию `openai/gpt-4o-mini`), таймаут — **`GDEPAR_ASSISTANT_LLM_TIMEOUT`** (сек, по умолчанию 25, диапазон 5–90), **`GDEPAR_ASSISTANT_LLM_MAX_TOKENS`** (по умолчанию 650, 120–2000), размер выборки каталога в промпт — **`GDEPAR_ASSISTANT_CATALOG_LIMIT`** (по умолчанию 40, 10–80), верхняя длина текста user — **`GDEPAR_ASSISTANT_PROMPT_MAX_CHARS`** (по умолчанию 48000, 8000–100000; при превышении каталог/отзывы в промпте ужимаются). При ошибке API / невалидном JSON / пустых picks / отсутствии попадания в `PCT` — откат к заглушке с **`recommendations`** из каталога (см. §2.2). При ответе LLM: если в выборке каталога **≥3** точек, в **`recommendations`** должно быть **3–7** валидных элементов (при неполном ответе модели список **дополняется** из каталога; при невозможности набрать 3 — откат к заглушке). Успешный ответ LLM: **`llm: true`**, **`stub: false`**, **`model`**, **`recommendations`** (см. выше).

### v2 (монетизация / качество)

- A/B: эвристика vs LLM для саммари в попапе. **Частично:** при **`OPENROUTER_API_KEY`** и **`GDEPAR_POPUP_SUMMARY_LLM`** (`1|true|yes|on`) ответ `GET /api/banya/reviews-block/{id}?include_summary=1` может подменять поле **`summary`** текстом LLM; иначе — прежняя эвристика. Доля трафика на LLM по точке за сутки UTC — **`GDEPAR_POPUP_SUMMARY_LLM_PCT`** (0–100, по умолчанию 100; детерминированный бакет от `spot_id` и даты). В JSON всегда есть **`summary_source`**: `heuristic` \| `llm`. Модель — **`GDEPAR_POPUP_SUMMARY_MODEL`** (иначе **`GDEPAR_ASSISTANT_MODEL`**, по умолчанию `openai/gpt-4o-mini`), таймаут **`GDEPAR_POPUP_SUMMARY_LLM_TIMEOUT`** (сек, 5–60, по умолчанию 18), **`GDEPAR_POPUP_SUMMARY_LLM_MAX_TOKENS`** (120–900, по умолчанию 420).
- Персонализация: «уже смотрел эти точки» из localStorage. **Реализовано:** скрипт `templates/gdepar_seen.inc.html` — **`gdeparRecordSpotSeen`**, **`gdeparGetSeenSpotIds`** (ключ `gdepar_seen_spot_ids_v1`, до 64 id). Запись при открытии попапа на карте / главной, выборе точки в списке `/map`, deep link `?spot=`, заходе на `/banya/{slug}` (блок саммари). В **`POST /api/gdepar/assistant`** передаётся **`seen_spot_ids`** (до 48), учёт в кэш-ключе и в промпте LLM / подсказке заглушки.
- Интеграция с целями Метрики (см. §6). **Дополнено:** `gdepar_summary_request` — параметр **`summary_source`**; **`gdepar_assistant_pick_click`** (`spot_id`, `dest`: banya\|map); **`gdepar_assistant_session_used`** (`page`) — один раз за вкладку при первом содержательном ответе помощника (sessionStorage).

---

## 4. Нефункциональные требования

- **Латентность:** p95 ответа помощника < 8–12 с при внешнем API (пользователю показывать скелетон/стриминг при наличии). **UI:** скелетон + **стриминг** (`POST /api/gdepar/assistant/stream`, SSE). **Сервер:** строки лога `timing route=assistant|assistant/stream ms=…` (для p95 — `journalctl | grep timing`); заголовок **`X-Gdepar-Response-Ms`** у `POST /assistant`. **Отзывы в попапе** (первый запрос **`include_summary=0`**): слот списка — **`gdepar-assistant-out`**, **`aria-live="polite"`**, при загрузке те же **`aria-busy`** / **`aria-label`** «Загрузка отзывов» и **`is-loading`**; тело блока открывается до прихода ответа. **Саммари по «Дай саммари»** (попап карты/главной и страница бани): при запросе **`include_summary=1`** блок саммари получает те же **`aria-busy`** / **`aria-label`** «Загрузка саммари» и **`is-loading`** (класс **`gdepar-assistant-out`** на слоте); в попапе при первом запросе открывается тело блока отзывов, чтобы скелетон был виден; при ошибке сети — короткое сообщение в слоте.
- **Доступность:** деградация в заглушку при ошибке провайдера. Клик по блоку рейтинга в попапе (открыть отзывы) — **`role="button"`**, **`tabindex="0"`**, **Enter** / **пробел**. **Дополнено (UI помощника):** при открытии панели фокус переходит в поле запроса; **Escape** закрывает панель и возвращает фокус на кнопку «Пар?»; у кнопки **`aria-controls`**, у панели **`role="region"`** и **`aria-label`**. Кнопка **«Спросить»** на время запроса получает **`aria-busy="true"`** (вместе с **`disabled`**). В попапе карты / главной у **«Показать отзывы»** и **«Дай саммари»** — **`aria-controls`** (на `id` блока и слота саммари), синхронизируемый **`aria-expanded`** и **`aria-busy="true"`** на кнопках на время **`fetch`** (вместе с **`disabled`**); слоты списка и саммари при этом тоже получают **`aria-busy`** / **`aria-label`** / **`is-loading`** (см. выше). На **`/banya/{slug}`** у **«Дай саммари»** — **`aria-controls="gdepar-spot-summary-out"`**, **`aria-expanded`** по видимости блока вывода и **`aria-busy="true"`** на время **`fetch`** саммари (вместе с **`disabled`**). Блок текста ответа помощника, список **`recommendations`** (`#gdepar-assistant-picks`), слот списка отзывов в попапе (**`.banya-popup-reviews-list-slot`**) и блоки вывода саммари (страница бани, попап) имеют **`aria-live="polite"`**; подпись **`#gdepar-assistant-disclaimer`** (§4 прозрачность) — тоже **`aria-live="polite"`** (у списка рекомендаций при появлении подборки задаётся **`aria-label`** с числом пунктов), чтобы обновление озвучивалось вспомогательными технологиями.
- **Прозрачность:** короткая подпись «ответ сформирован автоматически; проверьте контакты на карточке бани».

---

## 5. Воронка и метрики

**Подключение на gdepar.ru:** в `.env` задать `YANDEX_METRIKA_ID` (только цифры счётчика). В интерфейсе Метрики создать **JavaScript-цели** с теми же идентификаторами, что в колонке «Событие», либо использовать конверсии по `reachGoal` (зависит от настроек счётчика).

### 5.1. Воронка (пример событий для Я.Метрики / аналога)

| Этап | Событие | Зачем |
|------|---------|--------|
| 1 | `gdepar_session_start` (`page`) | один раз за вкладку (sessionStorage; реализовано) |
| 2 | `gdepar_page_view` (`page`: `home` \| `map` \| `spot`) | воронка по разделам (реализовано) |
| 3 | `gdepar_popup_open` (spot_id) | интерес к точке (реализовано) |
| 4 | `gdepar_reviews_open` (spot_id) | вовлечённость (реализовано) |
| 5 | `gdepar_summary_request` (`spot_id`, **`summary_source`**: heuristic\|llm) | спрос на сводку (реализовано) |
| 6 | `gdepar_assistant_fab_click` (`action`: open \| close) | кнопка «Пар?» — каждый клик (реализовано) |
| 7 | `gdepar_assistant_open` | панель помощника открыта (дублирует `action=open` из п.6; для целей-воронок; реализовано) |
| 8 | `gdepar_assistant_submit` (len_bucket) | интент (реализовано) |
| 8a | `gdepar_assistant_session_used` (`page`) | первая успешная «живая» выдача помощника за вкладку (реализовано) |
| 9 | `gdepar_assistant_reply_ok` / `gdepar_assistant_reply_fail` / `gdepar_assistant_rate_limited` (`status` при лимите/ошибке; у `reply_ok` — `stub`, `empty`, **`spam_blocked`**, **`toxic_blocked`**, **`llm_rollout`**, при ответе из кэша **`cached`**, при LLM — **`llm`**, число строк подсказок **`recs`**: 0…7) | ответ заглушки или LLM; сбой HTTP; срабатывание RL на сервере (реализовано) |
| 9a | `gdepar_assistant_pick_click` (`spot_id`, `dest`: banya\|map) | переход по ссылке из списка рекомендаций помощника (реализовано) |
| 10 | `gdepar_spot_click_out` (`spot_id`, `kind`: yandex\|twogis\|site) / `gdepar_phone_click` | целевой уход (реализовано) |
| 11 | `gdepar_map_filter_submit` (`page`, `city`, `heating`, `visited`) | отправка фильтров на `/map` (реализовано) |
| 12 | `gdepar_home_filter_submit` (`page`, `city`, `heating`, `visited`) | с главной на карту с фильтрами (реализовано) |
| 13 | `gdepar_map_list_pick` (`spot_id`) | выбор бани в боковом списке карты (реализовано) |
| 14 | `gdepar_popup_full_map_link` (`spot_id`) | «Полная карта →» из попапа на главной (реализовано) |
| 15 | `gdepar_spot_page_from_popup` (`spot_id`) | «Страница бани →» из попапа карты / главной (реализовано) |
| 16 | `gdepar_spot_page_map_link` (`spot_id`) | «Открыть на карте» с карточки `/banya/{slug}` (реализовано) |
| 17 | `gdepar_nav_click` (`dest`: brand\|karta\|map\|bayki\|manifesto\|merch\|contacts\|theme) | шапка, футер, переключатель темы (реализовано) |
| 18 | `gdepar_home_cta` (`dest`: hero_karta\|hero_skip\|lead_map) | герой и ссылка на `/map` в лиде секции карты (только главная; реализовано) |
| 19 | `gdepar_bayka_card_click` (`post_id`) | клик по карточке «Байки» (главная; реализовано) |
| 20 | `gdepar_contact_click` (`channel`: telegram\|email\|vk\|ok\|whatsapp\|phone) | блок «Контакты» (главная; реализовано) |
| 21 | `gdepar_merch_interest` (`sku`: hat\|venik\|shaika\|oil) | клик по карточке-заглушке «Мерч» (главная; реализовано) |
| 22 | `gdepar_hash_section` (`section`, `page`) | якорь `#karta` \| `#bayki` \| `#manifesto` \| `#merch` \| `#contacts` при загрузке или `hashchange` (реализовано) |

**Ключевые KPI:**

- **CR1:** `assistant_submit` → любое целевое действие в той же сессии: `gdepar_phone_click`, `gdepar_spot_click_out`, `gdepar_spot_page_from_popup`, `gdepar_assistant_pick_click`, `gdepar_popup_open` (смешанная конверсия, §7).
- **CR2:** `popup_open` → `phone_click` / `gdepar_spot_click_out` / переход на карточку бани.
- **Доля сессий с AI:** `sessions_with_assistant / all_sessions`.
- **Стоимость на сессию с AI:** `LLM_cost / sessions_with_assistant`.

### 5.2. Оценка окупаемости (упрощённая модель)

Обозначения:

- `U` — мес. уникальные посетители (или сессии).
- `a` — доля сессий, в которых вызвали помощника (например 0.5–3%).
- `q` — среднее число запросов к LLM на такую сессию (1–2).
- `C` — средняя себестоимость одного запроса к API (руб.), включая эмбеддинги/RAG, **без** амортизации разработки.

**Месячная переменная стоимость LLM:**

`Cost_m ≈ U × a × q × C`

Пример порядка (подставьте свои `U`, `C` из счёта провайдера):

| U (сессий/мес) | a | q | C (руб) | Cost_m |
|----------------|---|---|---------|--------|
| 10 000 | 1% | 1.5 | 3 | ≈ 450 |
| 50 000 | 2% | 1.5 | 3 | ≈ 4 500 |
| 100 000 | 2% | 2 | 2 | ≈ 8 000 |

**Когда «окупается»:** только если есть **явная монетизация** или **LTV трафика**:

- платные размещения / CPL от владельцев бань;
- партнёрки бронирований;
- рекламная сеть.

Тогда грубо: дополнительная маржа `ΔM` от внедрения помощника должна превышать `Cost_m + поддержка`.

`ΔM ≈ U × Δcr × value_per_conversion`

где `Δcr` — прирост конверсии в целевое действие (например +0.05 п.п. = +0.0005 доли). Пример: при `U=50 000`, `value_per_conversion=40` руб чистой маржи, нужно `Δcr × 50 000 × 40 > 4 500` → `Δcr > 0.225%` абсолютного прироста доли сессий с конверсией. Это достижимо только при измерении на A/B и реальном `value`.

**Вывод:** при чисто информационном проекте без CPL **LLM чаще не «окупается» сам по себе** — его оправдывают рост удержания, бренд, подготовка к монетизации. **Схема «отзывы / саммари раздельно»** почти бесплатна по API (только свой CPU) и уже даёт часть ценности.

---

## 6. Нужно ли это (рекомендация)

1. **Обязательно оставить** раздельные «Отзывы» и «Дай саммари» — доверие и предсказуемость UI.
2. **ИИ-помощник** имеет смысл как эксперимент при возможности замерить CR и плане монетизации; начать с **MVP-заглушки + метрик**, затем **лимитированный** LLM для части трафика.
3. **Снижение стоимости:** кэш, короткие ответы, дешёвая модель для ранжирования + дорогая только для финального текста, серверная фильтрация «пустых» запросов.

---

## 7. Открытые вопросы к продукту

Без ответов на блок ниже **новый код не обязателен** — MVP уже на проде (заглушка, эвристика, метрики в JS). Ответы нужны, чтобы включить LLM, поменять RAG и приоритет KPI.

| # | Вопрос | Варианты | Влияние на реализацию |
|---|--------|----------|------------------------|
| 1 | **Отзывы в промпте LLM** (юридика, ToS OpenRouter) | (а) как сейчас — каталог + одобренные отзывы; (б) только каталог; (в) LLM только помощник, саммари — эвристика; (г) LLM на проде не включать | env/флаги `GDEPAR_ASSISTANT_*`, `GDEPAR_POPUP_SUMMARY_*`, объём RAG |
| 2 | **Главная конверсия** для CR1/CR2 (§5) | телефон / внешние ссылки / карточка бани / любое из перечисленного | какие цели в Метрике считать «успехом», отчёты |
| 3 | **LLM на проде** | выкл. / помощник 10–25% / помощник 100% / помощник + саммари попапа | `/etc/empire/gdepar.env`: `GDEPAR_ASSISTANT_LLM`, `*_PCT`, `GDEPAR_POPUP_SUMMARY_LLM` |
| 4 | **Стриминг** ответа помощника | **реализовано** (`POST /api/gdepar/assistant/stream`, SSE `delta` + `done`) | UI: поток текста, затем список бань |
| 5 | **YANDEX_METRIKA_ID** | есть ID / нет счётчика | счётчик в env + ручное создание JS-целей (§5.1) |

**Что можно сделать без ответов:** деплой (`deploy/README.md`), заглушка, раздельные отзывы/саммари, эвристика, все `reachGoal` в коде, тесты `pytest tests/`.

**Минимум для «включить ИИ на сайте»:** ответы на **1** и **3**; для аналитики — **2** и **5**.

### Решения продукта (зафиксировано)

| Тема | Решение |
|------|---------|
| Отзывы в промпте LLM | **Разрешено** — каталог + одобренные отзывы (как в коде) |
| Конверсия CR1/CR2 | **Смешанная** — успех: звонок, уход на карты/сайт, карточка бани / попап |
| LLM на проде | **Помощник** — `GDEPAR_ASSISTANT_LLM=1`, **`GDEPAR_ASSISTANT_LLM_PCT=25`**; **саммари** — `GDEPAR_POPUP_SUMMARY_LLM=1`, `GDEPAR_POPUP_SUMMARY_LLM_PCT=100` (при сбое LLM — эвристика) |
| Стриминг | **Готово** — `POST /api/gdepar/assistant/stream` (SSE); nginx `proxy_buffering off` для пути |
| Метрика | **Уточнить** `YANDEX_METRIKA_ID` (события в коде уже есть) |

---

## 8. Связь с кодом

- API отзывов попапа: `GET /api/banya/reviews-block/{spot_id}?include_summary=0|1`; при **`include_summary=1`** в JSON — поле **`transparency_note`** (§4 ТЗ: автоматическая сводка; проверьте контакты на карточке бани), фронт выводит под текстом сводки; поле **`summary_source`**: `heuristic` \| `llm` (§3 v2, **`GDEPAR_POPUP_SUMMARY_LLM`**, **`GDEPAR_POPUP_SUMMARY_LLM_PCT`** и OpenRouter). На **`gdepar.html`** / **`gdepar_map.html`** запросы отзывов (**`include_summary=0`**) и саммари (**`include_summary=1`**) разведены; слоты **`.banya-popup-reviews-list-slot`** и **`.banya-popup-reviews-summary-slot`** — **`gdepar-assistant-out`**, **`aria-live="polite"`**, при ожидании — **`aria-busy`**, **`aria-label`**, **`is-loading`**; у блока отзывов и слотов стабильные **`id`** с суффиксом **`spot_id`**; кнопки **«Показать отзывы»** / **«Дай саммари»** — **`aria-controls`** на эти **`id`**, **`aria-expanded`** и **`aria-busy`** на время **`fetch`** (см. §2.1 / §4). На **`templates/gdepar_spot.html`** кнопка **«Дай саммари»** — **`aria-controls="gdepar-spot-summary-out"`** (id слота вывода), **`aria-expanded`** по видимости блока и **`aria-busy`** на время **`fetch`**.
- Помощник: `POST /api/gdepar/assistant`, тело `{ "message": "...", "page"?: "home"|"map"|"spot", "city"?: "...", "heat"?: "...", "seen_spot_ids"?: number[] }` (`city` / `heat` / **`seen_spot_ids`** опционально; до 2000 символов в `message`, до 48 положительных id в **`seen_spot_ids`** — см. **`templates/gdepar_seen.inc.html`**). В тексте **`reply`** заглушки (скобки после основного абзаца) перечисляются до **24** первых **`seen_spot_ids`** при необходимости с «…», если список не пуст. В каждом JSON-ответе — **`disclaimer`** (§4). Поля ответа: **`reply`**, **`stub`** (заглушка — `true`), опционально **`empty`**, **`rate_limited`**, **`spam_blocked`**, **`toxic_blocked`**, **`llm_rollout`** (bool: для этого `client_fp` и даты UTC разрешён вызов LLM по **`GDEPAR_ASSISTANT_LLM_PCT`**; у пустого запроса — `false`), при выдаче из кэша — **`cached: true`**, при успешном LLM — **`llm: true`**, **`model`**, **`recommendations`** (массив объектов с **`spot_id`**, **`slug`** (если известен), **`title`**, **`reason`**, опционально **`score`** 0–100 от LLM; при **≥3** точках в выборке каталога для LLM — **3–7** валидных строк, при неполном ответе модели список **дополняется** из каталога, см. §3 v1). У цели **`gdepar_assistant_reply_ok`** в параметрах — **`stub`**, **`empty`**, **`cached`**, **`llm`**, **`llm_rollout`** (совпадает с JSON ответа: попал ли клиент в долю **`GDEPAR_ASSISTANT_LLM_PCT`**), **`spam_blocked`**, **`toxic_blocked`**, **`recs`** (число **`recommendations`**, 0…7). Серверные логи без текста запроса — логгер `gdepar.assistant` в `gdepar_app.py`; RL — `GDEPAR_ASSISTANT_RL_PER_MIN`, `GDEPAR_ASSISTANT_RL_DISABLE`. Кэш ответа — `GDEPAR_ASSISTANT_CACHE_SECONDS` (см. §3 v1). Лог попадания в кэш: строка `stub cache_hit` (если не отключено `GDEPAR_ASSISTANT_LOG=0`). RAG для LLM: каталог + одобренные отзывы — **`GDEPAR_ASSISTANT_REVIEW_SNIPPETS_PER_SPOT`**, **`GDEPAR_ASSISTANT_REVIEW_FETCH_CAP`** (см. §3 v1). Доля трафика на LLM помощника — **`GDEPAR_ASSISTANT_LLM_PCT`** (см. §3 v1). Лимит размера текста user в запросе к модели — **`GDEPAR_ASSISTANT_PROMPT_MAX_CHARS`** (см. §3 v1). Опциональный фильтр по тексту запроса — **`GDEPAR_ASSISTANT_TOXIC_REGEX`** (см. §3 v1).
- Проверка живости: `GET` / `HEAD /api/gdepar/health` → у **GET** тело `{"status":"ok", "assistant":{…}, "popup_summary":{…}, "metrika_id_set":…, "asset_version":…}`; у **HEAD** — **200** без тела. Помощник: `POST /api/gdepar/assistant` и **`POST /api/gdepar/assistant/stream`** (SSE).
- API точек `GET /api/banya/spots` и JSON для карты: поля **`yandex_url`**, **`twogis_url`**, **`site_url`** проходят **`_safe_http_url`** (только `http://`/`https://`); **`cover_url`** — **`_cover_url_for_output`** (http(s) или путь с `/`). Те же правила для ссылок в **`admin_banya._spot_card`**. Редирект **`GET`/`HEAD /banya`** → **`/map`** (301). Индексация: `GET /robots.txt`, `GET /sitemap.xml` (главная, `/map` и публичные карточки `GET /banya/{slug}` с `lastmod` по `updated_at` при наличии; `Disallow: /admin/`); канонический хост `GDEPAR_CANONICAL_HOST` (по умолчанию `gdepar.ru`) для `https://…`, `<link rel="canonical">`, Open Graph и sitemap; JSON-LD на главной (`WebSite`, `Organization`), на `/map` (`WebPage` + `isPartOf`), на карточке бани — `@graph`: `LocalBusiness` (`@id` …`#place`, **`sameAs`** — Яндекс/2ГИС/сайт при наличии безопасных URL, поле **`image`** — обложка `cover_url` если абсолютный http(s) или путь от `/`, иначе логотип-капля) + **`BreadcrumbList`** + **`WebPage`** (`@id` …`#webpage`, `mainEntity` → `#place`, **`primaryImageOfPage`** при недефолтном изображении, **`datePublished`** из `created_at`, **`dateModified`** из `updated_at`, UTC) + до **10** объектов **`Review`** (текст на странице до ~480 символов на отзыв, `itemReviewed` → `#place`, при наличии — `reviewRating`), плюс адрес/гео и **`aggregateRating`** при ненулевых `rating_avg` и `reviews_total`. В `<head>` карточки: **`og:image`** = то же изображение, **`og:image:alt`**, **`og:locale`** `ru_RU`, **`article:published_time`** / **`article:modified_time`**, **`og:updated_time`**, **`twitter:image`**, **`twitter:image:alt`**, при недефолтной обложке — **`twitter:card`** `summary_large_image` (иначе `summary`). Превью обложки под рейтингом при валидном **`cover_url`**. Внешние ссылки на карточке рендерятся только если URL проходит фильтр **`gdepar_http_url`** (только `http://` / `https://`). На главной и `/map`: полный блок Open Graph и Twitter (`og:title`, `og:url`, `og:image`, `og:image:alt`, `twitter:title`, `twitter:description`, `twitter:image`, `twitter:image:alt`) плюс **`og:locale`** `ru_RU`. Публичная карточка только при `status=published` и slug, проходящем серверную проверку; иначе 404 (для HTML — `gdepar_404.html` с темой и `data-gdepar-nav` на ссылках, для `/api/*` — JSON). На карточке: хлебные крошки в HTML, до 12 одобренных отзывов (SSR), кнопка **«Дай саммари»** (`GET /api/banya/reviews-block/{id}?include_summary=1`, цель **`gdepar_summary_request`**), первый клип из `clips` при наличии `embed_url`; ссылки Яндекс/2ГИС/сайт/телефон с `data-gdepar-spot-external` — **`gdepar_spot_click_out`** / **`gdepar_phone_click`**. На `/map` параметр **`spot`** (число) подсвечивает точку; форма фильтров передаёт **`spot`** скрытым полем, чтобы не терять deep link при смене города/нагрева. На карте: «Страница бани →» и `/map?spot=<id>`.
- Админка бань: при `published` и непустом `slug` в карточке есть ссылка **«на сайте ↗»** на `/banya/{slug}` (`admin_banya._spot_card`, `templates/admin_banya.html`).
- Заголовки безопасности — middleware (отключение: `GDEPAR_SECURITY_HEADERS=0`): `X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options`, `Permissions-Policy`; для путей **`/admin…`** добавляется **`X-Robots-Tag: noindex, nofollow`**. HTML-страница **404** (не `/api/*`): **`X-Robots-Tag: noindex`** вместе с **`gdepar_404.html`**. Опционально **HSTS**: если в окружении задано **`GDEPAR_HSTS_MAX_AGE`** (целое число секунд, например `31536000`) и запрос считается **HTTPS** (`request.url.scheme` или последний **`X-Forwarded-Proto`** в цепочке), выставляется **`Strict-Transport-Security: max-age=…`**. На главной и **`/map`** в `<head>` — **`rel="preconnect"`** к **`cdn.jsdelivr.net`** (Leaflet); при заданном **`YANDEX_METRIKA_ID`** — ещё **`preconnect`** к **`mc.yandex.ru`** (на карточке бани и **404** — то же).
- UI: `templates/gdepar_assistant.inc.html` (подключается на **`/`**, **`/map`**, **`/banya/{slug}`**, **`gdepar_404.html`**) (список **`recommendations`**: при наличии **`slug`** — ссылка на **`/banya/{slug}`** и отдельная «На карте» → **`/map?spot=`**; иначе одна ссылка на карту; при наличии **`score`** — подпись «N/100»; цель **`gdepar_assistant_pick_click`** по клику; ожидание ответа — **`aria-busy`**, **`aria-label`**, скелетон в **`theme.css`**; блок **`#gdepar-assistant-out`** — **`aria-live="polite"`**; список **`#gdepar-assistant-picks`** — **`aria-live="polite"`** и **`aria-label`** с количеством при показе; **`#gdepar-assistant-disclaimer`** — **`aria-live="polite"`**; кнопка **«Спросить»** — **`aria-busy`** на время запроса; **Enter** в поле запроса отправляет форму, **Shift+Enter** — новая строка; **Escape** — закрыть панель; фокус при открытии — в textarea; в POST уходит не более **48** id из **`gdeparGetSeenSpotIds()`**), **`templates/gdepar_seen.inc.html`**, стили в `static/gdepar/theme.css`.
- Кэш условных запросов: `GET`/`HEAD /banya/{slug}` при наличии `updated_at` отдают **`Last-Modified`**; при **`If-Modified-Since`** не новее этой даты для **`GET` и `HEAD`** — **304** без тела (те же заголовки кэша). В ответах **`GET`/`HEAD` (200) и `304`** для **`/banya/{slug}`** добавлен HTTP-заголовок **`Link: <абсолютный канонический URL>; rel="canonical"`** (RFC 8288, дублирует `<link rel="canonical">` в HTML). **`GET /`** и **`GET /map`** (и варианты `/map` с query из **`map_canonical_url`**) — тот же **`Link rel="canonical"`**; **`HEAD /`** и **`HEAD /map`** — те же **`Link`** (query у карты как у `GET`). **`GET /robots.txt`** и **`GET /sitemap.xml`** — **`Cache-Control: public, max-age=3600`**. **`GET`/`HEAD /banya/{slug}/`** (со слэшем) при опубликованной бане — **301** на **`/banya/{slug}`**; при неверном slug или неопубликованной — **404**. Редирект **`GET`/`HEAD /map/`** → **`/map`** (301).
- Клипы каталога: **`main.normalize_clip_list`** обнуляет небезопасный **`embed_url`** (только `http(s):` или путь от `/` без `//…`).
- Дымовые тесты: каталог **`tests/`** (`pytest`; в **`conftest`** задаётся **`EMPIRE_SKIP_EMBEDDINGS=1`**, чтобы импорт **`main`** не тянул HF). **`tests/test_gdepar_transparency.py`**: разделение **`include_summary=0|1`**, **`transparency_note`** / **`summary_source`**, пустой запрос без лога **`stub query`**, RL **429**, попадание в кэш **без** списания RL, заглушка с **`seen_spot_ids`** (до 24 в тексте), спам и токсичность **без** кэша. **`tests/test_gdepar_routes.py`**: виджет помощника на **`/`** и **`/map`**, на карточке бани — **`aria-controls`** / **`aria-live`** у саммари. При наличии **`empire.db`** в корне — дополнительно sitemap и 304 / Link для карточки бани.

### 8.1. Точки восстановления (как отдельные коммиты в git)

Если заведёте репозиторий, удобно резать историю так:

1. **`main` — клипы и лёгкий импорт:** `normalize_clip_list` + **`EMPIRE_SKIP_EMBEDDINGS`** + условие **`embeddings is not None`** у FAISS; **`tests/conftest.py`**, **`tests/test_banya_clips.py`**.
2. **`gdepar_app` — условный кэш страницы бани:** **`If-Modified-Since` → 304** для **`GET` и `HEAD`**, **`parsedate_to_datetime`**, убран дубль санитизации клипов в **`_spot_to_dict`** (остаётся только **`normalize_clip_list`**).
3. **Шаблоны и OG:** **`og_image_url` / `og_image_alt`**, **`_gdepar_share_image_url`**, **`templates/gdepar.html`**, **`templates/gdepar_map.html`**, **`fetchpriority`** на обложке в **`templates/gdepar_spot.html`**.
4. **Документация и маршруты в тестах:** правки **`docs/gdepar_ai_assistant_tz.md` §8**, **`tests/test_gdepar_routes.py`**.

Команда проверки: `pytest tests/` из корня проекта (venv с **`pytest`**); в **`tests/conftest.py`** корень репозитория добавляется в **`sys.path`**, чтобы импорт **`gdepar_app`** не требовал **`PYTHONPATH=.`**.

---

## 9. Статус внедрения

### Сделано (код и автотесты)

| Область | Статус |
|---------|--------|
| §2.1 отзывы / саммари раздельно (API `include_summary`, попап, страница бани) | готово |
| §2.2 помощник «Пар?» (заглушка, `recommendations`, ссылки баня/карта) | готово |
| §3 MVP — заглушка, лог без текста, пустой запрос без RL/лога | готово |
| §3 v1 — RAG, RL, спам/токсичность, кэш, LLM + откат, 3–7 picks | готово |
| §3 v2 — LLM-саммари попапа (`summary_source`), `seen_spot_ids`, Метрика | готово |
| §4 — скелетон, a11y, стриминг, `disclaimer`, лог `timing` | готово |
| §5 — события `reachGoal` на фронте | готово (цели в интерфейсе Метрики — вручную) |
| §8 — SEO, 304, OG, клипы, админка, health | готово |

### Не сделано / вне кода (ждёт владельца или инфраструктуры)

| Пункт | Почему |
|-------|--------|
| **p95 &lt; 8–12 с** (§4) | алерты на хостинге; в коде — лог `timing` и `X-Gdepar-Response-Ms` |
| **Цели в Я.Метрике** (§5) | вручную в UI при `YANDEX_METRIKA_ID` — см. `docs/metrika_goals_setup.md` |

### Закрыто по решениям §7 (без доработки кода)

| Пункт | Статус |
|-------|--------|
| Отзывы в промпте LLM | разрешено |
| CR1/CR2 | смешанная конверсия (цели в ТЗ §5.1) |
| LLM на проде | помощник 25%, саммари 100% (`gdepar.env`) |
| Стриминг | реализовано |

### Опционально на будущее (не блокирует MVP)

- Сквозная цепочка Metrika «submit → клик по рекомендации» в одной сессии (CR1) — сейчас события есть, сбор воронки в отчётах Метрики.
- Расширенный RL (не только in-memory на процесс) при горизонтальном масштабировании.

### Деплой (сервер)

- **Unit:** `deploy/empire_gdepar.service` → `/etc/systemd/system/` (uvicorn, `EMPIRE_SKIP_EMBEDDINGS=1`, `EnvironmentFile` `/etc/empire/gdepar.env` и `.env`).
- **Nginx:** `deploy/nginx/empire_hub` → `gdepar.ru:8001`, `proxy_read_timeout 90s` для LLM.
- **Выкат:** `sudo ./scripts/deploy_gdepar.sh` — см. **`deploy/README.md`**.
- **Prod-env:** `deploy/gdepar.production.env.example` → `/etc/empire/gdepar.env` (`YANDEX_METRIKA_ID`, `GDEPAR_ASSISTANT_LLM`, …).
