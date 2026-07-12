# Ассеты лендинга «Снегири не гири»

## Готово (PNG от Gemini, июль 2026)

| Файл | Блок |
|------|------|
| `hero-mockup-screen.png` | Hero |
| `track-01-spine.png`, `track-02-kettlebell.png` | Треки |
| `trainer-photo.png` | Trust |
| `og-image.png` | OG / соцсети |
| `app-record.png`, `app-analyze.png`, `app-result.png` | App preview |

## Дополнительно залито (не в index.html)

| Файл | Заметка |
|------|---------|
| `benefit-01-efficiency.png` … `benefit-03-validation.png` | можно добавить блок «преимущества» |
| `trainer-hero.png` | альтернатива hero |
| `footer-bg.png` | фон футера |

## SVG (в коде)

logo, step-01…03, lock, medical, tg, vk, cv-badge, og-image.svg (fallback)

## Оптимизация

✅ Сжато июль 2026: WebP ~1.3 MB суммарно, PNG fallback ~3.4 MB (было ~100 MB).

Повторить после новых картинок от Gemini:

```bash
./scripts/snegiri_compress_assets.sh
```

Браузер берёт `.webp` из `<picture>`, PNG — fallback.
