# День 1: локальный AI на ПК (Windows + RTX 4060)

Цель: **VS Code + Roo Code + Ollama `qwen2.5-coder:7b`**, без Cursor cloud.

## 1. Ollama

1. Скачать с https://ollama.com → установить.
2. PowerShell:

```powershell
ollama pull qwen2.5-coder:7b
ollama pull deepseek-r1:8b
# опционально позже:
# ollama pull qwen2.5-coder:1.5b
ollama list
```

Проверка: `ollama run qwen2.5-coder:7b` → короткий вопрос → ответ без ошибок CUDA/OOM.

## 2. VS Code + Roo Code

1. Установить VS Code (не Cursor, или Cursor только как редактор с отключённым AI).
2. Extensions → **Roo Code** (Roo Cline).
3. Settings → API Provider → **Ollama**.
4. Base URL: `http://localhost:11434`
5. Model: `qwen2.5-coder:7b`
6. Открыть папку клона `empire` — Roo подхватит `.clinerules` и `AGENTS.md`.

## 3. Клон репо на ПК (не Remote-SSH как основной режим)

**Вариант A — уже есть git remote (GitHub и т.п.):**

```powershell
git clone <url> empire
cd empire
```

**Вариант B — только VPS, без GitHub:** с ПК (нужен SSH-ключ на `138.124.90.47`):

```powershell
# разово зеркало
scp -r root@138.124.90.47:/root/projects/empire C:\src\empire
# дальше работа локально; деплой — см. ниже
```

Или на VPS сделать bare remote / использовать существующий `.git` + `git remote add` с ПК через SSH URL вида `ssh://root@138.124.90.47/root/projects/empire` (если настроен receive). Проще для старта: **rsync/scp изменённых файлов** + на VPS `systemctl restart …`.

SSH-ключ и keepalive: `docs/cursor_vps_ssh_ru.md`, скрипт `scripts/cursor_vps_ssh_setup_pc.ps1`.

## 4. Облачный fallback (когда 7B слабо / РФ)

| Путь | Когда |
|------|--------|
| https://platform.deepseek.com | Прямой API, без гео-блокировок Anthropic |
| VSEGPT / ProxyAPI | Нужен Claude с оплатой РФ |
| OpenRouter | Только если запросы идут с VPN exit (Flint/Amnezia), не с голого РФ IP |

В Roo завести второй профиль «Cloud» и включать вручную для `[ARCH]` / `[CRITICAL]`.

## 5. Критерий «день 1 готов»

- [ ] `ollama list` показывает `qwen2.5-coder:7b`
- [ ] Roo отвечает в чате по открытому `AGENTS.md`
- [ ] Локальная правка одного `.md` в `docs/` сохраняется
- [ ] Cursor Pro можно не отменять до дня 3–7 (пока стек не проверен)

Дальше: `docs/LOCAL_AI_RULES.md` (план 7 дней) · вердикт `docs/gemini_handoff/GEMINI_VERDICT_LOCAL_LLM_2026-10-21.md`.
