# Задачник — Android

Минимальный APK: WebView на `https://neverretire.ru/tasks/` + виджет «Следующие 7 дней».

## Сборка (на ПК с Android Studio)

1. Открой папку `android/zadachnik` в Android Studio (Giraffe+).
2. Дождись Gradle Sync (скачает SDK при необходимости).
3. **Build → Build Bundle(s) / APK(s) → Build APK(s)**.
4. Установи APK на телефон (разрешить установку из неизвестных источников).

Или из CLI (если есть Android SDK):

```bash
cd android/zadachnik
./gradlew assembleDebug
# app/build/outputs/apk/debug/app-debug.apk
```

## Первый запуск

1. Введи тот же **PLANNING_API_TOKEN**, что в веб-Задачнике.
2. Долгое нажатие на рабочий стол → **Виджеты** → **Задачник · 7 дней**.
3. Тап по ○ — отметить задачу; «+» — новая; ⋮ — обновить.

## Дальше

См. `docs/zadachnik_android_and_singularity.md`.
