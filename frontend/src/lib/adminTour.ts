import { driver, type DriveStep } from "driver.js"
import "driver.js/dist/driver.css"
import "../styles/driver-custom.css"
import { markTourCompleted as apiMarkTourCompleted } from "./api-client"

interface TourStep extends DriveStep {
  route?: string // Add route metadata
}

export const adminTourSteps: TourStep[] = [
  {
    route: "/dashboard",
    popover: {
      title: "👋 Добро пожаловать в EventAI!",
      description:
        "Это интерактивный тур по всем функциям административной панели. Мы автоматически переведем вас между разделами — просто следуйте указаниям.",
      side: "top",
      align: "center",
    },
  },
  {
    route: "/dashboard",
    element: "#metric-cards",
    popover: {
      title: "📊 Метрики в реальном времени",
      description:
        "Актуальная статистика мероприятия:\n\n• Проекты, студенты, эксперты, партнёры, залы\n• Автообновление каждые 30 секунд\n• Детализация по статусам (подтверждено/ожидание)",
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
        "В боковом меню — все разделы админки:\n\n🔧 Подготовка: Dashboard, Мероприятие, Импорт, Теги, Проекты\n🎯 Распределение: Кластеризация, Эксперты, Расписание\n📢 Коммуникация: Рассылки, Авто-напоминания\n📊 Аналитика: Аудитория бота\n⚙️ Администрирование: Настройки, Журнал",
      side: "right",
      align: "start",
    },
  },
  {
    route: "/import",
    element: "main",
    popover: {
      title: "📥 Импорт данных",
      description:
        "Первый шаг — загрузка данных:\n\n• Мероприятие: название, даты, описание\n• Проекты: массовая загрузка из Excel/CSV\n• Студенты и партнёры: списки участников\n• Эксперты: с тегами для автоматического matching\n\nПоддержка: .xlsx, .csv, .json",
      side: "top",
      align: "start",
    },
  },
  {
    route: "/clustering",
    element: "main",
    popover: {
      title: "🎯 AI Кластеризация",
      description:
        "Умное распределение проектов по тематическим залам:\n\n✨ AI анализирует теги и описания\n🏢 Предлагает названия залов\n⚖️ Балансирует нагрузку (±5 проектов)\n🔄 Можно запустить заново с вашим фидбэком\n\nЭкономит часы ручной работы!",
      side: "top",
      align: "start",
    },
  },
  {
    route: "/experts",
    element: "main",
    popover: {
      title: "👥 База экспертов",
      description:
        "Управление приглашенными экспертами:\n\n• 📋 Просмотр списка с тегами экспертизы\n• ➕ Добавление вручную или импорт\n• 📊 Экспорт в Excel для отчетов\n• 🏷️ Теги для автоматического matching",
      side: "top",
      align: "start",
    },
  },
  {
    route: "/schedule",
    element: "main",
    popover: {
      title: "📅 Генерация расписания",
      description:
        "Автоматическое создание расписания Demo Day:\n\n⏱️ Распределение слотов по залам\n✏️ Ручное редактирование времени\n📧 Рассылка расписания студентам\n🔔 Авто-напоминания за день и за 30 минут до выступления",
      side: "top",
      align: "start",
    },
  },
  {
    route: "/messaging",
    element: "main",
    popover: {
      title: "📨 Массовые рассылки",
      description:
        "Отправка сообщений через Telegram бота:\n\n👥 Выбор аудитории: все / студенты / партнёры\n🏷️ Фильтры по тегам и активности\n👁️ Предпросмотр перед отправкой\n♻️ Автоповторы при ошибках доставки",
      side: "top",
      align: "start",
    },
  },
  {
    route: "/guests",
    element: "main",
    popover: {
      title: "👤 Аудитория бота",
      description:
        "Статистика пользователей Telegram-бота:\n\n📊 Количество по ролям и подтипам\n📝 Профилирование гостей\n📈 Динамика активности\n\nПомогает отслеживать вовлеченность участников.",
      side: "top",
      align: "start",
    },
  },
  {
    route: "/settings",
    element: "main",
    popover: {
      title: "⚙️ Настройки системы",
      description:
        "Управление конфигурацией:\n\n👥 Организаторы: добавление/удаление\n🤖 LLM модели и API ключи\n🏷️ Управление тегами\n🔒 Безопасность: ролевой доступ",
      side: "top",
      align: "start",
    },
  },
  {
    route: "/audit-log",
    element: "main",
    popover: {
      title: "📋 Журнал действий",
      description:
        "Полная история операций в админке:\n\n🕐 Все действия организаторов с меткой времени\n👤 Кто и что делал\n📝 Детали изменений\n\nНезаменим для аудита и отладки.",
      side: "top",
      align: "start",
    },
  },
  {
    route: "/dashboard",
    popover: {
      title: "🎉 Готово!",
      description:
        "Вы прошли полный тур по админке EventAI!\n\n📋 Типичный workflow:\n1️⃣ Импорт данных\n2️⃣ AI кластеризация проектов\n3️⃣ Matching экспертов\n4️⃣ Генерация расписания\n5️⃣ Рассылки участникам\n\nМожете начать работу. Успехов! 🚀",
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
    animate: true,
    overlayOpacity: 0.7,
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
      // Mark as completed via API
      apiMarkTourCompleted().catch((err) => {
        console.error("Failed to mark tour as completed:", err)
      })
      // Return to dashboard when tour ends
      if (globalNavigate) {
        globalNavigate("/dashboard")
      }
      driverObj.destroy()
    },
  })

  driverObj.drive()
}

// Note: These functions are now just for compatibility
// Real status comes from backend via getTourStatus()
export function shouldShowTourPrompt(): boolean {
  // This is now checked via API in Dashboard component
  return false
}

export function shouldShowTour(): boolean {
  // This is now checked via API
  return false
}

export function markTourPrompted() {
  // This is now handled via API in Dashboard component
}

export function resetTour() {
  // This is now handled via API (resetTourStatus)
}
