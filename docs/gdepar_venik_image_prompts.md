# Gdepar: промпты для картинок веников

Канон подставляется в `main.generate_image`, если в **теме слота** (`topic_raw`) есть `[Веники]`, «веник», «берёза», «дуб» — **не** из PROMPT от LLM.

## Провайдер

| Переменная | Значение |
|------------|----------|
| `GDEPAR_VENIK_IMAGE_PROVIDER` | `auto` (дефолт), `gemini`, `flux` |
| `GEMINI_API_KEY` или `GOOGLE_AI_API_KEY` | ключ [Google AI Studio](https://aistudio.google.com/apikey) |
| `GDEPAR_VENIK_GEMINI_MODEL` | по умолчанию `gemini-2.5-flash-image` (Nano Banana) |
| `GDEPAR_VENIK_GEMINI_ASPECT` | `4:3` |
| `GDEPAR_VENIK_GEMINI_SIZE` | `1K` |

**`auto`:** если есть `GEMINI_API_KEY` → **Gemini (Nano Banana)** с вашими промптами; иначе fal/flux.

При сбое Gemini **Flux не подставляется автоматически** (чтобы не получать «веер из палочек»).  
Включить запасной Flux: `GDEPAR_VENIK_FLUX_FALLBACK=1`.

Типичная ошибка: **HTTP 429 quota exceeded** — лимит бесплатного tier; нужен billing в [AI Studio](https://aistudio.google.com/) или подождать сброс лимита.

Остальные картинки Gdepar (печь, интерьер) — по-прежнему **fal/flux**.

## Два набора промптов

| Провайдер | Константы | Зачем |
|-----------|-----------|-------|
| **Gemini** | `GDEPAR_VENIK_*_GEMINI_PROMPT` | ваши тексты («branches and small leaves», «short handle») — хорошо в NB |
| **Flux** | `GDEPAR_VENIK_*_IMAGE_PROMPT` | жёсткие анти-«трава» якоря — запасной вариант |

## Выбор вида

| Условие в теме | Промпт |
|----------------|--------|
| `дуб` / `oak` без `берёз` | дуб |
| `берёз` / `birch` или `[Веники]` без вида | берёза |
| можжевельник | можжевельник |

## Flux-only параметры

`GDEPAR_VENIK_FLUX`: 42 steps, guidance 5.5, `landscape_4_3`, negative `GDEPAR_VENIK_NEGATIVE_EXTRA`.

## Если снова мимо

1. **«Другая картинка»** на черновике с `[Веники]`.
2. Проверить `GEMINI_API_KEY` в `/etc/empire/empire.env` и `journalctl -u empire_main | grep gemini`.
3. Принудительно: `GDEPAR_VENIK_IMAGE_PROVIDER=gemini` или `=flux`.
4. Лучший результат — **своё фото веника** (posting matrix G2).
