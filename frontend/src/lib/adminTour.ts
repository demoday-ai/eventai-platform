import { driver, type DriveStep } from "driver.js"
import "driver.js/dist/driver.css"
import "../styles/driver-custom.css"

export const adminTourSteps: DriveStep[] = [
  {
    popover: {
      title: "👋 Добро пожаловать в EventAI!",
      description:
        "Давайте познакомимся с административной панелью. Этот краткий тур покажет основные элементы Dashboard.",
      side: "top",
      align: "center",
    },
  },
  {
    element: "#metric-cards",
    popover: {
      title: "📊 Метрики мероприятия",
      description:
        "Здесь вы видите основные показатели: количество проектов, студентов, экспертов, партнёров и залов.\n\nДанные обновляются автоматически каждые 30 секунд.",
      side: "bottom",
      align: "start",
    },
  },
  {
    element: "#sidebar-nav",
    popover: {
      title: "🧭 Навигация",
      description:
        "Все разделы доступны в боковом меню:\n\n• Подготовка: Dashboard, Мероприятие, Импорт, Теги, Проекты\n• Распределение: Кластеризация, Эксперты, Расписание\n• Коммуникация: Рассылки, Авто-напоминания\n• Аналитика и Администрирование\n\nКликните на любой раздел чтобы перейти.",
      side: "right",
      align: "start",
    },
  },
  {
    popover: {
      title: "✅ Готово!",
      description:
        "Типичный workflow:\n\n1. Импорт данных (проекты, студенты, эксперты)\n2. Кластеризация проектов по залам\n3. Matching экспертов к залам\n4. Генерация расписания\n5. Рассылки участникам\n\nНачните с раздела \"Импорт данных\" в меню слева. Удачи! 🚀",
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
