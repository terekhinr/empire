# Гдепар · контент из книг (не свободная генерация)

**Дата:** 2026-07-22

## Правило

| Делаем | Не делаем |
|--------|-----------|
| Дословная цитата из банной книги | Промпт «напиши как Михалыч» |
| Минимальная правка OCR / обрезка | Пересказ «своими словами» вместо цитаты |
| 0–2 коротких предложения канала (`note`) | Лекции, врач, поэтизмы |
| Классика литературы как сейчас | Пачки дуэтов/монологов из воздуха |

Формат в эфире:  
**цитата → автор → 🧔 Михалыч: / 🧐 Кириллыч: + note** (один ведущий).

Пин: слева Михалыч, справа Кириллыч. Эмодзи фиксированы (вариант A).

В JSON: `"host": "mikhalych"` | `"kirillych"`, `note` — текст **без** эмодзи (префикс ставит `gdepar_book_rubrics.py`).

Код: `data/gdepar_book_excerpts.json` → `gdepar_book_rubrics.py`.

## Промпты (только поиск цитаты)

| Файл | Зачем |
|------|--------|
| [`notebooklm_dlya_tebya/prompt_gdepar.txt`](notebooklm_dlya_tebya/prompt_gdepar.txt) | Вытащить quote из epub |
| [`gemini_dlya_tebya/zadaniya/gdepar_excerpt_only_01.txt`](gemini_dlya_tebya/zadaniya/gdepar_excerpt_only_01.txt) | Пачка углов поиска |

`gdepar_mono_selected_*.txt` — **не использовать** для эфира.

## Пайплайн

1. Книга в NotebookLM / фрагмент OCR в Gemini.  
2. Промпт excerpt → сырая цитата.  
3. Ты сверяешь с книгой, правишь `note` или сотрёшь.  
4. Запись в `gdepar_book_excerpts.json`.  
5. Слот `book_rubric` в `content_config.json` крутит без LLM.

Классика: `gdepar_classic_banya.json` (отдельно).
