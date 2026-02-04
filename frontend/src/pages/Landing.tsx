import { useCallback, useEffect, useRef, useState } from "react"
import {
  Sparkles,
  MessageCircle,
  MapPin,
  Users,
  BarChart3,
  Phone,
  ChevronDown,
  Target,
  Brain,
  ArrowRight,
  ArrowUpRight,
  Github,
  Sun,
  Moon,
  Send,
  Bot,
  Hash,
} from "lucide-react"

const BOT_URL = "https://t.me/DemoDayCurator_bot"
const GITHUB_URL = "https://github.com/demoday-ai/demoday-core"

/* ============================================================
   Theme
   ============================================================ */

function useTheme() {
  const [dark, setDark] = useState(() => {
    if (typeof window === "undefined") return false
    const stored = localStorage.getItem("dd-theme")
    if (stored) return stored === "dark"
    return window.matchMedia("(prefers-color-scheme: dark)").matches
  })

  const toggle = useCallback(() => {
    setDark((prev) => {
      const next = !prev
      localStorage.setItem("dd-theme", next ? "dark" : "light")
      return next
    })
  }, [])

  useEffect(() => {
    const root = document.documentElement
    root.classList.add("theme-transition")
    if (dark) {
      root.classList.add("dark")
    } else {
      root.classList.remove("dark")
    }
    const timer = setTimeout(() => root.classList.remove("theme-transition"), 350)
    return () => clearTimeout(timer)
  }, [dark])

  return { dark, toggle }
}

/* ============================================================
   Scroll-triggered reveal
   ============================================================ */

function useReveal<T extends HTMLElement>(threshold = 0.12) {
  const ref = useRef<T>(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const obs = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          el.classList.add("is-visible")
          obs.unobserve(el)
        }
      },
      { threshold }
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [threshold])
  return ref
}

function Reveal({
  children,
  className = "",
  as: Tag = "div",
  delay = 0,
}: {
  children: React.ReactNode
  className?: string
  as?: React.ElementType
  delay?: number
}) {
  const ref = useReveal<HTMLDivElement>()
  return (
    <Tag
      ref={ref}
      className={`opacity-0 translate-y-6 transition-all duration-700 ease-[cubic-bezier(0.22,1,0.36,1)] [&.is-visible]:opacity-100 [&.is-visible]:translate-y-0 ${className}`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {children}
    </Tag>
  )
}

/* ============================================================
   Components
   ============================================================ */

function SectionTag({ children }: { children: React.ReactNode }) {
  return (
    <span
      className="font-display inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[11px] font-medium uppercase tracking-widest"
      style={{
        background: "var(--ld-accent-soft)",
        color: "var(--ld-accent-text)",
        border: "1px solid var(--ld-border-subtle)",
      }}
    >
      <Hash className="h-3 w-3" />
      {children}
    </span>
  )
}

function FeatureCard({
  icon: Icon,
  title,
  description,
  index,
}: {
  icon: React.ElementType
  title: string
  description: string
  index: number
}) {
  return (
    <Reveal delay={index * 80}>
      <div
        className="group relative overflow-hidden rounded-xl p-6 transition-all duration-300 hover:-translate-y-1 cursor-default"
        style={{
          background: "var(--ld-surface)",
          border: "1px solid var(--ld-border)",
          boxShadow: "var(--ld-card-shadow)",
        }}
        onMouseEnter={(e) => {
          ;(e.currentTarget as HTMLElement).style.boxShadow = "var(--ld-card-shadow-hover)"
          ;(e.currentTarget as HTMLElement).style.borderColor = "var(--ld-accent)"
        }}
        onMouseLeave={(e) => {
          ;(e.currentTarget as HTMLElement).style.boxShadow = "var(--ld-card-shadow)"
          ;(e.currentTarget as HTMLElement).style.borderColor = "var(--ld-border)"
        }}
      >
        {/* Subtle gradient shine on hover */}
        <div
          className="absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
          style={{
            background: `linear-gradient(135deg, var(--ld-accent-soft), transparent 60%)`,
          }}
        />
        <div className="relative z-10">
          <div
            className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg"
            style={{
              background: "var(--ld-accent-soft)",
              color: "var(--ld-accent)",
            }}
          >
            <Icon className="h-5 w-5" />
          </div>
          <h3
            className="font-display mb-2 text-base font-medium"
            style={{ color: "var(--ld-text)" }}
          >
            {title}
          </h3>
          <p
            className="font-body text-sm leading-relaxed"
            style={{ color: "var(--ld-text-secondary)" }}
          >
            {description}
          </p>
        </div>
      </div>
    </Reveal>
  )
}

function StatBlock({
  value,
  label,
  accent,
  delay,
}: {
  value: string
  label: string
  accent: string
  delay: number
}) {
  return (
    <Reveal delay={delay}>
      <div
        className="rounded-xl p-5 text-center"
        style={{
          background: accent === "ember" ? "var(--ld-ember-soft)"
            : accent === "teal" ? "var(--ld-teal-soft)"
            : "var(--ld-amber-soft)",
          border: "1px solid var(--ld-border-subtle)",
        }}
      >
        <div
          className="font-display text-3xl font-medium"
          style={{
            color: accent === "ember" ? "var(--ld-ember)"
              : accent === "teal" ? "var(--ld-teal)"
              : "var(--ld-amber)",
          }}
        >
          {value}
        </div>
        <div
          className="font-body mt-1 text-xs"
          style={{ color: "var(--ld-text-secondary)" }}
        >
          {label}
        </div>
      </div>
    </Reveal>
  )
}

function StepItem({
  number,
  title,
  description,
  delay,
}: {
  number: number
  title: string
  description: string
  delay: number
}) {
  return (
    <Reveal delay={delay} className="flex gap-4">
      <div
        className="font-display flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-medium"
        style={{
          background: "var(--ld-accent)",
          color: "#fff",
        }}
      >
        {number}
      </div>
      <div>
        <h4
          className="font-display text-sm font-medium"
          style={{ color: "var(--ld-text)" }}
        >
          {title}
        </h4>
        <p
          className="font-body mt-1 text-sm leading-relaxed"
          style={{ color: "var(--ld-text-secondary)" }}
        >
          {description}
        </p>
      </div>
    </Reveal>
  )
}

function TeamMember({
  name,
  role,
  tag,
  delay,
}: {
  name: string
  role: string
  tag: string
  delay: number
}) {
  return (
    <Reveal delay={delay}>
      <div
        className="flex items-center gap-4 rounded-xl p-4 transition-all duration-200"
        style={{
          background: "var(--ld-surface)",
          border: "1px solid var(--ld-border-subtle)",
        }}
      >
        <div
          className="font-display flex h-11 w-11 items-center justify-center rounded-full text-xs font-medium uppercase tracking-wider"
          style={{
            background: "var(--ld-accent-soft)",
            color: "var(--ld-accent)",
          }}
        >
          {tag}
        </div>
        <div>
          <div
            className="font-display text-sm font-medium"
            style={{ color: "var(--ld-text)" }}
          >
            {name}
          </div>
          <div
            className="font-body text-xs"
            style={{ color: "var(--ld-text-muted)" }}
          >
            {role}
          </div>
        </div>
      </div>
    </Reveal>
  )
}

function ChatBubble({
  side,
  text,
  delay,
}: {
  side: "bot" | "user"
  text: string
  delay: number
}) {
  const isBot = side === "bot"
  return (
    <Reveal
      delay={delay}
      className={`flex ${isBot ? "justify-start" : "justify-end"}`}
    >
      <div className="flex max-w-[85%] gap-2">
        {isBot && (
          <div
            className="mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full"
            style={{ background: "var(--ld-accent)", color: "#fff" }}
          >
            <Bot className="h-3 w-3" />
          </div>
        )}
        <div
          className="font-body whitespace-pre-line rounded-2xl px-4 py-2.5 text-[13px] leading-relaxed"
          style={
            isBot
              ? {
                  background: "var(--ld-chat-bot)",
                  color: "var(--ld-text)",
                  borderTopLeftRadius: "4px",
                }
              : {
                  background: "var(--ld-chat-user)",
                  color: "var(--ld-chat-user-text)",
                  borderTopRightRadius: "4px",
                }
          }
        >
          {text}
        </div>
      </div>
    </Reveal>
  )
}

/* ============================================================
   LANDING PAGE
   ============================================================ */

export function Landing() {
  const { dark, toggle } = useTheme()

  return (
    <div
      className="font-body relative min-h-screen overflow-hidden"
      style={{ background: "var(--ld-bg)", color: "var(--ld-text)" }}
    >
      {/* ===================== NAV ===================== */}
      <nav
        className="fixed top-0 z-50 w-full backdrop-blur-xl"
        style={{
          background: "var(--ld-nav-bg)",
          borderBottom: "1px solid var(--ld-border-subtle)",
        }}
      >
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3.5">
          {/* Logo */}
          <a
            href="#"
            className="font-display flex items-center gap-2 text-base font-medium tracking-tight"
            style={{ color: "var(--ld-text)" }}
          >
            <div
              className="flex h-7 w-7 items-center justify-center rounded-md"
              style={{ background: "var(--ld-accent)", color: "#fff" }}
            >
              <Sparkles className="h-3.5 w-3.5" />
            </div>
            DD.AI
          </a>

          {/* Nav links */}
          <div
            className="font-display hidden items-center gap-7 text-xs font-medium uppercase tracking-widest md:flex"
            style={{ color: "var(--ld-text-muted)" }}
          >
            <a href="#problem" className="transition-colors hover:opacity-80" style={{ color: "var(--ld-text-secondary)" }}>
              Problem
            </a>
            <a href="#features" className="transition-colors hover:opacity-80" style={{ color: "var(--ld-text-secondary)" }}>
              Features
            </a>
            <a href="#how" className="transition-colors hover:opacity-80" style={{ color: "var(--ld-text-secondary)" }}>
              How
            </a>
            <a href="#team" className="transition-colors hover:opacity-80" style={{ color: "var(--ld-text-secondary)" }}>
              Team
            </a>
          </div>

          {/* Right side */}
          <div className="flex items-center gap-3">
            <button
              onClick={toggle}
              className="flex h-8 w-8 items-center justify-center rounded-lg transition-all duration-200 hover:scale-110"
              style={{
                background: "var(--ld-surface)",
                border: "1px solid var(--ld-border)",
                color: "var(--ld-text-secondary)",
              }}
              aria-label="Toggle theme"
            >
              {dark ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
            </button>
            <a
              href={BOT_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="font-display hidden items-center gap-2 rounded-lg px-4 py-2 text-xs font-medium transition-all duration-200 hover:scale-[1.03] sm:flex"
              style={{
                background: "var(--ld-accent)",
                color: "#fff",
              }}
            >
              <MessageCircle className="h-3.5 w-3.5" />
              Open Bot
            </a>
          </div>
        </div>
      </nav>

      {/* ===================== HERO ===================== */}
      <section className="noise-overlay dot-grid relative flex min-h-screen flex-col items-center justify-center px-6 pt-24 pb-16">
        {/* Background gradient orbs */}
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <div
            className="animate-hero-gradient absolute -left-32 -top-32 h-[600px] w-[600px] rounded-full opacity-30 blur-[120px]"
            style={{ background: "var(--ld-hero-gradient-1)" }}
          />
          <div
            className="animate-hero-gradient absolute -right-20 top-1/4 h-[500px] w-[500px] rounded-full opacity-20 blur-[100px]"
            style={{ background: "var(--ld-hero-gradient-2)", animationDelay: "-7s" }}
          />
          <div
            className="animate-hero-gradient absolute bottom-0 left-1/3 h-[400px] w-[400px] rounded-full opacity-15 blur-[80px]"
            style={{ background: "var(--ld-hero-gradient-3)", animationDelay: "-14s" }}
          />
        </div>

        <div className="relative z-10 mx-auto max-w-4xl text-center">
          {/* Badge */}
          <Reveal>
            <div className="mb-8 inline-flex items-center gap-2">
              <SectionTag>AI Talent Camp 2026</SectionTag>
            </div>
          </Reveal>

          {/* Title */}
          <Reveal delay={100}>
            <h1 className="font-display text-4xl font-medium leading-[1.1] tracking-tight sm:text-5xl md:text-[4.5rem]">
              <span style={{ color: "var(--ld-text)" }}>
                {"Ваш "}
              </span>
              <span
                className="animate-shimmer"
                style={{
                  backgroundImage: `linear-gradient(90deg, var(--ld-hero-gradient-1), var(--ld-hero-gradient-2), var(--ld-hero-gradient-3), var(--ld-hero-gradient-1))`,
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  backgroundClip: "text",
                }}
              >
                AI-куратор
              </span>
              <br />
              <span style={{ color: "var(--ld-text)" }}>Demo Day</span>
            </h1>
          </Reveal>

          {/* Subtitle */}
          <Reveal delay={200}>
            <p
              className="font-body mx-auto mt-6 max-w-xl text-base leading-relaxed sm:text-lg"
              style={{ color: "var(--ld-text-secondary)" }}
            >
              330 проектов. 10 залов. 1 день.{" "}
              <strong style={{ color: "var(--ld-text)" }}>
                Не пропустите то, что важно именно вам.
              </strong>{" "}
              AI-бот составит персональную программу за 2&nbsp;минуты.
            </p>
          </Reveal>

          {/* CTA */}
          <Reveal delay={300}>
            <div className="mt-10 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
              <a
                href={BOT_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="font-display group flex items-center gap-2 rounded-xl px-7 py-3.5 text-sm font-medium transition-all duration-200 hover:scale-[1.03]"
                style={{
                  background: "var(--ld-accent)",
                  color: "#fff",
                  boxShadow: `0 4px 20px var(--ld-accent-glow)`,
                }}
              >
                <MessageCircle className="h-4 w-4" />
                Попробовать в Telegram
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </a>
              <a
                href={GITHUB_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="font-display flex items-center gap-2 rounded-xl px-6 py-3.5 text-sm font-medium transition-all duration-200 hover:scale-[1.03]"
                style={{
                  background: "var(--ld-surface)",
                  color: "var(--ld-text-secondary)",
                  border: "1px solid var(--ld-border)",
                }}
              >
                <Github className="h-4 w-4" />
                GitHub
                <ArrowUpRight className="h-3.5 w-3.5 opacity-50" />
              </a>
            </div>
          </Reveal>

          {/* Stats row */}
          <Reveal delay={400}>
            <div
              className="mx-auto mt-16 flex max-w-md items-center justify-center gap-8 rounded-xl px-8 py-4"
              style={{
                background: "var(--ld-surface)",
                border: "1px solid var(--ld-border-subtle)",
                boxShadow: "var(--ld-card-shadow)",
              }}
            >
              {[
                { v: "330", l: "проектов" },
                { v: "10", l: "залов" },
                { v: "<2'", l: "на профиль" },
                { v: "5", l: "ролей" },
              ].map((s, i) => (
                <div key={i} className="text-center">
                  <div
                    className="font-display text-xl font-medium sm:text-2xl"
                    style={{ color: "var(--ld-accent)" }}
                  >
                    {s.v}
                  </div>
                  <div
                    className="font-body text-[10px] uppercase tracking-wider"
                    style={{ color: "var(--ld-text-muted)" }}
                  >
                    {s.l}
                  </div>
                </div>
              ))}
            </div>
          </Reveal>
        </div>

        {/* Scroll hint */}
        <Reveal delay={600} className="absolute bottom-6">
          <div className="flex animate-float flex-col items-center">
            <ChevronDown className="h-5 w-5" style={{ color: "var(--ld-text-muted)" }} />
          </div>
        </Reveal>
      </section>

      {/* ===================== PROBLEM ===================== */}
      <section
        id="problem"
        className="relative py-24 px-6"
        style={{ borderTop: "1px solid var(--ld-border-subtle)" }}
      >
        <div className="mx-auto max-w-4xl text-center">
          <Reveal>
            <SectionTag>Проблема</SectionTag>
          </Reveal>
          <Reveal delay={100}>
            <h2
              className="font-display mt-6 text-2xl font-medium tracking-tight sm:text-3xl"
              style={{ color: "var(--ld-text)" }}
            >
              330 проектов. 10 залов.{" "}
              <span style={{ color: "var(--ld-ember)" }}>Кого вы пропустите?</span>
            </h2>
          </Reveal>
          <Reveal delay={150}>
            <p
              className="font-body mx-auto mt-4 max-w-2xl leading-relaxed"
              style={{ color: "var(--ld-text-secondary)" }}
            >
              Гость физически успевает увидеть менее 20% проектов.
              NLP-энтузиаст пропускает 68% релевантных докладов из-за параллельности залов.
              Нет умных подсказок, нет follow-up.
            </p>
          </Reveal>

          <div className="mx-auto mt-10 grid max-w-2xl grid-cols-1 gap-4 sm:grid-cols-3">
            <StatBlock value="<20%" label="проектов увидит гость" accent="ember" delay={200} />
            <StatBlock value="68%" label="пропущенных по интересам" accent="amber" delay={280} />
            <StatBlock value="0" label="follow-up после DD" accent="teal" delay={360} />
          </div>
        </div>
      </section>

      {/* ===================== FEATURES ===================== */}
      <section
        id="features"
        className="relative py-24 px-6"
        style={{
          borderTop: "1px solid var(--ld-border-subtle)",
          background: "var(--ld-bg-alt)",
        }}
      >
        <div className="mx-auto max-w-6xl">
          <div className="text-center">
            <Reveal>
              <SectionTag>Возможности</SectionTag>
            </Reveal>
            <Reveal delay={100}>
              <h2
                className="font-display mt-6 text-2xl font-medium tracking-tight sm:text-3xl"
                style={{ color: "var(--ld-text)" }}
              >
                Что умеет AI-куратор
              </h2>
            </Reveal>
            <Reveal delay={150}>
              <p
                className="font-body mx-auto mt-3 max-w-lg"
                style={{ color: "var(--ld-text-secondary)" }}
              >
                Единый бот в Telegram для всех участников Demo Day
              </p>
            </Reveal>
          </div>

          <div className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <FeatureCard
              icon={Target}
              title="Персональная программа"
              description="AI соберёт топ проектов с релевантностью в процентах, разбивкой по залам и приоритетами."
              index={0}
            />
            <FeatureCard
              icon={Brain}
              title="Q&A-помощник"
              description="3-5 умных вопросов к каждому проекту, заточенных под ваш профиль и бизнес-задачи."
              index={1}
            />
            <FeatureCard
              icon={BarChart3}
              title="Матрица сравнения"
              description="Сравните 2-5 проектов в таблице: тема, зал, релевантность, ключевые особенности."
              index={2}
            />
            <FeatureCard
              icon={MapPin}
              title="Планирование маршрута"
              description="AI учитывает параллельность залов и спланирует переходы без потерь."
              index={3}
            />
            <FeatureCard
              icon={Phone}
              title="Контакт с авторами"
              description="Одна кнопка — автор решает, делиться ли контактом. Безопасный обмен с согласия обеих сторон."
              index={4}
            />
            <FeatureCard
              icon={Users}
              title="5 ролей"
              description="Гость, партнёр, эксперт, студент, организатор — каждый получает свой интерфейс."
              index={5}
            />
          </div>
        </div>
      </section>

      {/* ===================== CHAT DEMO ===================== */}
      <section
        className="relative py-24 px-6"
        style={{ borderTop: "1px solid var(--ld-border-subtle)" }}
      >
        <div className="mx-auto max-w-4xl">
          <div className="text-center">
            <Reveal>
              <SectionTag>Live Demo</SectionTag>
            </Reveal>
            <Reveal delay={100}>
              <h2
                className="font-display mt-6 text-2xl font-medium tracking-tight sm:text-3xl"
                style={{ color: "var(--ld-text)" }}
              >
                Диалог с куратором
              </h2>
            </Reveal>
          </div>

          {/* Chat */}
          <Reveal delay={150}>
            <div
              className="mx-auto mt-10 max-w-md overflow-hidden rounded-2xl"
              style={{
                background: "var(--ld-surface)",
                border: "1px solid var(--ld-border)",
                boxShadow: "var(--ld-card-shadow-hover)",
              }}
            >
              {/* Chat header */}
              <div
                className="flex items-center gap-3 px-5 py-3.5"
                style={{ borderBottom: "1px solid var(--ld-border-subtle)" }}
              >
                <div className="relative">
                  <div
                    className="flex h-8 w-8 items-center justify-center rounded-full"
                    style={{ background: "var(--ld-accent)", color: "#fff" }}
                  >
                    <Bot className="h-4 w-4" />
                  </div>
                  {/* Online dot */}
                  <div className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2" style={{ background: "#22c55e", borderColor: "var(--ld-surface)" }} />
                </div>
                <div>
                  <div
                    className="font-display text-sm font-medium"
                    style={{ color: "var(--ld-text)" }}
                  >
                    Demo Day AI
                  </div>
                  <div className="font-body text-[10px]" style={{ color: "var(--ld-text-muted)" }}>
                    online
                  </div>
                </div>
              </div>

              {/* Messages */}
              <div className="space-y-3 p-5">
                <ChatBubble
                  side="bot"
                  text="Расскажите, что вас интересует на Demo Day?"
                  delay={300}
                />
                <ChatBubble
                  side="user"
                  text="Я HR-директор, ищу проекты по автоматизации найма и AI в HR"
                  delay={500}
                />
                <ChatBubble
                  side="bot"
                  text={"Нашёл 8 проектов. Ваш топ-3:\n\n1. AI Recruiter Assistant (94%)\n   📍 Зал 2 · HR, Agents\n\n2. Resume Screening Engine (87%)\n   📍 Зал 5 · NLP, HR\n\n3. Interview Copilot (82%)\n   📍 Зал 2 · LLM, Agents"}
                  delay={700}
                />
                <ChatBubble
                  side="user"
                  text="Подготовь вопросы к проекту #1"
                  delay={900}
                />
                <ChatBubble
                  side="bot"
                  text={"Вопросы к AI Recruiter Assistant:\n\n1. Какой % ложноположительных отсевов?\n2. Как система учитывает soft skills?\n3. Какие ATS поддерживаете?"}
                  delay={1100}
                />
              </div>

              {/* Input bar */}
              <div
                className="flex items-center gap-2 px-4 py-3"
                style={{ borderTop: "1px solid var(--ld-border-subtle)" }}
              >
                <div
                  className="font-body flex-1 rounded-lg px-3 py-2 text-xs"
                  style={{
                    background: "var(--ld-bg-alt)",
                    color: "var(--ld-text-muted)",
                  }}
                >
                  Сравни проекты #1 и #3...
                  <span className="animate-cursor ml-0.5 inline-block w-[2px] h-3 align-middle" style={{ background: "var(--ld-accent)" }} />
                </div>
                <div
                  className="flex h-8 w-8 items-center justify-center rounded-lg"
                  style={{ background: "var(--ld-accent)", color: "#fff" }}
                >
                  <Send className="h-3.5 w-3.5" />
                </div>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ===================== HOW IT WORKS ===================== */}
      <section
        id="how"
        className="relative py-24 px-6"
        style={{
          borderTop: "1px solid var(--ld-border-subtle)",
          background: "var(--ld-bg-alt)",
        }}
      >
        <div className="mx-auto max-w-3xl">
          <div className="text-center">
            <Reveal>
              <SectionTag>Как это работает</SectionTag>
            </Reveal>
            <Reveal delay={100}>
              <h2
                className="font-display mt-6 text-2xl font-medium tracking-tight sm:text-3xl"
                style={{ color: "var(--ld-text)" }}
              >
                6 шагов к идеальному Demo Day
              </h2>
            </Reveal>
          </div>

          <div className="mt-14 grid gap-8 sm:grid-cols-2">
            <div className="space-y-8">
              <StepItem
                number={1}
                title="Откройте бота"
                description="@DemoDayCurator_bot в Telegram или кнопка на этой странице."
                delay={0}
              />
              <StepItem
                number={2}
                title="Расскажите о себе"
                description="Роль, интересы текстом или кнопками. AI задаст уточняющие вопросы."
                delay={100}
              />
              <StepItem
                number={3}
                title="Получите программу"
                description="AI проанализирует 330 проектов и выдаст персональный топ с рейтингом."
                delay={200}
              />
            </div>
            <div className="space-y-8">
              <StepItem
                number={4}
                title="Изучите детали"
                description="Карточка проекта: описание, автор, зал, теги. Попросите AI подготовить вопросы."
                delay={300}
              />
              <StepItem
                number={5}
                title="Свяжитесь с автором"
                description="Безопасный обмен контактами с согласия обеих сторон."
                delay={400}
              />
              <StepItem
                number={6}
                title="Общайтесь с AI"
                description="«сравни #1 и #3», «какой зал ближе», «покажи профиль» — любые вопросы."
                delay={500}
              />
            </div>
          </div>
        </div>
      </section>

      {/* ===================== TEAM ===================== */}
      <section
        id="team"
        className="relative py-24 px-6"
        style={{ borderTop: "1px solid var(--ld-border-subtle)" }}
      >
        <div className="mx-auto max-w-3xl">
          <div className="text-center">
            <Reveal>
              <SectionTag>Команда</SectionTag>
            </Reveal>
            <Reveal delay={100}>
              <h2
                className="font-display mt-6 text-2xl font-medium tracking-tight sm:text-3xl"
                style={{ color: "var(--ld-text)" }}
              >
                ЯСНОПОНЯТНО
              </h2>
            </Reveal>
            <Reveal delay={150}>
              <p
                className="font-body mx-auto mt-2"
                style={{ color: "var(--ld-text-muted)" }}
              >
                AI Talent Camp 2026 &middot; Проект #10
              </p>
            </Reveal>
          </div>

          <div className="mt-10 grid gap-3 sm:grid-cols-2">
            <TeamMember name="Дмитрий Горбунов" role="Тимлид, продукт, UX/UI" tag="DG" delay={0} />
            <TeamMember name="Анастасия Гапеева" role="UX/UI, фронтенд" tag="AG" delay={80} />
            <TeamMember name="Иван Александров" role="Разработка, бизнес-логика" tag="IA" delay={160} />
            <TeamMember name="Claude" role="AI-ассистент команды" tag="AI" delay={240} />
          </div>
        </div>
      </section>

      {/* ===================== FINAL CTA ===================== */}
      <section
        className="noise-overlay relative py-28 px-6"
        style={{
          borderTop: "1px solid var(--ld-border-subtle)",
          background: "var(--ld-bg-alt)",
        }}
      >
        {/* Gradient background */}
        <div className="pointer-events-none absolute inset-0 overflow-hidden opacity-20">
          <div
            className="animate-hero-gradient absolute left-1/2 top-1/2 h-[500px] w-[500px] -translate-x-1/2 -translate-y-1/2 rounded-full blur-[100px]"
            style={{ background: "var(--ld-accent)" }}
          />
        </div>

        <div className="relative z-10 mx-auto max-w-2xl text-center">
          <Reveal>
            <h2
              className="font-display text-3xl font-medium tracking-tight sm:text-4xl"
              style={{ color: "var(--ld-text)" }}
            >
              Готовы к Demo Day?
            </h2>
          </Reveal>
          <Reveal delay={100}>
            <p
              className="font-body mx-auto mt-4 max-w-md"
              style={{ color: "var(--ld-text-secondary)" }}
            >
              Персональная программа из 330 проектов за 2 минуты. Бесплатно.
            </p>
          </Reveal>
          <Reveal delay={200}>
            <a
              href={BOT_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="font-display group mt-8 inline-flex items-center gap-2 rounded-xl px-10 py-4 text-base font-medium transition-all duration-200 hover:scale-[1.03]"
              style={{
                background: "var(--ld-accent)",
                color: "#fff",
                boxShadow: `0 8px 32px var(--ld-accent-glow)`,
              }}
            >
              <MessageCircle className="h-5 w-5" />
              Открыть бота
              <ArrowRight className="h-5 w-5 transition-transform group-hover:translate-x-0.5" />
            </a>
          </Reveal>
        </div>
      </section>

      {/* ===================== FOOTER ===================== */}
      <footer
        className="py-8 px-6"
        style={{ borderTop: "1px solid var(--ld-border-subtle)" }}
      >
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 sm:flex-row">
          <div
            className="font-display flex items-center gap-2 text-xs tracking-wider"
            style={{ color: "var(--ld-text-muted)" }}
          >
            <Sparkles className="h-3 w-3" />
            DD.AI &copy; 2026
          </div>
          <div
            className="font-body flex items-center gap-6 text-xs"
            style={{ color: "var(--ld-text-muted)" }}
          >
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 transition-opacity hover:opacity-70"
            >
              <Github className="h-3.5 w-3.5" />
              GitHub
            </a>
            <a
              href={BOT_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 transition-opacity hover:opacity-70"
            >
              <MessageCircle className="h-3.5 w-3.5" />
              Telegram
            </a>
          </div>
        </div>
      </footer>
    </div>
  )
}
