# RU TTS v2 — архитектура

Целевой пайплайн: **SSML + морфология + Whisper QA**, без ручных `+` / `[[ipa]]` в исходнике.

Пакет: `scripts/ru_tts/`. Старый путь (`prepare_md_for_tts` + `tts_pronunciation_dict.txt`) пока живёт параллельно.

## Классы

```
RuTtsPipeline
├── TextPreprocessor   # NBSP-клитики, омографы, SSML <break>/<sub>/<phoneme>
├── TTSClient            # YandexSpeechKitV3 | ElevenLabs | OpenAI
├── WhisperValidator     # faster-whisper → CER → ExceptionLexicon → re-synth
├── ExceptionLexicon     # JSON словарь самообучения
└── AudioMerger          # ffmpeg concat
```

## Поток данных

```
plain text
    → TextPreprocessor.process()
         plain (эталон CER) + ssml (<speak>…)
    → chunk
    → TTSClient.synthesize(ssml) → mp3
    → WhisperValidator.validate(mp3, plain)
         CER ≤ threshold → OK
         CER > threshold → LexiconEntry upsert → preprocess снова → re-synth
    → AudioMerger.merge → book.mp3
```

## Env

| Переменная | Смысл |
|------------|--------|
| `RU_TTS_PROVIDER` | `yandex` / `elevenlabs` / `openai` |
| `YANDEX_API_KEY` | SpeechKit |
| `RU_TTS_CONCURRENCY` | параллельные synth |
| `ELEVENLABS_API_KEY` / `ELEVENLABS_VOICE_ID` | ElevenLabs |
| `OPENAI_API_KEY` | OpenAI TTS |

## Включение

```bash
# .env
PDF_AUDIO_PIPELINE=v2
PDF_AUDIO_QA=0              # 1 = Whisper CER loop (нужен faster-whisper)
PDF_AUDIO_WHISPER_MODEL=small
PDF_AUDIO_MAX_CER=0.15
PDF_AUDIO_QA_RETRIES=2

# CLI одной главы / куска
python3 scripts/ru_tts_run.py data/sample.md -o tmp/out.mp3
PDF_AUDIO_QA=1 python3 scripts/ru_tts_run.py data/sample.md -o tmp/out.mp3 --qa
```

Бот (`pdf_audio_bot`): при `PDF_AUDIO_PIPELINE=v2` чистит текст через `clean_for_tts_v2` и озвучивает `render_part_v2` → `RuTtsPipeline`. Lexicon: `data/ru_tts_exception_lexicon.json` (seed из известных багов).

Fallback: ошибка v2 → legacy yandex → silero.

## Сделано

- Каркас классов + TextPreprocessor + WhisperValidator
- Yandex клиент (v1 form по умолчанию; `RU_TTS_YANDEX_V3=1` для эксперимента)
- Интеграция в `pdf_audio_bot` + CLI `scripts/ru_tts_run.py`

## Дальше

1. gRPC Yandex v3 (официальный SDK)
2. Полная миграция `tts_pronunciation_dict.txt` → JSON lexicon
3. GPU Whisper (`large-v3` / `turbo`) на ПК; VPS — `small` int8
