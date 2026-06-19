# Устарело как единственная точка входа.

Рекомендуемый путь на VPS: **`data/obsidian_vault/Empire/`** (все каналы, все `queue/`).

Синхронизация с ПК: `docs/obsidian_sync_vps_ru.md`

Локально без облака можно symlink:
`ln -s .../obsidian_vault/Empire/pension/queue data/obsidian_incoming`

---

# Старый вариант — одна папка incoming:

```bash
./venv/bin/python scripts/import_obsidian_queue.py
```

Пошагово (Obsidian → Telegram): **`docs/obsidian_practical_guide_ru.md`** · Технически: `docs/empire_obsidian_integration.md`
