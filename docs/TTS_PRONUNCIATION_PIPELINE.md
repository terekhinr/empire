# Алгоритм озвучки: ударения, аббревиатуры, фонемы

## Зачем

Yandex SpeechKit (и любой neural TTS) ошибается на:

1. **фонемах** — «много» → «мново» (ложное озвончение г→в);
2. **коротких аббревиатурах** — «АО» → «аоаоао»;
3. **ударениях/омографах** — за́мок / замо́к, мука́ / му́ка;
4. **доменных терминах** — покер, бренды, фамилии.

Полностью «лингвистическим анализом» это не закрыть: авто-стресс нужен, но поверх него обязателен **лексикон исключений** (как у Azure / Amazon Polly / издательских TTS).

## Как делают другие

| Слой | Azure / Polly / Google | У нас (SpeechKit) |
|------|------------------------|-------------------|
| Text normalization (числа, даты, NSW) | да | `ru-normalizr` + `expand_speech_abbreviations` |
| Alias lexicon (W3C → полная форма) | PLS / `<sub alias>` | расшифровка АО/ООО + `tts_pronunciation_dict.txt` |
| Phoneme override | SSML `<phoneme>` / PLS | TTS-разметка `[[m n ɔ g ʌ]]` |
| Stress / homographs | реже (EN) | `silero-stress` + overrides с `+` |
| QA loop | услышать → в lexicon | то же: ошибка из ушей → одна строка в dict |

Оптимальный путь для multi-provider (Yandex + Silero + Edge): **вся коррекция в тексте до синтеза**, без зависимости от hosted PLS (у SpeechKit его нет).

## Алгоритм (обязательный порядок)

```
сырой текст (md/pdf/docx)
    │
    ▼
1. CLEAN — снять markdown, URL, редактуру
    │
    ▼
2. ALIAS / ABBR — т.д., ув., ООО/АО/ПАО… (гео-АО → автономный округ)
    │
    ▼
3. NORMALIZE — числа, даты (ru-normalizr light)
    │
    ▼
4. STRESS — silero-stress → `+` (Yandex/Silero) или ́ (Edge)
    │
    ▼
5. LEXICON — scripts/tts_pronunciation_dict.txt
    │         (алиас / +ударение / [[фонемы]], longest-first)
    │
    ▼
6. SYNTH — Yandex SpeechKit (filipp) / Silero fallback
    │
    ▼
7. QA — услышал ошибку → строка в dict → переозвучка куска
```

Почему lexicon **после** stress: иначе акцентуатор ломает блоки `[[…]]`.  
Почему юрформы **до** stress: читаются как обычные слова и получают нормальные ударения.

## Файлы

| Файл | Роль |
|------|------|
| `scripts/prepare_md_for_tts.py` | оркестратор пайплайна |
| `scripts/tts_pronunciation.py` | юрформы + применение словаря |
| `scripts/tts_pronunciation_dict.txt` | исключения произношения |
| `scripts/docx_to_mp3_yandex.py` | синтез SpeechKit |
| `bots/stepanich/pdf_audio_bot.py` | книжки/сайты через тот же `prepare_for_tts` |

## Env

| Переменная | По умолчанию | Смысл |
|------------|--------------|--------|
| `PDF_AUDIO_STRESS` | `1` | авто-ударения |
| `PDF_AUDIO_STRESS_FORMAT` | `acute` / для Yandex бот ставит `plus` | форма ударений |
| `PDF_AUDIO_PRONUNCIATION` | `1` | словарь исключений |
| `PDF_AUDIO_PRONUNCIATION_DICT` | `scripts/tts_pronunciation_dict.txt` | путь к словарю |

## Правило пополнения словаря

1. Классифицируй ошибку: alias / stress / phoneme.
2. Для аббревиатур и юрформ — **alias** (полная фраза).
3. Для омографов — **stress** (`зам+ок`).
4. Для подмены звука (г→в и т.п.) — **phoneme** (`[[…]]`, только Yandex).
5. Одна ошибка → одна строка; ключ без ударения; матч сработает и на `мн+ого`.

## Проверка

```bash
cd /root/projects/empire
python3 scripts/verify_tts_pronunciation.py           # SAMPLE + gold text (~35)
python3 scripts/verify_tts_pronunciation.py --cer     # TTS→STT CER (нужен YANDEX_API_KEY)
# отчёт: tmp/tts_cer_report.json
python3 scripts/prepare_md_for_tts.py /tmp/sample.md -o /tmp/sample_tts.txt
python3 scripts/docx_to_mp3_yandex.py /tmp/sample_tts.txt -o /tmp/sample.mp3 --voice filipp
```
