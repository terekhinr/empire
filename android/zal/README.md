# Зал — нативный Android (без VPS)

Офлайн-приложение: программа, дневник, замеры, таймеры отдыха/удержания.
Данные в Room на телефоне. Постоянный синк — через Supabase (опционально).

## Сборка

```bash
cd android/zal
# при необходимости: cp local.properties.example local.properties
# sdk.dir=... и ключи Supabase
./gradlew assembleDebug
# APK: app/build/outputs/apk/debug/app-debug.apk
# копия: zal-debug.apk (после сборки)
```

Установка: разрешить неизвестные источники → открыть APK.

## Облако

См. [docs/health/ZAL_ANDROID_SUPABASE.md](../../docs/health/ZAL_ANDROID_SUPABASE.md).

Без ключей приложение полностью работает офлайн. Вкладка «Облако» → импорт бэкапа с VPS.

## Формат программ

`empire-workout-program/v1` — в assets уже `gym_2026`, `outside_hall`, пример.
