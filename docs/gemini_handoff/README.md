# Gemini handoff — выход с Cursor AI на локальный Qwen/DeepSeek

Срез 31.10.2026 (схемы, аудит, история чатов, промпты Windsurf/Claude Code): [`../handoff/2026-10-31/README.md`](../handoff/2026-10-31/README.md). Этот каталог — пакет от 21.10, его не удалять.

| Файл | Назначение |
|------|------------|
| [`../GEMINI_HANDOFF_CURSOR_EXIT_LOCAL_LLM_2026-10.md`](../GEMINI_HANDOFF_CURSOR_EXIT_LOCAL_LLM_2026-10.md) | **Промпт** — скопировать в Gemini |
| [`EMPIRE_FULL_CONTEXT_PACK.md`](EMPIRE_FULL_CONTEXT_PACK.md) | **Пак ТЗ** (~383 KB) — загрузить attachment’ом |
| [`GEMINI_VERDICT_LOCAL_LLM_2026-10-21.md`](GEMINI_VERDICT_LOCAL_LLM_2026-10-21.md) | **Зафиксированный выбор** Gemini + поправки |
| [`../LOCAL_AI_PC_SETUP_RU.md`](../LOCAL_AI_PC_SETUP_RU.md) | День 1 на Windows |
| [`rebuild_pack.sh`](rebuild_pack.sh) | Пересобрать пак после правок docs |

## Как отправить в Gemini

1. Открой [Gemini](https://gemini.google.com) (лучше 2.5 Pro).
2. Загрузи `EMPIRE_FULL_CONTEXT_PACK.md`.
3. Вставь текст из промпта **от заголовка SYSTEM до конца** (без этой README).
4. Дождись ответа по формату OUTPUT FORMAT.

## Что внутри пака

Мастер-ТЗ, gdepar assistant, pension book, HA, stern/garden/career/pitch ТЗ, пайплайн, портфель, бизнес-план, checkpoints (свежий срез), Metrika, SSH/healer/infra README, факты R7.

Не включено (намеренно): `.env`, VPN UUID, токены, полные agent-transcripts, старые v10–v13 (история; канон = FINAL).

## Пересборка

```bash
bash docs/gemini_handoff/rebuild_pack.sh
```
