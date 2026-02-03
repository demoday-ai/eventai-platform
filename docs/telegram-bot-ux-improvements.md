# Telegram Bot UI/UX Improvements

## Текущее состояние

### Реализованные хэндлеры
✅ **Onboarding** (`start.py`):
- Выбор роли (5 ролей)
- Подтипы для гостей (AI-практик, Абитуриент, Рекрутер и т.д.)
- Auto-trigger profiling для гостей и бизнеса

✅ **Бизнес-профилирование** (`business_profiling.py`):
- Objective (Investment, Hiring, Technology, Partnership)
- Industries (multi-select с ✓ маркерами)
- Stages (multi-select)

✅ **Другие модули**:
- Clustering, Expert assignment, Confirmation
- Schedule, Reminders, Feedback
- Q&A helper, Business follow-up
- Coverage, Dashboard, Briefing

### Текущие паттерны UI

**InlineKeyboard patterns:**
```python
# 1. Вертикальные списки (роли, подтипы)
[[Button1], [Button2], [Button3]]

# 2. Пагинация (◀ 1/5 ▶)
[[Button◀], [Page counter], [Button▶]]

# 3. Multi-select (✓ маркеры)
[[✓ FinTech], [EdTech], [✓ NLP]]

# 4. Горизонтальные группы (действия)
[[Перегенерировать, Утвердить]]
```

---

## 🎨 Рекомендации по улучшению UI/UX

### 1. **Добавить эмодзи для визуальной навигации**

**Проблема:** Текстовые кнопки выглядят однообразно, сложно быстро сканировать.

**Решение:**
```python
# ❌ Было
["Студент", "Эксперт", "Гость", "Бизнес-партнёр"]

# ✅ Стало
["📋 Студент", "👨‍🏫 Эксперт", "👥 Гость", "💼 Бизнес-партнёр"]
```

**Эмодзи-гайд:**
- 📋 Студент
- 👨‍🏫 Эксперт
- 👥 Гость
- 💼 Бизнес-партнёр
- ⚙️ Организатор
- 🏠 Залы
- 🎯 Проекты
- ⏰ Расписание
- ⭐ Оценки
- 📊 Статистика
- ✅ Подтверждено
- ⏳ Ожидает
- ❌ Отменено
- 🔔 Напоминания
- 💡 Рекомендации

---

### 2. **Progress indicators для многошаговых флоу**

**Проблема:** Пользователь не понимает, сколько ещё шагов осталось.

**Решение:**
```python
# Business profiling flow
"Шаг 1/4: Какая у вас цель?"  # Objective
"Шаг 2/4: Какие отрасли интересны?"  # Industries
"Шаг 3/4: Какая стадия проектов?"  # Stages
"Шаг 4/4: Опишите задачу (опционально)"  # Task description
```

**Визуализация:**
```
🟢🟢🟡⚪ Шаг 3/4: Выберите стадии проектов
```

---

### 3. **Улучшить onboarding welcome message**

**Проблема:** Слишком сухое приветствие.

**Решение:**
```python
# ❌ Было
"Добро пожаловать на Demo Day, {name}!\n\nВыберите вашу роль:"

# ✅ Стало
"""
👋 Привет, {name}!

Это AI-агент Demo Day 2026. Я помогу:
• Найти интересные проекты
• Составить личную программу
• Получить напоминания
• Организовать встречи 1:1

Для начала выберите вашу роль:
"""
```

---

### 4. **Inline preview для выбранных фильтров**

**Проблема:** В multi-select неясно, что уже выбрано.

**Решение:**
```python
# После выбора industries
"✓ Выбрано: FinTech, NLP, EdTech\n\nВыберите стадии проектов:"

# При пересмотре
"Ваш профиль:\n• Цель: Инвестиции\n• Отрасли: FinTech, NLP\n• Стадии: MVP, Масштабирование"
```

---

### 5. **Быстрые действия (Quick Actions)**

**Проблема:** Нет главного меню, приходится помнить команды.

**Решение:** Добавить **ReplyKeyboardMarkup** с быстрыми действиями по ролям.

**Для Гостя:**
```python
[["📊 Моя программа", "🔍 Найти проект"],
 ["⏰ Расписание", "🔔 Настройки"]]
```

**Для Эксперта:**
```python
[["🎯 Мои залы", "⭐ Оценить проект"],
 ["⏰ Расписание", "📋 Список проектов"]]
```

**Для Организатора:**
```python
[["📊 Dashboard", "🏠 Покрытие"],
 ["📋 Все проекты", "⚙️ Настройки"]]
```

---

### 6. **Contextual help hints**

**Проблема:** Непонятно, зачем нужен каждый шаг.

**Решение:** Добавить tooltips/hints.

```python
# При выборе objective
"""
Какая у вас цель на Demo Day?

💡 Подсказка: Мы подберём проекты и вопросы
   под вашу задачу. Это займёт 2 минуты.

[💰 Инвестиции]
[🤝 Партнёрство]
[🛠️ Технологии]
[👔 Наём]
"""
```

---

### 7. **Rich media для рекомендаций**

**Проблема:** Текстовые списки проектов скучные.

**Решение:** Использовать форматирование Markdown v2.

```python
# Вместо
"Чатбот для поддержки\nКоманда А\n10:00-10:15"

# Использовать
"""
🎯 *Чатбот для поддержки*
👥 Команда А
🏠 Зал 1: NLP
⏰ 10:00-10:15
🏷️ #NLP #Chatbot

_Подходит под ваши интересы: FinTech, NLP_
"""
```

---

### 8. **Персонализированные нотификации**

**Проблема:** Стандартные напоминания игнорируются.

**Решение:**
```python
# ❌ Generic
"Через час начинается ваш слот"

# ✅ Персонализированное
"""
🔔 Через час!

📍 Зал 1: NLP
🎯 Чатбот для поддержки (Команда А)
⏰ 10:00-10:15

💡 Вопросы для Q&A:
• Как обрабатываете edge cases?
• Планы по монетизации?

[Посмотреть проект] [Отменить]
"""
```

---

### 9. **Gamification элементы**

**Идеи:**
```python
# После оценки проектов
"""
✅ Проект оценён!

Ваш прогресс сегодня:
🎯 Посещено: 5/12 проектов
⭐ Оценено: 3 проекта
🏆 Уровень: Активный эксперт

Продолжайте в том же духе! 🔥
"""

# Achievements
"🏅 Получен бейдж: 'Эксперт дня' (оценил 10+ проектов)"
```

---

### 10. **Улучшить error handling**

**Проблема:** Generic ошибки пугают.

**Решение:**
```python
# ❌ Было
"Ошибка. Попробуйте /start заново."

# ✅ Стало
"""
⚠️ Что-то пошло не так

Попробуйте:
1️⃣ Обновить данные: /start
2️⃣ Связаться с поддержкой: @support

Код ошибки: #DB_USER_NOT_FOUND
"""
```

---

### 11. **Smart defaults**

**Идея:** Угадывать намерения на основе контекста.

```python
# Если гость-рекрутер
default_industries = ["EdTech", "FinTech"]  # Популярные для найма

# Если гость-инвестор
default_stages = ["early_traction", "scaling"]  # Интересны для инвестиций

# Показать с предзаполнением
"Мы предположили, что вам интересны:\n✓ FinTech\n✓ EdTech\n\nИзмените при необходимости:"
```

---

### 12. **Conversational UI вместо форм**

**Проблема:** Чекбоксы и формы кажутся формальными.

**Решение:** Natural language processing.

```python
# Вместо многошаговой формы
"""
Опишите свой интерес в свободной форме:

Например:
"Ищу проекты по NLP для финтеха на стадии MVP"
"Интересны AI-агенты для автоматизации HR"

[Пропустить и выбрать вручную]
"""

# LLM парсит и предлагает подтверждение
"""
Я понял ваш запрос:
• Отрасль: FinTech
• Технологии: NLP
• Стадия: MVP

Всё верно?
[Да, найти проекты] [Уточнить]
"""
```

---

## 📋 Приоритизация (RICE)

| Улучшение | Reach | Impact | Confidence | Effort | RICE | Приоритет |
|-----------|-------|--------|------------|--------|------|-----------|
| 1. Эмодзи в кнопках | 100% | 3 | 100% | 1 | 300 | 🔥 High |
| 5. Quick Actions | 100% | 3 | 80% | 2 | 120 | 🔥 High |
| 3. Welcome message | 100% | 2 | 100% | 0.5 | 400 | 🔥 High |
| 2. Progress bars | 60% | 2 | 80% | 1 | 96 | 🟡 Medium |
| 4. Filter preview | 40% | 2 | 90% | 1 | 72 | 🟡 Medium |
| 7. Rich media | 80% | 3 | 70% | 3 | 56 | 🟡 Medium |
| 8. Personalized notif | 80% | 3 | 60% | 4 | 36 | 🟢 Low |
| 12. Conversational UI | 60% | 3 | 50% | 8 | 11.25 | 🟢 Low |

**Quick wins (высокий RICE, низкий Effort):**
1. ✅ Добавить эмодзи (RICE: 300, Effort: 1)
2. ✅ Улучшить welcome message (RICE: 400, Effort: 0.5)
3. ✅ Quick Actions меню (RICE: 120, Effort: 2)

---

## 🎯 План реализации

### Phase 1: Visual Polish (2-3 часа)
- [ ] Добавить эмодзи во все клавиатуры
- [ ] Улучшить welcome message
- [ ] Добавить tooltips/hints
- [ ] Rich media форматирование (Markdown v2)

### Phase 2: Navigation (3-4 часа)
- [ ] Quick Actions ReplyKeyboard по ролям
- [ ] Main menu command (`/menu`)
- [ ] Breadcrumbs в длинных флоу

### Phase 3: Feedback (2-3 часа)
- [ ] Progress indicators (🟢🟡⚪)
- [ ] Inline filter preview
- [ ] Better error messages

### Phase 4: Personalization (4-5 часов)
- [ ] Smart defaults по роли
- [ ] Персонализированные уведомления
- [ ] Gamification элементы

### Phase 5: Advanced (8+ часов)
- [ ] Conversational UI с LLM
- [ ] Voice messages support
- [ ] Inline mode для шеринга

---

## 📊 Метрики успеха

**До улучшений:**
- Conversion rate onboarding: ?
- Time to complete profiling: ?
- % пользователей, завершивших профилирование: ?

**После улучшений (целевые метрики):**
- ✅ Conversion rate onboarding: +20%
- ✅ Time to complete: -30%
- ✅ Completion rate: +40%
- ✅ Daily active users: +25%

**Отслеживать:**
- Bounce rate на каждом шаге onboarding
- Most used quick actions
- Error frequency по типам

---

## 🎨 Design System

### Эмодзи-палитра
```python
EMOJI = {
    # Roles
    "student": "📋",
    "expert": "👨‍🏫",
    "guest": "👥",
    "business": "💼",
    "organizer": "⚙️",

    # Status
    "confirmed": "✅",
    "pending": "⏳",
    "declined": "❌",
    "warning": "⚠️",

    # Actions
    "search": "🔍",
    "schedule": "⏰",
    "notification": "🔔",
    "settings": "⚙️",
    "star": "⭐",
    "target": "🎯",

    # Content
    "project": "🎯",
    "room": "🏠",
    "dashboard": "📊",
    "tag": "🏷️",
    "question": "❓",
    "idea": "💡",
}
```

### Tone of Voice
- **Дружелюбный**, но профессиональный
- **Краткий** — не более 2-3 предложений
- **Actionable** — всегда понятно, что делать дальше
- **Персональный** — обращение по имени, контекстные советы

---

## 📝 Примеры кода

### Quick Actions Keyboard
```python
def get_quick_actions_keyboard(role_code: RoleCode) -> ReplyKeyboardMarkup:
    """Role-specific quick actions keyboard."""
    keyboards = {
        RoleCode.GUEST: [
            ["📊 Моя программа", "🔍 Найти проект"],
            ["⏰ Расписание", "🔔 Настройки"],
        ],
        RoleCode.EXPERT: [
            ["🎯 Мои залы", "⭐ Оценить проект"],
            ["⏰ Расписание", "📋 Список проектов"],
        ],
        RoleCode.ORGANIZER: [
            ["📊 Dashboard", "🏠 Покрытие"],
            ["📋 Все проекты", "⚙️ Настройки"],
        ],
    }
    return ReplyKeyboardMarkup(
        keyboards.get(role_code, [["⚙️ Главное меню"]]),
        resize_keyboard=True
    )
```

### Progress Bar
```python
def format_progress(current: int, total: int) -> str:
    """Format progress bar: 🟢🟢🟡⚪⚪"""
    filled = "🟢" * current
    active = "🟡" if current < total else ""
    empty = "⚪" * (total - current - (1 if active else 0))
    return f"{filled}{active}{empty}"

# Usage
progress = format_progress(2, 4)  # 🟢🟢🟡⚪
text = f"{progress} Шаг 3/4: Выберите стадии проектов"
```

### Rich Recommendation
```python
def format_project_card(project, match_score: float) -> str:
    """Format project with rich markdown."""
    return f"""
🎯 *{escape_markdown(project.title)}*
👥 {escape_markdown(project.author)}
🏠 {escape_markdown(project.room.name)}
⏰ {project.start_time.strftime('%H:%M')}-{project.end_time.strftime('%H:%M')}
🏷️ {' '.join(f'#{tag}' for tag in project.tags[:3])}

_Совпадение: {match_score:.0%} с вашим профилем_

[Добавить в программу](callback://add_{project.id})
"""
```
