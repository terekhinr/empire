# Напоминания: Pension · neverretire.ru / YouTube

**Общий пайплайн (статусы A + C):** [`docs/EMPIRE_PIPELINE_CHECKLIST.md`](EMPIRE_PIPELINE_CHECKLIST.md)

---

## Сейчас (владелец)

- [ ] **Метрика neverretire.ru** — отдельный счётчик (не путать с gdepar): `docs/pension_analytics_accounts_guide.md`
- [ ] Канал YouTube: чеклист §10 в `docs/pension_youtube_roadmap_12m_2026.md`
- [ ] Снять **yt-001** по `data/pension/scripts/pension_yt/yt-001_pension_ponzi.md`

## Контент (агент / вы)

- [x] Кримсон 24 файла в `kb_sources/pension/crimson/`
- [x] Шаблон Мячина + справочник + календарь 12 нед
- [x] RAG Crimson (июнь 2026): `build_rag.py --persona pension --force --input-dir kb_sources/pension`
- [ ] После новой партии Crimson — повторить команду выше

## Не смешивать с gdepar

| | Pension | gdepar |
|---|---------|--------|
| Сайт | neverretire.ru | gdepar.ru |
| Метрика env | webapp / pension | `/etc/empire/gdepar.env` |
| ИИ на сайте | — | «Пар?» |
