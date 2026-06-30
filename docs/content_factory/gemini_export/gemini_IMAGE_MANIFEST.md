# Манифест картинок Nano Banana

Задач Nano Banana: **246**
Классическая баня (уже готово, **не печатать**): **160/160**

| Канал | Nano Banana |
|-------|-------------|
| gdepar | 163 |
| stern | 83 |

## Gdepar: Классическая баня (15:00)

- Данные: `data/gdepar_classic_banya.json`
- Портреты: `media/gdepar/classic/{id}.jpg`
- На диске: **160** / 160
- Источник: Wikipedia/Commons (`ensure_classic_image`), **не** Nano Banana
- Prefetch: `./venv/bin/python scripts/prefetch_gdepar_classic_images.py`

## Paste-батчи (только duo + stern)

- `docs/content_factory/gemini_export/image_batch_requests/gdepar_images_part01.txt`
- `docs/content_factory/gemini_export/image_batch_requests/gdepar_images_part02.txt`
- `docs/content_factory/gemini_export/image_batch_requests/gdepar_images_part03.txt`
- `docs/content_factory/gemini_export/image_batch_requests/gdepar_images_part04.txt`
- `docs/content_factory/gemini_export/image_batch_requests/gdepar_images_part05.txt`
- `docs/content_factory/gemini_export/image_batch_requests/gdepar_images_part06.txt`
- `docs/content_factory/gemini_export/image_batch_requests/gdepar_images_part07.txt`
- `docs/content_factory/gemini_export/image_batch_requests/gdepar_images_part08.txt`
- `docs/content_factory/gemini_export/image_batch_requests/gdepar_images_part09.txt`
- `docs/content_factory/gemini_export/image_batch_requests/gdepar_images_part10.txt`
- `docs/content_factory/gemini_export/image_batch_requests/gdepar_images_part11.txt`
- `docs/content_factory/gemini_export/image_batch_requests/gdepar_images_part12.txt`
- `docs/content_factory/gemini_export/image_batch_requests/gdepar_images_part13.txt`
- `docs/content_factory/gemini_export/image_batch_requests/gdepar_images_part14.txt`
- `docs/content_factory/gemini_export/image_batch_requests/gdepar_images_part15.txt`
- `docs/content_factory/gemini_export/image_batch_requests/gdepar_images_part16.txt`
- `docs/content_factory/gemini_export/image_batch_requests/gdepar_images_part17.txt`
- `docs/content_factory/gemini_export/image_batch_requests/gdepar_images_part18.txt`
- `docs/content_factory/gemini_export/image_batch_requests/gdepar_images_part19.txt`
- `docs/content_factory/gemini_export/image_batch_requests/gdepar_images_part20.txt`
- `docs/content_factory/gemini_export/image_batch_requests/gdepar_images_part21.txt`
- `docs/content_factory/gemini_export/image_batch_requests/gdepar_images_part22.txt`
- `docs/content_factory/gemini_export/image_batch_requests/gdepar_images_part23.txt`
- `docs/content_factory/gemini_export/image_batch_requests/gdepar_images_part24.txt`
- `docs/content_factory/gemini_export/image_batch_requests/gdepar_images_part25.txt`
- `docs/content_factory/gemini_export/image_batch_requests/gdepar_images_part26.txt`
- `docs/content_factory/gemini_export/image_batch_requests/gdepar_images_part27.txt`
- `docs/content_factory/gemini_export/image_batch_requests/gdepar_images_part28.txt`
- `docs/content_factory/gemini_export/image_batch_requests/stern_images_part01.txt`
- `docs/content_factory/gemini_export/image_batch_requests/stern_images_part02.txt`
- `docs/content_factory/gemini_export/image_batch_requests/stern_images_part03.txt`
- `docs/content_factory/gemini_export/image_batch_requests/stern_images_part04.txt`
- `docs/content_factory/gemini_export/image_batch_requests/stern_images_part05.txt`
- `docs/content_factory/gemini_export/image_batch_requests/stern_images_part06.txt`
- `docs/content_factory/gemini_export/image_batch_requests/stern_images_part07.txt`
- `docs/content_factory/gemini_export/image_batch_requests/stern_images_part08.txt`
- `docs/content_factory/gemini_export/image_batch_requests/stern_images_part09.txt`
- `docs/content_factory/gemini_export/image_batch_requests/stern_images_part10.txt`
- `docs/content_factory/gemini_export/image_batch_requests/stern_images_part11.txt`
- `docs/content_factory/gemini_export/image_batch_requests/stern_images_part12.txt`
- `docs/content_factory/gemini_export/image_batch_requests/stern_images_part13.txt`
- `docs/content_factory/gemini_export/image_batch_requests/stern_images_part14.txt`

## После генерации

1. Положите JPG в пути из `output_file` (или в `media/_nanobanana_drop/` и запустите import).
2. `./venv/bin/python tools/apply_curated_images.py`
3. Или API: `./venv/bin/python tools/generate_curated_images_nanobanana.py`
