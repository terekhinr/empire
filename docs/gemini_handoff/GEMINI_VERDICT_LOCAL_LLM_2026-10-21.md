# Вердикт Gemini (зафиксирован владельцем) · 2026-10-21

Источник: ответ Gemini на `docs/GEMINI_HANDOFF_CURSOR_EXIT_LOCAL_LLM_2026-10.md` + пак.

## Выбор (утверждено)

| Роль | Решение |
|------|---------|
| Primary | **Ollama + `qwen2.5-coder:7b`** на RTX 4060 8 ГБ |
| Reasoning | `deepseek-r1:8b` |
| Agent | **VS Code + Roo Code** (не Cursor cloud agent) |
| Autocomplete | Continue + `qwen2.5-coder:1.5b` (день 6) |
| Cloud fallback РФ | Прямой **DeepSeek API** или **VSEGPT / ProxyAPI**; OpenRouter — только через VPN exit |
| Workflow | Клон на ПК → деплой на origin `138.124.90.47`; не Remote-SSH как основной AI-режим |

## Почему не другое

- Windsurf — ок как запасной IDE, но зависимость от чужого бэкенда снова.
- Чистый Continue без агента — слабее для «сделай задачу по репо».
- 32B/70B на 4060 — не primary.

## Поправки к ответу Gemini (важно)

1. `git clone root@IP:/root/projects/empire` — так **не** клонируют. Нужен либо `git` remote (GitHub/свой bare), либо разово `rsync`/`scp` дерева, либо уже существующий remote. На VPS репо есть (`.git`) — с ПК: добавить remote по SSH или зеркало.
2. Front `109.107.174.17` ≠ место кода; код и systemd — на **origin** `138.124.90.47`.
3. OpenRouter «не даёт модели из РФ» — лечится VPN exit **или** отказом от OpenRouter в пользу DeepSeek/VSEGPT; локальный Qwen от гео не зависит.

## Артефакты в репо после фиксации

- `AGENTS.md`
- `docs/LOCAL_AI_RULES.md`
- `.clinerules`
- `docs/LOCAL_AI_PC_SETUP_RU.md` — день 1 на Windows
