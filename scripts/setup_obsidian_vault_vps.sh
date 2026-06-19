#!/usr/bin/env bash
# Создаёт дерево Empire на VPS (вариант A). Без rclone — только папки и README.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VAULT="${VAULT_ROOT:-$ROOT/data/obsidian_vault/Empire}"

CHANNELS=(pension gdepar garden stern lenin)
SUBS=(inbox queue published)

mkdir -p "$VAULT"
for ch in "${CHANNELS[@]}"; do
  for sub in "${SUBS[@]}"; do
    d="$VAULT/$ch/$sub"
    mkdir -p "$d"
    touch "$d/.gitkeep"
  done
done

mkdir -p "$VAULT/_scenarios" "$VAULT/_canvas"
cat > "$VAULT/README.md" <<'EOF'
# Empire (Obsidian → Telegram, вариант A)

- **queue/** — готовые посты (`status: ready`) → импорт на VPS
- **inbox/** — черновики, бот не трогает
- **published/** — архив после «Опубликовать»
- **_canvas/**, **_scenarios/** — планы, не импортируются

На ПК: та же структура в `YandexDisk/obsidian (2)/Empire/`.
Синхронизация: rclone → см. `docs/obsidian_sync_vps_ru.md`.
EOF

# Пример заметки (не в queue — не уйдёт в бот)
EXAMPLE="$VAULT/pension/inbox/EXAMPLE-ne-v-queue.md"
if [[ ! -f "$EXAMPLE" ]]; then
  cat > "$EXAMPLE" <<'EOF'
---
status: draft
---

Черновик: перенесите в `pension/queue/` и добавьте frontmatter из `templates/obsidian_empire_post.md`.
EOF
fi

echo "OK: $VAULT"
find "$VAULT" -type d | sort
