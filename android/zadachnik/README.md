# Зал — Android

APK открывает `https://neverretire.ru/tasks/?app=gym&view=program` (учёт тренировок, замеры, графики).
Виджет задач на рабочем столе остаётся отдельным («Задачник · 7 дней»).

Формат программ: `docs/health/WORKOUT_PROGRAM_FORMAT.md`.

## Сборка

```bash
cd /root/projects/empire/android/zadachnik
./gradlew assembleDebug
# app/build/outputs/apk/debug/app-debug.apk
# копия: android/zadachnik/zadachnik-debug.apk
```

Установка: разрешить неизвестные источники → открыть APK → токен `PLANNING_API_TOKEN`.

Ярлыки (долгое нажатие на иконку): Тренировка, Замеры, Статистика, Дневник.
