import { useEffect, useRef } from "react"
import {
  Sparkles,
  MessageCircle,
  Route,
  Users,
  BarChart3,
  Phone,
  ChevronDown,
  Zap,
  Target,
  Brain,
  ArrowRight,
  Github,
} from "lucide-react"

const BOT_URL = "https://t.me/DemoDayCurator_bot"
const GITHUB_URL = "https://github.com/demoday-ai/demoday-core"

/* ---------- animated gradient blob ---------- */
function GradientBlob({ className }: { className?: string }) {
  return (
    <div
      className={`absolute rounded-full blur-3xl opacity-20 animate-blob ${className ?? ""}`}
    />
  )
}

/* ---------- feature card ---------- */
function FeatureCard({
  icon: Icon,
  title,
  description,
  delay,
}: {
  icon: React.ElementType
  title: string
  description: string
  delay: number
}) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.classList.add("animate-fade-in-up")
          observer.unobserve(el)
        }
      },
      { threshold: 0.15 }
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  return (
    <div
      ref={ref}
      className="opacity-0 group relative overflow-hidden rounded-2xl border border-white/10 bg-white/5 backdrop-blur-md p-6 transition-all duration-300 hover:border-indigo-400/30 hover:bg-white/10 hover:shadow-lg hover:shadow-indigo-500/5 hover:-translate-y-1"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-lg shadow-indigo-500/30">
        <Icon className="h-6 w-6" />
      </div>
      <h3 className="mb-2 text-lg font-semibold text-white">{title}</h3>
      <p className="text-sm leading-relaxed text-slate-400">{description}</p>
    </div>
  )
}

/* ---------- step ---------- */
function Step({
  number,
  title,
  description,
}: {
  number: number
  title: string
  description: string
}) {
  return (
    <div className="flex gap-4">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 text-sm font-bold text-white shadow-lg shadow-indigo-500/30">
        {number}
      </div>
      <div>
        <h4 className="font-semibold text-white">{title}</h4>
        <p className="mt-1 text-sm text-slate-400">{description}</p>
      </div>
    </div>
  )
}

/* ---------- stat ---------- */
function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div className="text-center">
      <div className="text-3xl font-bold bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent md:text-4xl">
        {value}
      </div>
      <div className="mt-1 text-xs text-slate-400 md:text-sm">{label}</div>
    </div>
  )
}

/* ---------- team member ---------- */
function TeamMember({
  name,
  role,
  emoji,
}: {
  name: string
  role: string
  emoji: string
}) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 p-4 backdrop-blur-md">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-slate-700 to-slate-800 text-2xl">
        {emoji}
      </div>
      <div>
        <div className="font-medium text-white">{name}</div>
        <div className="text-xs text-slate-400">{role}</div>
      </div>
    </div>
  )
}

/* ========== LANDING ========== */
export function Landing() {
  return (
    <div className="min-h-screen bg-slate-950 text-white overflow-hidden">
      {/* ---- NAV ---- */}
      <nav className="fixed top-0 z-50 w-full border-b border-white/5 bg-slate-950/80 backdrop-blur-lg">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-indigo-400" />
            <span className="text-lg font-bold tracking-tight">
              Demo Day <span className="text-indigo-400">AI</span>
            </span>
          </div>
          <div className="hidden items-center gap-6 text-sm text-slate-400 md:flex">
            <a href="#features" className="transition hover:text-white">
              Возможности
            </a>
            <a href="#how" className="transition hover:text-white">
              Как это работает
            </a>
            <a href="#team" className="transition hover:text-white">
              Команда
            </a>
          </div>
          <a
            href={BOT_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="group flex items-center gap-2 rounded-full bg-gradient-to-r from-indigo-500 to-violet-600 px-5 py-2 text-sm font-medium text-white shadow-lg shadow-indigo-500/30 transition-all hover:shadow-indigo-500/50 hover:scale-105"
          >
            <MessageCircle className="h-4 w-4" />
            Открыть бота
          </a>
        </div>
      </nav>

      {/* ---- HERO ---- */}
      <section className="relative flex min-h-screen flex-col items-center justify-center px-6 pt-20">
        {/* Blobs */}
        <GradientBlob className="left-1/4 top-1/4 h-96 w-96 bg-indigo-600 animation-delay-0" />
        <GradientBlob className="right-1/4 top-1/3 h-80 w-80 bg-violet-600 animation-delay-2000" />
        <GradientBlob className="bottom-1/4 left-1/3 h-72 w-72 bg-blue-600 animation-delay-4000" />

        {/* Grid pattern */}
        <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(99,102,241,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(99,102,241,0.03)_1px,transparent_1px)] bg-[size:64px_64px]" />

        <div className="relative z-10 mx-auto max-w-4xl text-center">
          {/* Badge */}
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-4 py-1.5 text-xs font-medium text-indigo-300">
            <Zap className="h-3.5 w-3.5" />
            AI Talent Camp 2026
          </div>

          {/* Title */}
          <h1 className="text-4xl font-extrabold leading-tight tracking-tight sm:text-5xl md:text-7xl">
            Ваш{" "}
            <span className="bg-gradient-to-r from-indigo-400 via-violet-400 to-purple-400 bg-clip-text text-transparent animate-gradient-x">
              AI-куратор
            </span>
            <br />
            Demo Day
          </h1>

          {/* Subtitle */}
          <p className="mx-auto mt-6 max-w-2xl text-base text-slate-400 sm:text-lg md:text-xl">
            330 проектов. 10 залов. 1 день.{" "}
            <span className="text-white">
              Не пропустите то, что важно именно вам.
            </span>{" "}
            AI-бот составит персональную программу за 2 минуты.
          </p>

          {/* CTA */}
          <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <a
              href={BOT_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="group flex items-center gap-2 rounded-full bg-gradient-to-r from-indigo-500 to-violet-600 px-8 py-3.5 text-base font-semibold text-white shadow-xl shadow-indigo-500/30 transition-all hover:shadow-indigo-500/50 hover:scale-105"
            >
              <MessageCircle className="h-5 w-5" />
              Попробовать в Telegram
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
            </a>
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-6 py-3.5 text-sm font-medium text-slate-300 backdrop-blur transition-all hover:border-white/20 hover:text-white"
            >
              <Github className="h-5 w-5" />
              GitHub
            </a>
          </div>

          {/* Stats */}
          <div className="mx-auto mt-16 grid max-w-lg grid-cols-3 gap-8">
            <Stat value="330" label="проектов" />
            <Stat value="10" label="залов" />
            <Stat value="<2 мин" label="на профиль" />
          </div>
        </div>

        {/* Scroll hint */}
        <div className="absolute bottom-8 flex animate-bounce flex-col items-center text-slate-500">
          <ChevronDown className="h-5 w-5" />
        </div>
      </section>

      {/* ---- PROBLEM ---- */}
      <section className="relative border-t border-white/5 bg-slate-950 py-24 px-6">
        <div className="mx-auto max-w-4xl text-center">
          <h2 className="text-2xl font-bold text-white sm:text-3xl">
            Проблема
          </h2>
          <p className="mx-auto mt-6 max-w-2xl text-slate-400 leading-relaxed">
            На Demo Day{" "}
            <span className="text-white font-semibold">
              330 проектов идут параллельно в 10 залах
            </span>
            . Гость физически успевает увидеть менее 20% из них. NLP-энтузиаст
            пропускает 68% релевантных докладов. Нет глубокого профилирования,
            нет умных подсказок, нет follow-up после мероприятия.
          </p>
          <div className="mx-auto mt-10 grid max-w-2xl grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-4">
              <div className="text-2xl font-bold text-red-400">&lt;20%</div>
              <div className="mt-1 text-xs text-slate-400">
                проектов увидит гость
              </div>
            </div>
            <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
              <div className="text-2xl font-bold text-amber-400">68%</div>
              <div className="mt-1 text-xs text-slate-400">
                пропущенных по интересам
              </div>
            </div>
            <div className="rounded-xl border border-orange-500/20 bg-orange-500/5 p-4">
              <div className="text-2xl font-bold text-orange-400">0</div>
              <div className="mt-1 text-xs text-slate-400">
                follow-up после DD
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ---- FEATURES ---- */}
      <section
        id="features"
        className="relative border-t border-white/5 py-24 px-6"
      >
        <GradientBlob className="left-0 top-1/2 h-96 w-96 bg-indigo-700 -translate-y-1/2" />

        <div className="relative z-10 mx-auto max-w-6xl">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-white sm:text-3xl">
              Что умеет AI-куратор
            </h2>
            <p className="mx-auto mt-3 max-w-xl text-slate-400">
              Единый бот в Telegram для всех участников Demo Day
            </p>
          </div>

          <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            <FeatureCard
              icon={Target}
              title="Персональная программа"
              description="Расскажите, что вам интересно, и AI соберёт топ проектов с релевантностью в процентах, разбивкой по залам и приоритетами."
              delay={0}
            />
            <FeatureCard
              icon={Brain}
              title="Q&A-помощник"
              description="Получите 3-5 умных вопросов к каждому проекту, заточенных под ваш профиль. Не приходите на доклад без подготовки."
              delay={100}
            />
            <FeatureCard
              icon={BarChart3}
              title="Матрица сравнения"
              description="Сравните 2-5 проектов по вашим критериям в удобной таблице: тема, зал, релевантность, ключевые особенности."
              delay={200}
            />
            <FeatureCard
              icon={Route}
              title="Планирование маршрута"
              description="AI учитывает параллельность залов и поможет спланировать переходы, чтобы вы не пропустили ничего важного."
              delay={300}
            />
            <FeatureCard
              icon={Phone}
              title="Контакт с авторами"
              description="Нажмите одну кнопку — автор получит запрос и решит, поделиться ли контактом. Безопасный обмен с согласия обеих сторон."
              delay={400}
            />
            <FeatureCard
              icon={Users}
              title="5 ролей"
              description="Гость, бизнес-партнёр, эксперт, студент, организатор — каждый получает свой интерфейс и набор функций."
              delay={500}
            />
          </div>
        </div>
      </section>

      {/* ---- HOW IT WORKS ---- */}
      <section
        id="how"
        className="relative border-t border-white/5 py-24 px-6"
      >
        <div className="mx-auto max-w-3xl">
          <h2 className="text-center text-2xl font-bold text-white sm:text-3xl">
            Как это работает
          </h2>

          <div className="mt-14 grid gap-8 sm:grid-cols-2">
            <div className="space-y-8">
              <Step
                number={1}
                title="Откройте бота"
                description="Нажмите кнопку «Открыть бота» или найдите @DemoDayCurator_bot в Telegram."
              />
              <Step
                number={2}
                title="Расскажите о себе"
                description="Выберите роль и опишите свои интересы свободным текстом или кнопками. AI задаст уточняющие вопросы."
              />
              <Step
                number={3}
                title="Получите программу"
                description="AI проанализирует 330 проектов и выдаст персональный топ с рейтингом, описаниями и разбивкой по залам."
              />
            </div>
            <div className="space-y-8">
              <Step
                number={4}
                title="Изучите детали"
                description="Откройте карточку проекта: полное описание, автор, зал, теги. Попросите AI подготовить вопросы."
              />
              <Step
                number={5}
                title="Свяжитесь с автором"
                description="Нажмите «Связаться с автором» — безопасный обмен контактами с согласия обеих сторон."
              />
              <Step
                number={6}
                title="Общайтесь с AI"
                description="Задавайте любые вопросы: «сравни проекты #1 и #3», «какой зал ближе», «покажи мой профиль»."
              />
            </div>
          </div>
        </div>
      </section>

      {/* ---- DEMO / MOCKUP ---- */}
      <section className="relative border-t border-white/5 py-24 px-6">
        <div className="mx-auto max-w-4xl">
          <h2 className="text-center text-2xl font-bold text-white sm:text-3xl">
            Диалог с AI-куратором
          </h2>
          <p className="mx-auto mt-3 max-w-lg text-center text-slate-400">
            Пример разговора с ботом
          </p>

          {/* Chat mockup */}
          <div className="mx-auto mt-10 max-w-md overflow-hidden rounded-2xl border border-white/10 bg-slate-900">
            {/* Header */}
            <div className="flex items-center gap-3 border-b border-white/10 bg-slate-800/50 px-5 py-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-violet-600">
                <Sparkles className="h-4 w-4 text-white" />
              </div>
              <div>
                <div className="text-sm font-medium text-white">
                  Demo Day AI Куратор
                </div>
                <div className="text-xs text-green-400">online</div>
              </div>
            </div>

            {/* Messages */}
            <div className="space-y-3 p-5">
              <ChatBubble
                side="left"
                text="Расскажите, что вас интересует на Demo Day? Напишите свободным текстом или выберите темы кнопками."
              />
              <ChatBubble
                side="right"
                text="Я HR-директор, ищу проекты по автоматизации найма и AI в HR"
              />
              <ChatBubble
                side="left"
                text="Отлично! Я нашёл 8 проектов, подходящих под ваш запрос. Вот топ-3:"
              />
              <ChatBubble
                side="left"
                text={
                  "1. AI Recruiter Assistant (94%)\n📍 Зал 2 · HR, Agents\n\n2. Resume Screening Engine (87%)\n📍 Зал 5 · NLP, HR\n\n3. Interview Copilot (82%)\n📍 Зал 2 · LLM, Agents"
                }
              />
              <ChatBubble
                side="right"
                text="Подготовь вопросы к проекту #1"
              />
              <ChatBubble
                side="left"
                text={
                  "Вопросы к AI Recruiter Assistant:\n\n1. Какой процент ложноположительных отсевов на этапе скрининга?\n2. Как система учитывает soft skills?\n3. Какие ATS поддерживаете?"
                }
              />
            </div>
          </div>
        </div>
      </section>

      {/* ---- TEAM ---- */}
      <section
        id="team"
        className="relative border-t border-white/5 py-24 px-6"
      >
        <div className="mx-auto max-w-3xl">
          <h2 className="text-center text-2xl font-bold text-white sm:text-3xl">
            Команда ЯСНОПОНЯТНО
          </h2>
          <p className="mx-auto mt-3 max-w-lg text-center text-slate-400">
            AI Talent Camp 2026 &middot; Проект #10
          </p>

          <div className="mt-10 grid gap-4 sm:grid-cols-2">
            <TeamMember
              name="Дмитрий Горбунов"
              role="Тимлид, продукт, UX/UI"
              emoji="🚀"
            />
            <TeamMember
              name="Анастасия Гапеева"
              role="UX/UI, фронтенд"
              emoji="🎨"
            />
            <TeamMember
              name="Иван Александров"
              role="Разработка, бизнес-логика"
              emoji="🛠"
            />
            <TeamMember
              name="Claude"
              role="AI-ассистент команды"
              emoji="🤖"
            />
          </div>
        </div>
      </section>

      {/* ---- CTA ---- */}
      <section className="relative border-t border-white/5 py-24 px-6">
        <GradientBlob className="left-1/2 top-1/2 h-80 w-80 -translate-x-1/2 -translate-y-1/2 bg-indigo-600" />

        <div className="relative z-10 mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold text-white sm:text-4xl">
            Готовы к Demo Day?
          </h2>
          <p className="mx-auto mt-4 max-w-md text-slate-400">
            Откройте бота в Telegram и получите персональную программу за 2
            минуты. Бесплатно.
          </p>
          <a
            href={BOT_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="group mt-8 inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-indigo-500 to-violet-600 px-10 py-4 text-lg font-semibold text-white shadow-2xl shadow-indigo-500/30 transition-all hover:shadow-indigo-500/50 hover:scale-105"
          >
            <MessageCircle className="h-5 w-5" />
            Открыть бота
            <ArrowRight className="h-5 w-5 transition-transform group-hover:translate-x-1" />
          </a>
        </div>
      </section>

      {/* ---- FOOTER ---- */}
      <footer className="border-t border-white/5 py-8 px-6">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 sm:flex-row">
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Sparkles className="h-4 w-4" />
            Demo Day AI &copy; 2026
          </div>
          <div className="flex items-center gap-6 text-sm text-slate-500">
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 transition hover:text-white"
            >
              <Github className="h-4 w-4" />
              GitHub
            </a>
            <a
              href={BOT_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 transition hover:text-white"
            >
              <MessageCircle className="h-4 w-4" />
              Telegram Bot
            </a>
          </div>
        </div>
      </footer>
    </div>
  )
}

/* ---------- chat bubble ---------- */
function ChatBubble({ side, text }: { side: "left" | "right"; text: string }) {
  const isLeft = side === "left"
  return (
    <div className={`flex ${isLeft ? "justify-start" : "justify-end"}`}>
      <div
        className={`max-w-[80%] whitespace-pre-line rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
          isLeft
            ? "rounded-tl-sm bg-slate-800 text-slate-200"
            : "rounded-tr-sm bg-indigo-600 text-white"
        }`}
      >
        {text}
      </div>
    </div>
  )
}
