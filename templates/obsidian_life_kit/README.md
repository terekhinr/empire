# Life kit — один раз в vault (Яндекс.Диск)

Скопируйте **всю папку** `obsidian_life_kit` в vault:

```text
F:\YandexDisk\obsidian (2)\Life\tools\
```

Структура после копирования:

```text
Life/tools/ticktick_csv_to_obsidian.py
Life/tools/voice_to_obsidian.py
Life/tools/sync_evrec_to_life.ps1
Life/tools/README.md
```

Репозиторий Empire на ПК **не нужен**. VPS по-прежнему синхронизирует только `Empire/`, не `Life/`.

Как скопировать с VPS в vault на ПК:

1. В Cursor (SSH к серверу) откройте `templates/obsidian_life_kit/`.
2. Скопируйте файлы в `F:\YandexDisk\obsidian (2)\Life\tools\` (проводник / Яндекс.Диск).

Geminese — отдельно: `templates/obsidian_plugins/geminese/` →  
`F:\YandexDisk\obsidian (2)\.obsidian\plugins\geminese\`

**Windows + API key:** скопируйте `geminese-launcher.js` в  
`C:\Users\ВЫ\.gemini\geminese-launcher.js`  
и в Geminese укажите этот путь как **Gemini CLI path**.  
Ключ только в `C:\Users\ВЫ\.gemini\.env` → `GEMINI_API_KEY=...`  
Если снова не взлетит — **выключите Geminese**, пользуйтесь `gemini` в терминале из vault.

**Easy Voice Recorder (Google Drive `G:\Мой диск\Easy Voice Recorder\`):**

```powershell
powershell -ExecutionPolicy Bypass -File "F:\YandexDisk\obsidian (2)\Life\tools\sync_evrec_to_life.ps1" -Transcribe
```

Гайд: `docs/obsidian_evening_setup_ru.md`
