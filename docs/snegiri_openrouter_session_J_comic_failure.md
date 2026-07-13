# OpenRouter · Сессия J

**Дата:** 2026-07-13 13:33 UTC  
**Модель:** `deepseek/deepseek-chat`  
**Провайдер:** [OpenRouter](https://openrouter.ai)
**Токены:** `{"prompt_tokens": 409, "completion_tokens": 984, "total_tokens": 1393, "cost": 0.0008691802, "is_byok": false, "prompt_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0, "audio_tokens": 0, "video_tokens": 0}, "cost_details": {"upstream_inference_cost": 0.0008691802, "upstream_inference_prompt_cost": 8.18818e-05, "upstream_inference_completions_cost": 0.0007872984}, "completion_tokens_details": {"reasoning_tokens": 0, "image_tokens": 0, "audio_tokens": 0}}`

---

```markdown
### 1. Классификация дефектов
| Категория               | Частота | Корневая причина                     | Fix в процессе          |
|-------------------------|---------|---------------------------------------|-------------------------|
| Инвентарь в кадре       | 40%     | Промпт без запрета фона               | `FORBID: gym equipment` |
| Языковой хаос           | 35%     | Отсутствие языкового контроля         | Единый язык в brief     |
| Несоответствие гирь     | 25%     | Разные промпты для M/F                | Унифицированные веса    |
| Ошибки техники (F)      | 30%     | Стереотипные позы в датасетах         | Жёсткие референсы       |
| Промпт-загрязнение      | 50%     | Industrial-стиль в тренировочных данных| `FORBID: industrial`    |

---

### 2. TOP-15 Negative Prompts (EN)
```text
1. gym equipment, barbell, weight plates, power rack
2. industrial lighting, concrete walls, warehouse
3. incorrect kettlebell form, elbows flaring
4. mixed languages, Russian text, Cyrillic
5. asymmetric kettlebell holds
6. distorted anatomy, extra limbs
7. cluttered background
8. low contrast, overexposed
9. bodybuilder physique (если не цель)
10. sweat droplets (если не реализм)
11. cartoonish style
12. watermark, logo
13. unsafe exercise form
14. mirrored kettlebells (2 вместо 1)
15. incorrect foot placement
```

---

### 3. TOP-10 Positive Mandatory Lines (EN)
```text
1. Professional fitness photography
2. Single kettlebell centered in frame
3. Perfect exercise form according to [Alferova method]
4. Neutral background, studio lighting
5. Gender-specific stance (male/female)
6. Dynamic tension visible in muscles
7. High-resolution, 8K detail
8. Consistent language: English only
9. Minimalist composition
10. Anatomically correct proportions
```

---

### 4. Почему F без M обречена
**Технически:**  
- Датсеты перекошены в сторону male-dominated фитнес-контента → женские позы генерируются как "эстетичные", а не техничные.  
**Процессно:**  
- Разные промпты для M/F → дрифт стиля. Без параллельной генерации невозможно сохранить единую методологию (например, гири 24кг у M и 16кг у F должны быть согласованы).

---

### 5. Критерии спасения контента
**Сохранить:**  
- Кадры без инвентаря в фоне + корректная техника (локти, стойка).  
**В архив:**  
- Всё с mixed languages, зеркальными гирями, industrial-стилем.  
**Порог:** 5/50 (10%) при ручной выборке.

---

### 6. Сообщение основателю
"Выбросили 45/50 лент из-за системных ошибок: неконтролируемый инвентарь, разнобой в технике и языковой бардак. Это правильно — такой контент дискредитирует методологию и порождает юридические риски (травмоопасные демонстрации). Пилот: 2 упражнения (толчок и фермерская прогулка) с жёстким Чек-листом перед генерацией."

---

### Пилот (2 упражнения)
1. **Kettlebell Clean**  
   - `Positive:` + строка 3 + "kettlebell in rack position, elbow touching iliac crest"  
   - `Negative:` + "elbows flaring, kettlebell swinging"  

2. **Overhead Press**  
   - `Positive:` + "straight wrist alignment, core braced"  
   - `Negative:` + "arched lower back, leaning backwards"
``` 

**Жёсткие требования к пилоту:**  
- Генерация M/F в одной сессии  
- Референс-видео в промпте (ссылка на Alferova)  
- Post-audit через фитнес-эксперта.
