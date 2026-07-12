# Промпты Gemini · мультики-эталоны «Снегири не гири»

**Дата:** июль 2026  
**Связано:** [`snegiri_brand_prompts.md`](snegiri_brand_prompts.md) · [`snegiri_program_k_schools_audit.md`](snegiri_program_k_schools_audit.md) · `snegiri_kb/exercise_refs_data.json`

---

## 1. Стратегия: YouTube vs мультик

| Где | Что | Зачем |
|-----|-----|-------|
| **Лендинг** | Ссылки на YouTube (StrongFirst, McGill, Руднев, Денисов…) | Контекст, доверие к школам, SEO «учись у мастеров» |
| **Приложение** | **Мультик-эталон** (M/F) + CV-разбор **вашего** видео | Единый стиль, ракурс под камеру, без копирования чужих кадров |

**Лицензии:** ссылки на публичные ролики YouTube — без embed. Мультик — **оригинальный** арт бренда (не скриншоты из чужих видео). Атрибутика: футболка с **кибер-снегирем** (знак бренда), не логотипы StrongFirst/Руднева.

**Данные:** `snegiri_kb/exercise_refs_data.json` · после правок: `./scripts/sync_snegiri_exercise_refs.sh`

---

## 2. Визуальный код (как лендинг)

**Палитра — только три цвета:**
- `#000000` — фон
- `#FFFFFF` — фигура, гиря, UI, скелет CV
- `#FF3300` — **одна** линия ошибки / метка POOR (не декор)

**Стиль:** brutalist · industrial gym · high-contrast **ч/б фото-эстетика** (не мультяшность, не pastel, не wellness-smile).  
**CV-оверлей:** тонкая белая сетка скелета; на панели «ошибка» — одна красная линия/угол на проблемной зоне (поясница, таз, локоть).

**Референсы стиля:** `static/snegiri/assets/hero-poster.png`, `ad-cv-scanner.png`, `app-analyze.png`.

---

## 3. Персонажи (два эталона)

### М — мужчина
- 30–45 лет, athletic build, **не** бодибилдер
- Чёрная футболка **oversize**, на груди **белый line-art снегирь на гире** (кибер-гравюра, 8–10 см)
- Чёрные шорты/штаны, босиком или минималистичные кроссы
- Фон: тёмный зал / бетон / минимум реквизита

### F — женщина
- 28–45 лет, athletic build
- Та же **чёрная футболка с кибер-снегирем**, чёрные легgings
- Те же ракурсы и освещение, что у M (для сравнения CV)

**Гиря:** 16 кг (домашний стандарт). Для S-трека без гири — только коврик.

---

## 4. Формат выхода

| Параметр | Значение |
|----------|----------|
| Тип | Горизонтальная **лентa 4–6 панелей** (комикс-разбор) **или** один постер 16:9 с фазами слева направо |
| Размер | **1920×1080** (master), экспорт WebP 1200px ширина |
| Имена | `static/snegiri/assets/comics/{slug}_m.webp`, `{slug}_f.webp` |
| Панели | ① старт → ② ключевая фаза → ③ верх/фиксация → ④ (опц.) **ошибка** с #FF3300 |

---

## 5. Мастер-промпт (первое сообщение в Gemini)

Скопировать целиком. Прикрепить: `hero-poster.png` + `logo-final-square.png`.

```
Ты — арт-директор приложения snegirinegiri.ru («Снегири не гири»).

ЗАДАЧА: серия эталонных КОМИКС-РАЗБОРОВ упражнений для домашних тренировок.
Работаешь ПО ОДНОМУ упражнению. После каждого — имя файла и «следующий?».

ПАЛИТРА (строго):
#000000 фон · #FFFFFF линии/тело/UI · #FF3300 ТОЛЬКО линия ошибки CV

СТИЛЬ: brutalist industrial gym, ч/б фото-эстетика, НЕ мультяшность, НЕ pastel.
Поверх фигуры — белая CV-сетка (скелет). На панели ERROR — одна красная линия #FF3300.

ПЕРСОНАЖ:
- M или F (указано в задании)
- Чёрная футболка, на груди белый line-art: снегирь сидит на гире (кибер-гравюра)
- Гиря 16 кг чугунная, текстура реалистичная

ФОРМАТ: горизонталь 1920×1080, 4–6 панелей слева направо, подписи фаз мелким mono (IBM Plex Mono стиль): «1 ST», «2 DRIVE», «3 TOP», «4 ERROR»

НЕ: watermark Gemini, логотипы StrongFirst/YouTube, цвет кроме #FF3300, улыбки stock-моделей.

Начни с упражнения, которое я пришлю следующим сообщением.
```

---

## 6. Шаблон одного упражнения

Для каждого ниже — **два промпта** (M и F): заменить `{PERFORMER}` → «мужчина 35 лет» / «женщина 35 лет».

```
Упражнение: {NAME} · slug {SLUG} · comic_id {COMIC_ID}
Камера: {CAMERA}
Панели ({N}):
1. {PHASE1}
2. {PHASE2}
3. {PHASE3}
4. ERROR: {COMMON_ERROR} — красная линия #FF3300 на {ZONE}

Промпт M/F:
Horizontal 1920×1080 comic strip, 4 panels, black background #000000.
{PERFORMER}, black t-shirt with white cyber-engraving bullfinch-on-kettlebell logo on chest,
{ACTION_DESCRIPTION}.
Panel 4: same athlete, common mistake — {ERROR_VISUAL}, single #FF3300 CV error line on {ZONE}.
White skeleton overlay on athlete, industrial gym, brutalist, no color except #FF3300.
Russian mono labels under panels: {LABELS_RU}.
No watermark. File: {slug}_m.webp or {slug}_f.webp
```

---

## 7. Трек S · McGill (7 упражнений)

### S1 · curl_up · comic_s1_curl_up

| | |
|--|--|
| Камера | Сбоку 90° |
| Панели | 4 |
| Фазы | ① лёжа, руки под поясницей · ② выдох, подъём грудью · ③ пауза, поясница нейтральна · ④ ERROR: подъём шеей |
| ERROR | #FF3300 на шее/подбородке |

**Промпт M/F:** `{PERFORMER}` on mat, McGill curl-up side view. Panel 1 supine neutral spine hands under lower back. Panel 2 lift chest not neck. Panel 3 hold 2 sec. Panel 4 ERROR lifting head/chin — red line on cervical flexion. Labels: «ЛЁЖА» · «ПОДЪЁМ ГРУДЬЮ» · «ПАУЗА» · «ERROR: ШЕЯ». Files: `curl_up_m.webp`, `curl_up_f.webp`

---

### S2 · side_plank · comic_s2_side_plank

| Камера | Спереди 45° |
| Панели | 4 |
| Фазы | ① локоть под плечом · ② линия плеч–таз–колени · ③ дыхание · ④ ERROR: провис таза |
| ERROR | #FF3300 на провисающем тазе |

**Промпт:** Side plank, front 45°. Straight line shoulder-hip-knee. Panel 4 sagging hip — red line at pelvis. Labels: «ОПОРА» · «ЛИНИЯ» · «ДЕРЖИМ» · «ERROR: ТАЗ». Files: `side_plank_m.webp`, `side_plank_f.webp`

---

### S3 · bird_dog · comic_s3_bird_dog

| Камера | Сбоку |
| Панели | 4 |
| Фазы | ① четвереньки · ② противоположная рука+нога · ③ таз неподвижен · ④ ERROR: ротация таза |
| ERROR | #FF3300 на крутящемся тазе |

**Промпт:** Bird-dog quadruped side view. Extend opposite arm/leg. Stable pelvis. Panel 4 hip rotation error. Labels: «СТАРТ» · «ВЫТЯНУЛ» · «ТАЗ СТОП» · «ERROR: КРУЧЕНИЕ». Files: `bird_dog_m.webp`, `bird_dog_f.webp`

---

### S4 · pallof_press · comic_s4_pallof

| Камера | Спереди |
| Панели | 3 |
| Реквизит | Резина/эспандер у груди (не гиря) |
| ERROR | таз крутится к якорю резины |

**Промпт:** Pallof press, band at chest, front view. Press arms forward anti-rotation. Panel 3 hips rotate — red line on pelvis. Labels: «СТОЙКА» · «ЖМЁМ» · «ERROR: ТАЗ». Files: `pallof_press_m.webp`, `pallof_press_f.webp`

---

### S5 · plank_shoulder_tap · comic_s5_shoulder_tap

| Камера | Спереди |
| Панели | 4 |
| ERROR | качание таза при касании плеча |

**Промпт:** High plank shoulder tap front view. Panel 2 tap shoulder. Panel 4 hip sway — red line on pelvis. Files: `plank_shoulder_tap_m.webp`, `plank_shoulder_tap_f.webp`

---

### S6 · suitcase_carry · comic_s6_suitcase

| Камера | Спереди/сзади |
| Панели | 3 |
| Реквизит | Одна гиря 16 кг в одной руке |
| ERROR | наклон к гире |

**Промпт:** Suitcase carry one kettlebell, vertical torso front view. Panel 3 lean toward bell — red line on lateral flexion. Files: `suitcase_carry_m.webp`, `suitcase_carry_f.webp`

---

### S7 · farmer_walk · comic_s7_farmer

| Камера | Спереди |
| Панели | 3 |
| Реквизит | Две гири |
| ERROR | провисание плеч, шарканье |

**Промпт:** Farmer walk two kettlebells, upright posture front view. Panel 3 shrugged shoulders — red line on traps. Files: `farmer_walk_m.webp`, `farmer_walk_f.webp`

---

## 8. Трек K · Гиря (18 упражнений)

### K1 · hip_hinge · comic_k1_hinge

| Камера | Сбоку 90° |
| Панели | 4 |
| Фазы | ① стоя · ② таз назад, shins vertical · ③ спина нейтральна · ④ ERROR: присед вместо hinge |
| ERROR | округление поясницы |

**Промпт:** Hip hinge no swing, kettlebell at shins side view. Hinge at hips not knees. Panel 4 squat pattern — red line on rounded lumbar. Labels: «СТОЯ» · «ТАЗ НАЗАД» · «НЕЙТРАЛЬ» · «ERROR: ПРИСЕД». Files: `hip_hinge_m.webp`, `hip_hinge_f.webp`

---

### K2 · dead_stop · comic_k2_dead_stop

| Камера | Сбоку |
| Панели | 4 |
| Фазы | низ hinge · **пауза 2 сек** · подъём · ERROR: нет паузы / рывок |

**Промпт:** Dead-stop hinge, pause at bottom 2 seconds side view. Panel 4 bouncing bottom — red line timing. Files: `dead_stop_m.webp`, `dead_stop_f.webp`

---

### K3 · goblet_squat · comic_k3_goblet

| Камера | Сбоку |
| Панели | 4 |
| ERROR | пятки отрыв / округление спины |

**Промпт:** Goblet squat bell at chest side view. Knees track toes. Panel 4 heels lift — red line at heel gap. Files: `goblet_squat_m.webp`, `goblet_squat_f.webp`

---

### K4 · halo · comic_k4_halo

| Камера | Спереди |
| Панели | 3 |
| Вес | лёгкий (8–12 кг) |
| ERROR | гиря далеко от головы |

**Промпт:** Kettlebell halo around head front view, light weight. Panel 3 bell too far — red line on path. Files: `halo_m.webp`, `halo_f.webp`

---

### K5 · rack_hold · comic_k5_rack

| Камера | 45° спереди |
| Панели | 3 |
| Фазы | локти на корпус · треугольник локтей (Алferova) · ERROR: локти опущены |

**Промпт:** Rack hold front 45°, elbows on torso wrist straight. Panel 3 dropped elbows — red line. Files: `rack_hold_m.webp`, `rack_hold_f.webp`

---

### K6 · swing · comic_k6_swing

| Камера | Сбоку |
| Панели | 5 |
| Фазы | ① hinge back · ② импulse hips · ③ float · ④ vertical top · ⑤ ERROR: arm lift / hyperextension |
| Школа | StrongFirst + Руднев (маятник) |

**Промпт:** Two-hand kettlebell swing side view 5 panels. Hip drive not arms. Panel 5 hyperextension at top — red line on lumbar arch. Labels: «НАЗАД» · «ВЗРЫВ» · «ПОЛЁТ» · «ВЕРХ» · «ERROR: ПРОГИБ». Files: `swing_m.webp`, `swing_f.webp`

---

### K7 · one_arm_swing · comic_k7_one_arm

| Камера | Сбоку |
| Панели | 5 |
| ERROR | ротация корпуса |

**Промпт:** One-arm swing side view, anti-rotation core. Panel 5 torso twist — red line on ribcage rotation. Files: `one_arm_swing_m.webp`, `one_arm_swing_f.webp`

---

### K8 · hand_switch · comic_k8_hand_switch

| Камера | Сбоку |
| Панели | 5 |
| Фазы | верх маха · «мёртвая точка» · перехват · продолжение · ERROR: смена не в верхней точке |
| Школа | **Руднев / ФГОС** |

**Промпт:** Hand switch at swing top dead point side view, bell at belt height in front of body. Panel 5 early switch hitting forearm — red line on impact zone. Labels: «ВЕРХ» · «МЁРТВАЯ ТОЧКА» · «ПЕРЕХВАТ» · «МАХ» · «ERROR: РАНО». Files: `hand_switch_m.webp`, `hand_switch_f.webp`

---

### K9 · clean · comic_k9_clean

| Камера | 45° спереди |
| Панели | 5 |
| ERROR | удар по предплечью |

**Промпт:** Kettlebell clean to rack front 45°. Soft catch elbow tight. Panel 5 forearm bang — red line on forearm. Files: `clean_m.webp`, `clean_f.webp`

---

### K10 · front_squat · comic_k10_front_squat

| Камера | Сбоку |
| Панели | 4 |
| ERROR | локти опущены / гиря вперёд |

**Промпт:** Front squat from rack side view high elbows. Panel 4 elbows drop — red line. Files: `front_squat_m.webp`, `front_squat_f.webp`

---

### K11 · press · comic_k11_press

| Камера | 45° спереди |
| Панели | 4 |
| ERROR | прогиб поясницы |

**Промпт:** Strict press from rack front 45° vertical torso. Panel 4 back hyperextension — red line on lumbar. Files: `press_m.webp`, `press_f.webp`

---

### K12 · push_press · comic_k12_push_press

| Камера | 45° спереди |
| Панели | 4 |
| Фазы | dip knees · drive · press · ERROR: только руками |

**Промпт:** Push press leg dip then drive front 45°. Panel 4 arm-only press — red line on knee lack of bend. Files: `push_press_m.webp`, `push_press_f.webp`

---

### K13 · tgu_partial · comic_k13_tgu_partial

| Камера | Сбоку |
| Панели | 5 |
| Фазы | лёжа · на локоть · сесть · ERROR: согнутый локоть / гиря уезжает |

**Промпт:** TGU partial to seated side view, eyes on bell straight arm. Panel 5 bent elbow — red line. Files: `tgu_partial_m.webp`, `tgu_partial_f.webp`

---

### K14 · tgu_full · comic_k14_tgu_full

| Камера | Сбоку |
| Панели | 6 |
| Полный TGU до стоя |

**Промпт:** Full Turkish get-up side view 6 key positions left to right. Panel 6 lateral bell drift — red line. Files: `tgu_full_m.webp`, `tgu_full_f.webp`

---

### K15 · high_pull · comic_k15_high_pull

| Камера | Сбоку |
| Панели | 4 |
| ERROR | ранний подъём корпуса |

**Промпт:** High pull snatch prep elbow high side view bell at chest not overhead. Panel 4 early lean back — red line. Files: `high_pull_m.webp`, `high_pull_f.webp`

---

### K16 · snatch · comic_k16_snatch

| Камера | Сбоку |
| Панели | 5 |
| ERROR | нет фиксации / просов кисти (подсказка Руднева) |
| Школа | Руднев, Денисов, StrongFirst |

**Промпт:** One-arm snatch side view fixation overhead. Panel 5 bent arm lockout — red line on elbow. Label panel 3 optional «ПРОСОВ КИСТИ». Files: `snatch_m.webp`, `snatch_f.webp`

---

### K17 · jerk · comic_k17_jerk

| Камера | Сбоку |
| Панели | 5 |
| ERROR | отжим от груди |

**Промпт:** Kettlebell jerk from rack side view dip-drive-fixation. Panel 5 press-out — red line on elbow re-bend. Files: `jerk_m.webp`, `jerk_f.webp`

---

### K18 · complex · comic_k18_complex

| Камера | 45° спереди |
| Панели | 6 |
| Связка | clean → press → front squat |

**Промпт:** Complex clean press front squat single strip 6 panels front 45° fluid transitions. Panel 6 broken rack between moves — red line on posture. Files: `complex_m.webp`, `complex_f.webp`

---

## 9. Порядок генерации (MVP)

**Неделя 1 (блокирует CV):** K1–K3, K6, S1–S3  
**Неделя 2:** K8 hand_switch, K9 clean, K7 one-arm  
**Неделя 3:** K11 press, K16 snatch, K17 jerk  
**Остальное:** по мере открытия фаз

После каждой пары M+F: `./scripts/snegiri_compress_assets.sh` (если есть) · проверка в app → экран упражнения.

---

## 10. Чеклист приёмки кадра

- [ ] Только #000 / #FFF / #FF3300  
- [ ] Снегирь на груди читается на превью 360px  
- [ ] Ракурс совпадает с `hint` в program_data (side/front)  
- [ ] Панель ERROR одна, красная линия на правильном сегменте  
- [ ] Нет watermark / чужих логотипов  
- [ ] WebP положен в `assets/comics/` · JSON refs не менять slug

---

*YouTube-ссылки:* лендинг `#refs` · *мультики:* только app · *источник данных:* `exercise_refs_data.json`*
