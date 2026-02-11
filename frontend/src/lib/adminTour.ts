import { driver, type DriveStep } from "driver.js"
import "driver.js/dist/driver.css"
import "../styles/driver-custom.css"

interface TourStep extends DriveStep {
  route?: string // Add route metadata
}

export const adminTourSteps: TourStep[] = [
  {
    route: "/dashboard",
    popover: {
      title: "👋 Добро пожаловать в EventAI!",
      description:
        "Давайте познакомимся с административной панелью. Этот тур займет ~3 минуты и покажет все ключевые функции.",
      side: "top",
      align: "center",
    },
  },
  {
    route: "/dashboard",
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
    route: "/dashboard",
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
    route: "/import",
    popover: {
      title: "📥 Импорт данных",
      description:
        "Сейчас перейдем на страницу импорта данных.\n\nНажмите 'Далее' чтобы продолжить.",
      side: "top",
      align: "center",
    },
  },
  {
    route: "/import",
    element: "main",
    popover: {
      title: "📥 Импорт данных",
      description:
        "Здесь загружайте:\n• Мероприятие (название, даты)\n• Проекты (Excel/CSV)\n• Студентов и партнёров\n• Экспертов с тегами\n\nПоддерживаются форматы: .xlsx, .csv, .json",
      side: "top",
      align: "start",
    },
  },
  {
    route: "/clustering",
    popover: {
      title: "🎯 Кластеризация проектов",
      description: "Переходим к кластеризации проектов.\n\nНажмите 'Далее'.",
      side: "top",
      align: "center",
    },
  },
  {
    route: "/clustering",
    element: "main",
    popover: {
      title: "🎯 Кластеризация проектов",
      description:
        "AI автоматически распределяет проекты по тематическим залам:\n• Анализирует теги и описания\n• Предлагает темы залов\n• Обеспечивает баланс (±5 проектов)\n\nМожно запустить заново с фидбэком.",
      side: "top",
      align: "start",
    },
  },
  {
    route: "/experts",
    popover: {
      title: "👥 Эксперты",
      description: "Переходим к управлению экспертами.\n\nНажмите 'Далее'.",
      side: "top",
      align: "center",
    },
  },
  {
    route: "/experts",
    element: "main",
    popover: {
      title: "👥 Эксперты",
      description:
        "Управление экспертами:\n• Просмотр списка с тегами\n• Добавление новых экспертов\n• Экспорт в Excel\n\nТеги используются для matching с залами.",
      side: "top",
      align: "start",
    },
  },
  {
    route: "/schedule",
    popover: {
      title: "📅 Расписание",
      description: "Переходим к генерации расписания.\n\nНажмите 'Далее'.",
      side: "top",
      align: "center",
    },
  },
  {
    route: "/schedule",
    element: "main",
    popover: {
      title: "📅 Расписание",
      description:
        "Генерация и управление расписанием:\n• Автоматическое распределение слотов\n• Редактирование времени презентаций\n• Рассылка напоминаний студентам\n\nАвтоматические напоминания за день и за 30 мин.",
      side: "top",
      align: "start",
    },
  },
  {
    route: "/messaging",
    popover: {
      title: "📨 Рассылки",
      description: "Переходим к разделу рассылок.\n\nНажмите 'Далее'.",
      side: "top",
      align: "center",
    },
  },
  {
    route: "/messaging",
    element: "main",
    popover: {
      title: "📨 Рассылки",
      description:
        "Отправка сообщений через Telegram бота:\n• Выбор сегмента (все/студенты/партнёры)\n• Фильтры по тегам и активности\n• Предпросмотр перед отправкой\n\nРабота через очередь с повторами при ошибках.",
      side: "top",
      align: "start",
    },
  },
  {
    route: "/dashboard",
    popover: {
      title: "✅ Обучение завершено!",
      description:
        "Теперь вы знаете все основные функции админки.\n\nТипичный workflow:\n1. Импорт → 2. Кластеризация → 3. Matching → 4. Расписание → 5. Рассылки\n\nМожете начать с импорта данных. Удачи! 🚀",
      side: "top",
      align: "center",
    },
  },
]

let globalNavigate: ((path: string) => void) | null = null

export function setTourNavigate(navigate: (path: string) => void) {
  globalNavigate = navigate
}

export function startAdminTour() {
  const driverObj = driver({
    showProgress: true,
    steps: adminTourSteps,
    nextBtnText: "Далее →",
    prevBtnText: "← Назад",
    doneBtnText: "Завершить",
    progressText: "{{current}} из {{total}}",
    popoverClass: "driver-popover-custom",
    onNextClick: (_element, _step, options) => {
      const currentStepIndex = options.state.activeIndex ?? 0
      const nextStepIndex = currentStepIndex + 1
      const nextStep = adminTourSteps[nextStepIndex] as TourStep | undefined

      if (nextStep?.route && globalNavigate) {
        const currentPath = window.location.pathname
        if (currentPath !== nextStep.route) {
          // Navigate to the new page
          globalNavigate(nextStep.route)
          // Wait for navigation and re-render
          setTimeout(() => {
            driverObj.moveNext()
          }, 300)
          return
        }
      }
      driverObj.moveNext()
    },
    onPrevClick: (_element, _step, options) => {
      const currentStepIndex = options.state.activeIndex ?? 0
      const prevStepIndex = currentStepIndex - 1
      const prevStep = adminTourSteps[prevStepIndex] as TourStep | undefined

      if (prevStep?.route && globalNavigate) {
        const currentPath = window.location.pathname
        if (currentPath !== prevStep.route) {
          // Navigate to the previous page
          globalNavigate(prevStep.route)
          // Wait for navigation and re-render
          setTimeout(() => {
            driverObj.movePrevious()
          }, 300)
          return
        }
      }
      driverObj.movePrevious()
    },
    onDestroyStarted: () => {
      localStorage.setItem("admin_tour_completed", "true")
      // Return to dashboard when tour ends
      if (globalNavigate) {
        globalNavigate("/dashboard")
      }
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
