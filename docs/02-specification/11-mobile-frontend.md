# Mobile Frontend Specification v1.0

## Контекст

Admin Console (React + Tailwind + shadcn/ui) -- веб-панель для организаторов (~5 человек). Текущее состояние:

- Sidebar фиксированной ширины 224px (`w-56`), всегда видим
- Нет hamburger-меню, нет скрытия sidebar на мобильных
- Таблицы используют `overflow-x-auto` (горизонтальный скролл)
- Грид-раскладки адаптивные: `grid-cols-1 → md:grid-cols-2 → lg:grid-cols-4`
- Landing page уже mobile-first

**Проблема:** на экранах < 768px sidebar занимает ~60% ширины, оставляя ~320px для контента. Таблицы, визарды и формы нечитабельны.

**Целевые устройства:** смартфоны организаторов (iPhone 13+, Samsung Galaxy S21+), планшеты (iPad). Основной сценарий -- оперативный контроль во время Demo Day (проверить dashboard, посмотреть покрытие, отправить уведомление).

---

## Breakpoints

| Токен | Ширина | Устройства | Поведение sidebar |
|-------|--------|------------|-------------------|
| `sm` | < 640px | Смартфоны | Скрыт, hamburger в header |
| `md` | 640-1023px | Планшеты, landscape-телефоны | Скрыт, hamburger в header |
| `lg` | >= 1024px | Десктоп | Видим постоянно (текущее поведение) |

---

## 1. Layout: AppLayout + Sidebar

### 1.1 Header (AppLayout.tsx)

**Текущее:** `<header>` с названием приложения и кнопкой "Выйти".

**Изменения:**

- Добавить hamburger-кнопку слева, видимую на `< lg`:
  ```
  [=] Demo Day Admin          ID: 123 [Выйти]
  ```
- На `lg+` hamburger скрыт, layout без изменений.
- Header: `sticky top-0 z-40` на мобильных для постоянного доступа к меню.

### 1.2 Sidebar (Sidebar.tsx)

**Текущее:** `<aside className="w-56 border-r">`, всегда видим.

**Изменения:**

- На `< lg`: sidebar становится overlay-панелью поверх контента.
  - Позиционирование: `fixed inset-y-0 left-0 z-50 w-64`.
  - Backdrop: полупрозрачный overlay (`bg-black/50`), клик закрывает.
  - Анимация: slide-in слева (`translate-x` transition, 200ms).
  - Закрытие: клик по backdrop, клик по пункту меню, свайп влево (опционально).
- На `lg+`: поведение без изменений.
- Состояние `isOpen` управляется в `AppLayout` через `useState`, передается в Sidebar.

### 1.3 Main content area

**Текущее:** `<main className="flex-1 overflow-auto p-6">`.

**Изменения:**

- На `< md`: padding `p-4` вместо `p-6`.
- На `< lg`: main занимает 100% ширины (sidebar скрыт).

---

## 2. Страницы

### 2.1 Dashboard

**Текущее:** 4 метрики в `grid-cols-1 md:grid-cols-2 lg:grid-cols-4`, таблица покрытия, алерты.

**Изменения:**

- Метрики: `grid-cols-2` на мобильных (компактные карточки по 2 в ряд).
- Карточки метрик: уменьшить padding (`p-3` вместо `p-6`), шрифт числа `text-2xl` вместо `text-3xl`.
- Таблица покрытия: сохранить `overflow-x-auto`, добавить hint "Проведите для прокрутки &rarr;" на `< md`.
- Алерты: полная ширина, без изменений.

### 2.2 Clustering, ExpertMatching, Schedule (визарды)

**Текущее:** Stepper + контент, карточки в `md:grid-cols-2 lg:grid-cols-3`.

**Изменения:**

- Stepper: на `< sm` показывать только текущий шаг (compact stepper): `"Шаг 2 из 4"`.
- Карточки комнат/экспертов: `grid-cols-1` на мобильных, каждая карточка полная ширина.
- Кнопки действий ("Запустить", "Подтвердить"): `w-full` на мобильных, sticky внизу экрана.

### 2.3 DataImport

**Текущее:** 3 таба (проекты, эксперты, гости), upload area.

**Изменения:**

- Табы: горизонтальный скролл (`overflow-x-auto flex gap-2`) вместо wrap.
- Upload area: полная ширина, увеличить touch-target до 48px минимум.
- Результаты импорта: карточки вместо inline-текста.

### 2.4 Coverage

**Текущее:** 4 метрики, 3 таба, таблица с экспертами и комнатами.

**Изменения:**

- Метрики: `grid-cols-2` на мобильных.
- Таблица: `overflow-x-auto`, фиксировать первый столбец (имя эксперта) через `sticky left-0`.
- Табы: горизонтальный скролл.

### 2.5 Notifications

**Текущее:** 4 метрики, 3 таба, таблица уведомлений.

**Изменения:**

- Метрики: `grid-cols-2`.
- Таблица: на `< md` карточный вид вместо таблицы. Каждая строка -- карточка:
  ```
  [Тип иконка] Имя пользователя
  Статус: Доставлено | 12:34
  ```

### 2.6 Participation

**Текущее:** Метрики + таблица участников.

**Изменения:**

- Аналогично Notifications: таблица &rarr; карточки на `< md`.
- Фильтры: вертикальный стек (`flex-col`) вместо горизонтального.

### 2.7 Messaging, Briefing

**Текущее:** Текстовая форма + превью + отправка.

**Изменения:**

- Форма: `w-full`, textarea на полную ширину.
- Кнопки: `w-full` на мобильных, стек вертикально.
- Превью: в модальном окне (sheet снизу) вместо inline.

### 2.8 ProjectsList, ExpertList

**Текущее:** Списки/таблицы.

**Изменения:**

- На `< md`: карточный вид. Каждый проект/эксперт -- отдельная карточка.
- Поиск/фильтры: `w-full`, sticky сверху.

### 2.9 Settings

**Текущее:** Форма с полями.

**Изменения минимальны:** поля уже `w-full`, адаптируются.

### 2.10 Landing

**Без изменений** -- уже mobile-first с адаптивными классами.

---

## 3. Компоненты

### 3.1 Touch targets

Все интерактивные элементы: минимальный размер 44x44px (Apple HIG) / 48x48dp (Material).

- Кнопки: уже `h-9` (36px) -- увеличить до `h-10` (40px) на `< md` или обеспечить spacing.
- Ссылки в sidebar: padding `py-2` (32px + text = ~40px) -- достаточно.
- Inline-кнопки в таблицах: группировать в dropdown-меню вместо ряда мелких кнопок.

### 3.2 Модальные окна

Текущие inline-формы (ExpertFormDialog, edit-формы в Schedule) -- на `< md` показывать как bottom sheet (full-width, slide-up снизу).

### 3.3 Таблицы

Два режима в зависимости от контента:

| Режим | Когда | Пример |
|-------|-------|--------|
| Горизонтальный скролл | Данные структурно табличные, мало строк | Coverage matrix |
| Карточный вид | Много строк, 3-5 значимых полей | Notifications, Participation |

### 3.4 Stepper (stepper.tsx)

- На `lg+`: горизонтальный, все шаги видны (текущее поведение).
- На `< lg`: compact-режим: `"Шаг N из M — Название шага"`.

---

## 4. Состояние и навигация

### 4.1 Sidebar state

```
AppLayout:
  const [sidebarOpen, setSidebarOpen] = useState(false)
```

- Hamburger click: `setSidebarOpen(true)`
- NavLink click / backdrop click: `setSidebarOpen(false)`
- Resize to `lg+`: auto-close overlay (useEffect на `matchMedia`)

### 4.2 Route transitions

Без SPA-анимаций. При переходе sidebar закрывается, скролл сбрасывается наверх.

### 4.3 Pull-to-refresh

Не реализуем. TanStack Query `refetchInterval` на Dashboard (60s) достаточно. Ручной refresh через кнопку.

---

## 5. Затронутые файлы

| Файл | Изменение |
|------|-----------|
| `components/layout/AppLayout.tsx` | Hamburger, sidebar state, sticky header, responsive padding |
| `components/layout/Sidebar.tsx` | Overlay mode, backdrop, close-on-navigate, transition |
| `components/ui/stepper.tsx` | Compact mode для `< lg` |
| `pages/Dashboard.tsx` | `grid-cols-2` на мобильных, compact cards |
| `pages/Clustering.tsx` | `grid-cols-1`, sticky action buttons |
| `pages/ExpertMatching.tsx` | `grid-cols-1`, sticky action buttons |
| `pages/Schedule.tsx` | `grid-cols-1`, compact edit forms |
| `pages/Coverage.tsx` | `grid-cols-2` метрики, sticky column |
| `pages/Notifications.tsx` | Card view на `< md` |
| `pages/Participation.tsx` | Card view на `< md` |
| `pages/Messaging.tsx` | Full-width form, vertical buttons |
| `pages/Briefing.tsx` | Full-width form, vertical buttons |
| `pages/ProjectsList.tsx` | Card view на `< md` |
| `pages/ExpertList.tsx` | Card view на `< md` |
| `pages/DataImport.tsx` | Scrollable tabs, larger touch targets |

---

## 6. Что НЕ входит

- PWA / Service Worker / offline mode -- не нужно (5 организаторов, всегда онлайн)
- Native app -- вне scope, пользователи в Telegram
- Свайп-жесты (кроме опционального закрытия sidebar) -- overkill для admin panel
- Адаптация Landing -- уже сделана
- Login page -- минимальная форма, уже адаптивна
