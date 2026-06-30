# Аудит Telegram-каналов Empire · Gemini

Готовый пакет для **Gemini 2.5 Pro** (или 1.5 Pro с большим контекстом).

---

## Быстрый старт

1. Обновить экспорт (на VPS):
   ```bash
   chmod +x scripts/export_gemini_tg_audit.sh
   ./scripts/export_gemini_tg_audit.sh
   ```

2. В [Gemini](https://gemini.google.com) → **Новый чат** → прикрепить файлы:

   | Файл | Зачем |
   |------|--------|
   | `docs/audit/gemini_export/channel_context.md` | Бизнес, персоны, статистика |
   | `docs/audit/gemini_export/all_channels_last40.txt` | 200 последних постов (40×5) |
   | `docs/audit/gemini_export/pattern_flags.tsv` | Клише и флаги |
   | `docs/audit/gemini_export/stats_summary.tsv` | Цифры по каналам |

   **Полный аудит** (если влезает в контекст) — дополнительно прикрепить:
   - `gdepar_published.txt`, `stern_published.txt`, … (все 636 постов)

3. Скопировать промпт из **`gemini_PROMPT.txt`** (в этой же папке `docs/audit/`) в поле ввода → отправить.

4. Сохранить ответ Gemini в `docs/audit/gemini_tg_audit_RESPONSE.md` (вручную).

---

## Содержимое `docs/audit/gemini_export/`

| Файл | Строк / размер |
|------|----------------|
| `all_channels_last40.txt` | ~200 постов, компактная выборка |
| `gdepar_published.txt` | 114 постов |
| `stern_published.txt` | 206 постов |
| `lenin_published.txt` | 120 постов |
| `garden_published.txt` | 182 поста |
| `pension_published.txt` | 14 постов |
| `channel_context.md` | Контекст для модели |
| `stats_summary.tsv` | Сводка |
| `backlog_summary.tsv` | pending/rejected |
| `topics_distribution.tsv` | Темы |
| `pattern_flags.tsv` | Автофлаги |

---

## Альтернатива: один архив

```bash
cd /root/projects/empire/docs/audit
tar -czf gemini_tg_audit_bundle.tar.gz gemini_export/ gemini_PROMPT.txt gemini_tg_channels_audit_prompt.md
```

Загрузить `gemini_tg_audit_bundle.tar.gz` в Gemini и вставить промпт из `gemini_PROMPT.txt`.

---

См. также: `docs/audit/02_ROI_MEDIA_AUDIT.md`, `docs/gdepar_posting_matrix_2026.md`, `docs/pension_content_calendar_2026.md`
