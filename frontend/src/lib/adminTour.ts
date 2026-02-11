import { driver, type DriveStep } from "driver.js"
import "driver.js/dist/driver.css"
import "../styles/driver-custom.css"

export const adminTourSteps: DriveStep[] = [
  {
    popover: {
      title: "👋 Добро пожаловать в EventAI!",
      description:
        "Давайте познакомимся с административной панелью. Этот тур займет ~3 минуты и покажет все ключевые функции.",
      side: "top",
      align: "center",
    },
  },
  {
    element: "#metric-cards",
    popover: {
      title: "📊 Метрики мероприятия",
      description:
        "Здесь вы видите основные показатели: количество проектов, студентов, экспертов, партнёров и залов. Обновляются в реальном времени каждые 30 секунд.",
      side: "bottom",
      align: "start",
    },
  },
  {
    element: "#sidebar-nav",
    popover: {
      title: "🧭 Навигация",
      description:
        "Все разделы доступны в боковом меню:\n• Подготовка: Dashboard, Мероприятие, Импорт, Теги, Проекты, Участники\n• Распределение: Кластеризация, Эксперты, Расписание\n• Коммуникация: Рассылки, Авто-напоминания\n• Аналитика и Администрирование",
      side: "right",
      align: "start",
    },
  },
  {
    popover: {
      title: "📥 Импорт данных",
      description:
        "Следующий шаг: загрузить данные.\n\nНажмите 'Далее' и я покажу, как импортировать проекты, студентов и экспертов.",
      side: "top",
      align: "center",
    },
  },
  {
    element: "[href='/import']",
    popover: {
      title: "📥 Импорт данных",
      description:
        "Здесь загружайте:\n• Мероприятие (название, даты)\n• Проекты (Excel/CSV)\n• Студентов и партнёров\n• Экспертов с тегами\n\nПоддерживаются форматы: .xlsx, .csv, .json",
      side: "right",
      align: "start",
    },
  },
  {
    element: "[href='/clustering']",
    popover: {
      title: "🎯 Кластеризация проектов",
      description:
        "AI автоматически распределяет проекты по тематическим залам:\n• Анализирует теги и описания\n• Предлагает темы залов\n• Обеспечивает баланс (±5 проектов)\n\nМожно запустить заново с фидбэком.",
      side: "right",
      align: "start",
    },
  },
  {
    element: "[href='/experts']",
    popover: {
      title: "👥 Эксперты",
      description:
        "Управление экспертами:\n• Просмотр списка с тегами\n• Добавление новых экспертов\n• Экспорт в Excel\n\nТеги используются для matching с залами.",
      side: "right",
      align: "start",
    },
  },
  {
    element: "[href='/expert-matching']",
    popover: {
      title: "🤝 Matching экспертов",
      description:
        "AI подбирает экспертов по залам:\n• Сопоставляет теги экспертов и залов\n• Учитывает capacity (макс. залов на эксперта)\n• Генерирует персональные инвайты\n\nМожно редактировать вручную.",
      side: "right",
      align: "start",
    },
  },
  {
    element: "[href='/schedule']",
    popover: {
      title: "📅 Расписание",
      description:
        "Генерация и управление расписанием:\n• Автоматическое распределение слотов\n• Редактирование времени презентаций\n• Рассылка напоминаний студентам\n\nАвтоматические напомилки за день и за 30 мин.",
      side: "right",
      align: "start",
    },
  },
  {
    element: "[href='/messaging']",
    popover: {
      title: "📨 Рассылки",
      description:
        "Отправка сообщений через Telegram бота:\n• Выбор сегмента (все/студенты/партнёры)\n• Фильтры по тегам и активности\n• Предпросмотр перед отправкой\n\nРабота через очередь с повторами при ошибках.",
      side: "right",
      align: "start",
    },
  },
  {
    element: "[href='/settings']",
    popover: {
      title: "⚙️ Настройки",
      description:
        "Управление:\n• Организаторами (добавление/удаление)\n• LLM моделями и API ключами\n• Тегами (добавление, нормализация)\n\nБезопасность: только владелец может удалять себя.",
      side: "right",
      align: "start",
    },
  },
  {
    popover: {
      title: "✅ Обучение завершено!",
      description:
        "Теперь вы знаете все основные функции админки.\n\nТипичный workflow:\n1. Импорт → 2. Кластеризация → 3. Matching → 4. Расписание → 5. Рассылки\n\nМожете начать с импорта данных. Удачи! 🚀",
      side: "top",
      align: "center",
    },
  },
]

export function startAdminTour() {
  const driverObj = driver({
    showProgress: true,
    steps: adminTourSteps,
    nextBtnText: "Далее →",
    prevBtnText: "← Назад",
    doneBtnText: "Завершить",
    progressText: "{{current}} из {{total}}",
    popoverClass: "driver-popover-custom",
    onDestroyStarted: () => {
      localStorage.setItem("admin_tour_completed", "true")
      driverObj.destroy()
    },
  })

  driverObj.drive()
}

export function shouldShowTourPrompt(): boolean {
  return !localStorage.getItem("admin_tour_prompted")
}

export function shouldShowTour(): boolean {
  return !localStorage.getItem("admin_tour_completed")
}

export function markTourPrompted() {
  localStorage.setItem("admin_tour_prompted", "true")
}

export function resetTour() {
  localStorage.removeItem("admin_tour_completed")
  localStorage.removeItem("admin_tour_prompted")
}
