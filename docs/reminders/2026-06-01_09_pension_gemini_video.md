# ⏰ Напоминание · 1 июня 2026, 09:00 МСК

## Pension: проверить видео (Gemini Veo, 4 сцены)

Генерация запланирована на **08:00 МСК** (`run_pension_gemini_scheduled.sh`).

### Что проверить

1. Финал: `data/pension/video/pension_4scenes_gemini.mp4`
2. Отчёт: `data/pension/video/gemini_scheduled_report.txt`
3. Лог: `data/pension/video/gemini_scheduled.log`

### Telegram

- После генерации — сообщение бота с результатом
- **09:00 МСК** — повторное напоминание «проверьте видео»

Если квота Veo (429) — [ai.dev/rate-limit](https://ai.dev/rate-limit), перезапуск:

```bash
python scripts/generate_pension_video_gemini.py
```

---

*Cron: `0 9 1 6 *` MSK · `remind_pension_gemini_video.py --kind check`*
