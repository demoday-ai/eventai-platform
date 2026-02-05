import { useCallback, useEffect, useRef, useState } from "react"
import {
  MessageCircle,
  MapPin,
  Users,
  BarChart3,
  Phone,
  ChevronDown,
  Target,
  Brain,
  ArrowRight,
  Github,
  Sun,
  Moon,
  Send,
  Bot,
  Hash,
  Calendar,
  Building2,
  Clapperboard,
  Mail,
  CheckCircle,
  Menu,
  X,
} from "lucide-react"

const BOT_URL = "https://t.me/demoday_ai_talent_hub_test_bot"
const GITHUB_URL = "https://github.com/AI-Talent-Camp-2026/demoday-ai"

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
    <Reveal delay={index * 80} className="h-full">
      <div
        className="group relative h-full overflow-hidden rounded-xl p-6 transition-all duration-300 hover:-translate-y-1 cursor-default"
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
  telegram,
  photo,
}: {
  name: string
  role: string
  tag: string
  delay: number
  telegram?: string
  photo?: string
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
        {photo ? (
          <img
            src={photo}
            alt={name}
            className="h-11 w-11 rounded-full object-cover"
          />
        ) : (
          <div
            className="font-display flex h-11 w-11 items-center justify-center rounded-full text-xs font-medium uppercase tracking-wider"
            style={{
              background: "var(--ld-accent-soft)",
              color: "var(--ld-accent)",
            }}
          >
            {tag}
          </div>
        )}
        <div className="flex-1">
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
        {telegram && (
          <a
            href={`https://t.me/${telegram}`}
            target="_blank"
            rel="noopener noreferrer"
            className="font-body flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium transition-all duration-200 hover:scale-105"
            style={{
              background: "var(--ld-accent-soft)",
              color: "var(--ld-accent)",
            }}
          >
            @{telegram}
          </a>
        )}
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
   Navigation
   ============================================================ */

const NAV_LINKS = [
  { href: "#features", label: "Возможности" },
  { href: "#case", label: "Демо" },
  { href: "#how", label: "Подключение" },
  { href: "#faq", label: "FAQ" },
  { href: "#contact", label: "Связаться" },
]

function NavBar({ dark, toggle }: { dark: boolean; toggle: () => void }) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener("scroll", handleScroll, { passive: true })
    return () => window.removeEventListener("scroll", handleScroll)
  }, [])

  // Close mobile menu on navigation
  const handleNavClick = () => setMobileOpen(false)

  return (
    <nav
      className="fixed top-0 z-50 w-full transition-all duration-300"
      style={{
        background: scrolled ? "var(--ld-nav-bg)" : "transparent",
        backdropFilter: scrolled ? "blur(20px)" : "none",
        borderBottom: scrolled ? "1px solid var(--ld-border-subtle)" : "1px solid transparent",
      }}
    >
      <div className="relative mx-auto max-w-6xl px-4 py-3 sm:px-6 sm:py-4">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <a
            href="#"
            className="font-display flex items-center gap-2 text-base font-semibold tracking-tight sm:text-lg"
            style={{ color: "var(--ld-text)" }}
          >
            <img src="/logo.png" alt="EventAI" className="h-8 w-8 rounded-lg" />
            <span className="hidden sm:inline">EventAI</span>
          </a>

          {/* Desktop Nav - Centered */}
          <div className="font-display absolute left-1/2 top-1/2 hidden -translate-x-1/2 -translate-y-1/2 items-center gap-1 md:flex">
            {NAV_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="rounded-lg px-3 py-2 text-sm font-medium transition-all duration-200 hover:bg-[var(--ld-surface-hover)]"
                style={{ color: "var(--ld-text-secondary)" }}
              >
                {link.label}
              </a>
            ))}
          </div>

          {/* Right side */}
          <div className="flex items-center gap-2 sm:gap-3">
          <button
            onClick={toggle}
            className="flex h-9 w-9 items-center justify-center rounded-lg transition-all duration-200 hover:scale-105"
            style={{
              background: "var(--ld-surface)",
              border: "1px solid var(--ld-border)",
              color: "var(--ld-text-secondary)",
            }}
            aria-label="Переключить тему"
          >
            {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>

          {/* Desktop CTA */}
          <a
            href={BOT_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="font-display hidden items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-all duration-200 hover:scale-[1.02] hover:shadow-lg sm:flex"
            style={{
              background: "var(--ld-accent)",
              color: "#fff",
              boxShadow: "0 2px 8px var(--ld-accent-glow)",
            }}
          >
            <MessageCircle className="h-4 w-4" />
            <span className="hidden lg:inline">Попробовать</span>
            <span className="lg:hidden">Demo</span>
          </a>

          {/* Mobile menu button */}
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="flex h-9 w-9 items-center justify-center rounded-lg transition-all duration-200 md:hidden"
            style={{
              background: "var(--ld-surface)",
              border: "1px solid var(--ld-border)",
              color: "var(--ld-text)",
            }}
            aria-label="Меню"
          >
            {mobileOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      <div
        className={`overflow-hidden transition-all duration-300 md:hidden ${
          mobileOpen ? "max-h-96 opacity-100" : "max-h-0 opacity-0"
        }`}
        style={{ background: "var(--ld-surface)" }}
      >
        <div className="border-t px-4 py-3" style={{ borderColor: "var(--ld-border-subtle)" }}>
          {NAV_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              onClick={handleNavClick}
              className="font-display block rounded-lg px-3 py-3 text-sm font-medium transition-colors"
              style={{ color: "var(--ld-text)" }}
            >
              {link.label}
            </a>
          ))}
          <a
            href={BOT_URL}
            target="_blank"
            rel="noopener noreferrer"
            onClick={handleNavClick}
            className="font-display mt-2 flex items-center justify-center gap-2 rounded-lg px-4 py-3 text-sm font-medium"
            style={{ background: "var(--ld-accent)", color: "#fff" }}
          >
            <MessageCircle className="h-4 w-4" />
            Попробовать Live Demo
          </a>
        </div>
      </div>
    </nav>
  )
}

/* ============================================================
   Lead Capture Form
   ============================================================ */

function LeadCaptureForm() {
  const [formState, setFormState] = useState<"idle" | "sending" | "success" | "error">("idle")
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    telegram: "",
    phone: "",
    eventType: "",
    message: "",
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormState("sending")

    try {
      const response = await fetch("/api/v1/leads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: formData.name,
          email: formData.email,
          telegram: formData.telegram || undefined,
          phone: formData.phone || undefined,
          event_type: formData.eventType,
          message: formData.message,
        }),
      })

      if (!response.ok) {
        throw new Error("Failed to submit")
      }

      setFormState("success")
    } catch (error) {
      console.error("Lead submission failed:", error)
      setFormState("error")
    }
  }

  if (formState === "success") {
    return (
      <div
        className="mt-8 rounded-2xl p-8 text-center"
        style={{
          background: "var(--ld-surface)",
          border: "1px solid var(--ld-border)",
          boxShadow: "var(--ld-card-shadow)",
        }}
      >
        <div
          className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full"
          style={{ background: "var(--ld-teal-soft)" }}
        >
          <CheckCircle className="h-8 w-8" style={{ color: "var(--ld-teal)" }} />
        </div>
        <h3
          className="font-display text-xl font-medium"
          style={{ color: "var(--ld-text)" }}
        >
          Заявка отправлена
        </h3>
        <p
          className="font-body mt-2 text-sm"
          style={{ color: "var(--ld-text-secondary)" }}
        >
          Свяжемся с вами в течение 24 часов
        </p>
      </div>
    )
  }

  if (formState === "error") {
    return (
      <div
        className="mt-8 rounded-2xl p-8 text-center"
        style={{
          background: "var(--ld-surface)",
          border: "1px solid var(--ld-border)",
          boxShadow: "var(--ld-card-shadow)",
        }}
      >
        <div
          className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full"
          style={{ background: "var(--ld-ember-soft)" }}
        >
          <Mail className="h-8 w-8" style={{ color: "var(--ld-ember)" }} />
        </div>
        <h3
          className="font-display text-xl font-medium"
          style={{ color: "var(--ld-text)" }}
        >
          Что-то пошло не так
        </h3>
        <p
          className="font-body mt-2 text-sm"
          style={{ color: "var(--ld-text-secondary)" }}
        >
          Напишите напрямую в Telegram:{" "}
          <a
            href="https://t.me/grbn_dima"
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: "var(--ld-accent)" }}
          >
            @grbn_dima
          </a>
        </p>
        <button
          onClick={() => setFormState("idle")}
          className="font-display mt-4 rounded-lg px-4 py-2 text-sm font-medium transition-all duration-200 hover:scale-[1.02]"
          style={{
            background: "var(--ld-accent-soft)",
            color: "var(--ld-accent)",
          }}
        >
          Попробовать снова
        </button>
      </div>
    )
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="mt-8 rounded-2xl p-6 sm:p-8"
      style={{
        background: "var(--ld-surface)",
        border: "1px solid var(--ld-border)",
        boxShadow: "var(--ld-card-shadow)",
      }}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label
            htmlFor="name"
            className="font-display mb-1.5 block text-xs font-medium uppercase tracking-wider"
            style={{ color: "var(--ld-text-muted)" }}
          >
            Имя
          </label>
          <input
            type="text"
            id="name"
            required
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            className="font-body w-full rounded-lg px-4 py-3 text-sm outline-none transition-all duration-200 focus:ring-2"
            style={{
              background: "var(--ld-bg)",
              border: "1px solid var(--ld-border)",
              color: "var(--ld-text)",
            }}
            placeholder="Как к вам обращаться"
          />
        </div>
        <div>
          <label
            htmlFor="email"
            className="font-display mb-1.5 block text-xs font-medium uppercase tracking-wider"
            style={{ color: "var(--ld-text-muted)" }}
          >
            Email
          </label>
          <input
            type="email"
            id="email"
            required
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            className="font-body w-full rounded-lg px-4 py-3 text-sm outline-none transition-all duration-200 focus:ring-2"
            style={{
              background: "var(--ld-bg)",
              border: "1px solid var(--ld-border)",
              color: "var(--ld-text)",
            }}
            placeholder="email@company.com"
          />
        </div>
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <div>
          <label
            htmlFor="telegram"
            className="font-display mb-1.5 block text-xs font-medium uppercase tracking-wider"
            style={{ color: "var(--ld-text-muted)" }}
          >
            Telegram
            <span className="font-body ml-1 normal-case tracking-normal" style={{ color: "var(--ld-text-muted)" }}>
              (опционально)
            </span>
          </label>
          <input
            type="text"
            id="telegram"
            value={formData.telegram}
            onChange={(e) => setFormData({ ...formData, telegram: e.target.value })}
            className="font-body w-full rounded-lg px-4 py-3 text-sm outline-none transition-all duration-200 focus:ring-2"
            style={{
              background: "var(--ld-bg)",
              border: "1px solid var(--ld-border)",
              color: "var(--ld-text)",
            }}
            placeholder="@username"
          />
        </div>
        <div>
          <label
            htmlFor="phone"
            className="font-display mb-1.5 block text-xs font-medium uppercase tracking-wider"
            style={{ color: "var(--ld-text-muted)" }}
          >
            Телефон
            <span className="font-body ml-1 normal-case tracking-normal" style={{ color: "var(--ld-text-muted)" }}>
              (опционально)
            </span>
          </label>
          <input
            type="tel"
            id="phone"
            value={formData.phone}
            onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
            className="font-body w-full rounded-lg px-4 py-3 text-sm outline-none transition-all duration-200 focus:ring-2"
            style={{
              background: "var(--ld-bg)",
              border: "1px solid var(--ld-border)",
              color: "var(--ld-text)",
            }}
            placeholder="+7 (999) 123-45-67"
          />
        </div>
      </div>

      <div className="mt-4">
        <label
          htmlFor="eventType"
          className="font-display mb-1.5 block text-xs font-medium uppercase tracking-wider"
          style={{ color: "var(--ld-text-muted)" }}
        >
          Тип мероприятия
        </label>
        <select
          id="eventType"
          required
          value={formData.eventType}
          onChange={(e) => setFormData({ ...formData, eventType: e.target.value })}
          className="font-body w-full rounded-lg px-4 py-3 text-sm outline-none transition-all duration-200 focus:ring-2"
          style={{
            background: "var(--ld-bg)",
            border: "1px solid var(--ld-border)",
            color: formData.eventType ? "var(--ld-text)" : "var(--ld-text-muted)",
          }}
        >
          <option value="">Выберите тип</option>
          <option value="demoday">Demo Day / Pitch Day</option>
          <option value="conference">Конференция</option>
          <option value="hackathon">Хакатон</option>
          <option value="exhibition">Выставка / Ярмарка</option>
          <option value="other">Другое</option>
        </select>
      </div>

      <div className="mt-4">
        <label
          htmlFor="message"
          className="font-display mb-1.5 block text-xs font-medium uppercase tracking-wider"
          style={{ color: "var(--ld-text-muted)" }}
        >
          Расскажите о мероприятии
          <span className="font-body ml-1 normal-case tracking-normal" style={{ color: "var(--ld-text-muted)" }}>
            (опционально)
          </span>
        </label>
        <textarea
          id="message"
          rows={3}
          value={formData.message}
          onChange={(e) => setFormData({ ...formData, message: e.target.value })}
          className="font-body w-full resize-none rounded-lg px-4 py-3 text-sm outline-none transition-all duration-200 focus:ring-2"
          style={{
            background: "var(--ld-bg)",
            border: "1px solid var(--ld-border)",
            color: "var(--ld-text)",
          }}
          placeholder="Сколько участников, проектов, залов? Какие задачи хотите решить?"
        />
      </div>

      <button
        type="submit"
        disabled={formState === "sending"}
        className="font-display mt-6 flex w-full items-center justify-center gap-2 rounded-xl px-6 py-4 text-sm font-medium transition-all duration-200 hover:scale-[1.02] disabled:opacity-70 disabled:cursor-not-allowed"
        style={{
          background: "var(--ld-accent)",
          color: "#fff",
          boxShadow: "0 4px 16px var(--ld-accent-glow)",
        }}
      >
        {formState === "sending" ? (
          <>
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
            Отправляем...
          </>
        ) : (
          <>
            <Mail className="h-4 w-4" />
            Оставить заявку
          </>
        )}
      </button>

      <p
        className="font-body mt-4 text-center text-xs"
        style={{ color: "var(--ld-text-muted)" }}
      >
        Нажимая кнопку, вы соглашаетесь на обработку персональных данных
      </p>
    </form>
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
      <NavBar dark={dark} toggle={toggle} />

      {/* ===================== HERO ===================== */}
      <section className="noise-overlay dot-grid relative flex min-h-screen flex-col items-center justify-center px-4 pt-20 pb-12 sm:px-6 sm:pt-24 sm:pb-16">
        {/* Gradient background - animated on desktop, static on mobile */}
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          {/* Primary gradient blob */}
          <div
            className="animate-hero-gradient absolute -left-32 -top-32 h-[600px] w-[600px] rounded-full opacity-30 blur-[120px]"
            style={{ background: "var(--ld-hero-gradient-1)" }}
          />
          {/* Secondary gradient blob */}
          <div
            className="animate-hero-gradient absolute -right-20 top-1/4 h-[500px] w-[500px] rounded-full opacity-20 blur-[100px]"
            style={{ background: "var(--ld-hero-gradient-2)", animationDelay: "-7s" }}
          />
          {/* Accent gradient blob */}
          <div
            className="animate-hero-gradient absolute bottom-0 left-1/3 h-[400px] w-[400px] rounded-full opacity-15 blur-[80px]"
            style={{ background: "var(--ld-hero-gradient-3)", animationDelay: "-14s" }}
          />
        </div>

        <div className="relative z-10 mx-auto max-w-5xl text-center">
          {/* Target audience badge - PROMINENT */}
          <Reveal>
            <div className="mb-8 flex justify-center">
              <div
                className="font-display inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-xs font-semibold sm:gap-2 sm:px-6 sm:py-3 sm:text-sm"
                style={{
                  background: "var(--ld-accent)",
                  color: "#fff",
                  boxShadow: "0 4px 24px var(--ld-accent-glow)",
                }}
              >
                <Target className="h-4 w-4 sm:h-5 sm:w-5" />
                Для организаторов мероприятий
              </div>
            </div>
          </Reveal>

          {/* Main headline */}
          <Reveal delay={100}>
            <h1 className="font-display text-3xl font-bold leading-[1.1] tracking-tight sm:text-4xl md:text-5xl lg:text-6xl">
              <span style={{ color: "var(--ld-text)" }}>
                Персональная программа
              </span>
              <br className="hidden sm:block" />
              <span className="sm:hidden"> </span>
              <span
                className="bg-clip-text text-transparent"
                style={{
                  backgroundImage: `linear-gradient(135deg, var(--ld-hero-gradient-1) 0%, var(--ld-hero-gradient-2) 50%, var(--ld-hero-gradient-3) 100%)`,
                }}
              >
                каждому гостю
              </span>
            </h1>
          </Reveal>

          {/* Subheadline with key metric */}
          <Reveal delay={150}>
            <p
              className="font-display mx-auto mt-6 text-lg font-medium sm:text-xl md:text-2xl"
              style={{ color: "var(--ld-text-secondary)" }}
            >
              за <span style={{ color: "var(--ld-accent)" }}>минуту</span> диалога с AI-ботом
            </p>
          </Reveal>

          {/* CTA Buttons */}
          <Reveal delay={300}>
            <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row sm:justify-center sm:gap-5">
              <a
                href={BOT_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="font-display group inline-flex w-full items-center justify-center gap-3 rounded-2xl px-8 py-4 text-base font-semibold transition-all duration-300 hover:scale-[1.03] hover:shadow-2xl active:scale-[0.98] sm:w-auto sm:text-lg"
                style={{
                  background: "var(--ld-accent)",
                  color: "#fff",
                  boxShadow: "0 8px 32px var(--ld-accent-glow)",
                }}
              >
                <MessageCircle className="h-5 w-5 sm:h-6 sm:w-6" />
                Попробовать Live Demo
                <ArrowRight className="h-5 w-5 transition-transform group-hover:translate-x-1 sm:h-6 sm:w-6" />
              </a>
              <a
                href={GITHUB_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="font-display inline-flex w-full items-center justify-center gap-2 rounded-2xl px-6 py-4 text-base font-medium transition-all duration-200 hover:scale-[1.02] sm:w-auto"
                style={{
                  background: "var(--ld-surface)",
                  color: "var(--ld-text)",
                  border: "2px solid var(--ld-border)",
                }}
              >
                <Github className="h-5 w-5" />
                GitHub
              </a>
            </div>
          </Reveal>

          {/* Social proof stats */}
          <Reveal delay={400}>
            <div className="mx-auto mt-10 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm sm:text-base">
              <span style={{ color: "var(--ld-text-secondary)" }}>
                <span className="font-display font-bold" style={{ color: "var(--ld-accent)" }}>330</span> проектов
              </span>
              <span style={{ color: "var(--ld-border)" }}>•</span>
              <span style={{ color: "var(--ld-text-secondary)" }}>
                <span className="font-display font-bold" style={{ color: "var(--ld-teal)" }}>10</span> залов
              </span>
              <span style={{ color: "var(--ld-border)" }}>•</span>
              <span style={{ color: "var(--ld-text-secondary)" }}>
                <span className="font-display font-bold" style={{ color: "var(--ld-ember)" }}>1 мин</span> на подборку
              </span>
            </div>
          </Reveal>
        </div>

        {/* Scroll indicator - desktop only */}
        <Reveal delay={600} className="absolute bottom-8 hidden md:block">
          <a href="#problem" className="group flex flex-col items-center gap-2 transition-opacity hover:opacity-70">
            <span className="font-body text-xs uppercase tracking-widest" style={{ color: "var(--ld-text-muted)" }}>
              Узнать больше
            </span>
            <ChevronDown className="h-5 w-5 animate-float" style={{ color: "var(--ld-text-muted)" }} />
          </a>
        </Reveal>
      </section>

      {/* ===================== PROBLEM ===================== */}
      <section
        id="problem"
        className="relative py-16 px-6 sm:py-24"
        style={{ borderTop: "1px solid var(--ld-border-subtle)" }}
      >
        <div className="mx-auto max-w-4xl">
          <div className="text-center">
            <Reveal>
              <SectionTag>Проблема</SectionTag>
            </Reveal>
            <Reveal delay={100}>
              <h2
                className="font-display mt-5 text-xl font-medium tracking-tight sm:text-2xl md:text-3xl"
                style={{ color: "var(--ld-text)" }}
              >
                Чем больше проектов —{" "}
                <span style={{ color: "var(--ld-ember)" }}>тем меньше видят гости</span>
              </h2>
            </Reveal>
          </div>

          <div className="mx-auto mt-10 grid max-w-3xl grid-cols-1 gap-4 sm:grid-cols-3">
            <StatBlock value="<20%" label="проектов успеет посетить гость" accent="ember" delay={150} />
            <StatBlock value="68%" label="релевантного контента пропущено" accent="amber" delay={200} />
            <StatBlock value="0" label="follow-up после мероприятия" accent="teal" delay={250} />
          </div>

          <Reveal delay={300}>
            <p
              className="font-body mx-auto mt-8 max-w-2xl text-center text-sm leading-relaxed sm:text-base"
              style={{ color: "var(--ld-text-secondary)" }}
            >
              Гости не знают, куда идти. Бизнес-партнёры не находят нужные проекты.
              Эксперты перегружены. Организаторы составляют расписание вручную за ночь до события.
            </p>
          </Reveal>
        </div>
      </section>

      {/* ===================== FEATURES / PLATFORM ===================== */}
      <section
        id="features"
        className="relative py-16 px-6 sm:py-24"
        style={{
          borderTop: "1px solid var(--ld-border-subtle)",
          background: "var(--ld-bg-alt)",
        }}
      >
        <div className="mx-auto max-w-5xl">
          <div className="text-center">
            <Reveal>
              <SectionTag>Решение</SectionTag>
            </Reveal>
            <Reveal delay={100}>
              <h2
                className="font-display mt-5 text-xl font-medium tracking-tight sm:text-2xl md:text-3xl"
                style={{ color: "var(--ld-text)" }}
              >
                Telegram-бот делает мероприятие персональным
              </h2>
            </Reveal>
          </div>

          <div className="mt-10 grid gap-3 sm:mt-12 sm:grid-cols-2 lg:grid-cols-3">
            <FeatureCard
              icon={Target}
              title="Персональный топ проектов"
              description="AI ранжирует все проекты под интересы гостя. Рейтинг релевантности, разбивка по залам."
              index={0}
            />
            <FeatureCard
              icon={Brain}
              title="Q&A-помощник"
              description="3-5 умных вопросов к проекту под профиль гостя. Готовый гайд для диалога."
              index={1}
            />
            <FeatureCard
              icon={BarChart3}
              title="Сравнение проектов"
              description="Таблица сравнения 2-5 проектов: тема, зал, отличия — для быстрого выбора."
              index={2}
            />
            <FeatureCard
              icon={MapPin}
              title="Маршрут по залам"
              description="Оптимальный порядок посещения с учётом параллельных секций."
              index={3}
            />
            <FeatureCard
              icon={Phone}
              title="Контакт с авторами"
              description="Запрос контакта через бота. Автор решает — делиться или нет."
              index={4}
            />
            <FeatureCard
              icon={Users}
              title="5 ролей"
              description="Гость, партнёр, эксперт, студент, организатор — свой интерфейс каждому."
              index={5}
            />
          </div>
        </div>
      </section>

      {/* ===================== METRICS ===================== */}
      <section
        id="metrics"
        className="relative py-16 px-6 sm:py-24"
        style={{ borderTop: "1px solid var(--ld-border-subtle)" }}
      >
        <div className="mx-auto max-w-5xl">
          <div className="text-center">
            <Reveal>
              <SectionTag>Качество рекомендаций</SectionTag>
            </Reveal>
            <Reveal delay={100}>
              <h2
                className="font-display mt-5 text-xl font-medium tracking-tight sm:text-2xl md:text-3xl"
                style={{ color: "var(--ld-text)" }}
              >
                Измеримая персонализация:{" "}
                <span style={{ color: "var(--ld-accent)" }}>IDF + LLM</span>
              </h2>
            </Reveal>
            <Reveal delay={150}>
              <p
                className="font-body mx-auto mt-4 max-w-2xl text-sm leading-relaxed sm:text-base"
                style={{ color: "var(--ld-text-secondary)" }}
              >
                Оценка на 10 реальных профилях (5 гостей + 5 бизнес-партнёров) по экспертным аннотациям 330 проектов
              </p>
            </Reveal>
          </div>

          <div className="mx-auto mt-10 grid max-w-4xl grid-cols-1 gap-4 sm:grid-cols-3">
            <Reveal delay={200}>
              <div
                className="rounded-xl p-6 text-center"
                style={{
                  background: "var(--ld-surface)",
                  border: "1px solid var(--ld-border)",
                }}
              >
                <div
                  className="font-display text-3xl font-medium"
                  style={{ color: "var(--ld-accent)" }}
                >
                  0.82
                </div>
                <div
                  className="font-display mt-1 text-sm font-medium"
                  style={{ color: "var(--ld-text)" }}
                >
                  NDCG@15
                </div>
                <div
                  className="font-body mt-2 text-xs"
                  style={{ color: "var(--ld-text-muted)" }}
                >
                  Релевантные проекты в топе списка
                </div>
              </div>
            </Reveal>
            <Reveal delay={250}>
              <div
                className="rounded-xl p-6 text-center"
                style={{
                  background: "var(--ld-surface)",
                  border: "1px solid var(--ld-border)",
                }}
              >
                <div
                  className="font-display text-3xl font-medium"
                  style={{ color: "var(--ld-teal)" }}
                >
                  0.71
                </div>
                <div
                  className="font-display mt-1 text-sm font-medium"
                  style={{ color: "var(--ld-text)" }}
                >
                  Precision@15
                </div>
                <div
                  className="font-body mt-2 text-xs"
                  style={{ color: "var(--ld-text-muted)" }}
                >
                  7 из 10 в подборке — действительно интересны
                </div>
              </div>
            </Reveal>
            <Reveal delay={300}>
              <div
                className="rounded-xl p-6 text-center"
                style={{
                  background: "var(--ld-surface)",
                  border: "1px solid var(--ld-border)",
                }}
              >
                <div
                  className="font-display text-3xl font-medium"
                  style={{ color: "var(--ld-amber)" }}
                >
                  0.78
                </div>
                <div
                  className="font-display mt-1 text-sm font-medium"
                  style={{ color: "var(--ld-text)" }}
                >
                  Recall@15
                </div>
                <div
                  className="font-body mt-2 text-xs"
                  style={{ color: "var(--ld-text-muted)" }}
                >
                  Находим 8 из 10 подходящих проектов
                </div>
              </div>
            </Reveal>
          </div>

          <Reveal delay={350}>
            <div
              className="mx-auto mt-8 max-w-2xl rounded-xl p-5"
              style={{
                background: "var(--ld-accent-soft)",
                border: "1px solid var(--ld-border-subtle)",
              }}
            >
              <p
                className="font-body text-center text-sm leading-relaxed"
                style={{ color: "var(--ld-text-secondary)" }}
              >
                <strong style={{ color: "var(--ld-text)" }}>Как измеряли:</strong> система подбирает проекты по тегам и ключевым словам профиля, затем AI (Claude/GPT) переранжирует топ-20 с учётом контекста. Результаты сравнили с оценками экспертов — каждая пара «профиль-проект» размечена по шкале релевантности 0-3.
              </p>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ===================== CASE STUDY ===================== */}
      <section
        id="case"
        className="relative py-16 px-6 sm:py-24"
        style={{ borderTop: "1px solid var(--ld-border-subtle)" }}
      >
        <div className="mx-auto max-w-5xl">
          <div className="text-center">
            <Reveal>
              <SectionTag>Как это выглядит</SectionTag>
            </Reveal>
            <Reveal delay={100}>
              <h2
                className="font-display mt-5 text-xl font-medium tracking-tight sm:text-2xl md:text-3xl"
                style={{ color: "var(--ld-text)" }}
              >
                Диалог с ботом → персональная программа
              </h2>
            </Reveal>
            <Reveal delay={150}>
              <p
                className="font-body mx-auto mt-3 max-w-lg text-sm sm:text-base"
                style={{ color: "var(--ld-text-secondary)" }}
              >
                Реальный пример: HR-директор ищет проекты по автоматизации найма
              </p>
            </Reveal>
          </div>

          <div className="mt-10 grid gap-6 lg:grid-cols-5 lg:gap-8">
            {/* Left: what bot does - simplified */}
            <div className="space-y-4 lg:col-span-2">
              <Reveal>
                <div
                  className="rounded-xl p-5"
                  style={{
                    background: "var(--ld-surface)",
                    border: "1px solid var(--ld-border)",
                  }}
                >
                  <div
                    className="font-display text-xs font-medium uppercase tracking-widest"
                    style={{ color: "var(--ld-text-muted)" }}
                  >
                    Бот умеет
                  </div>
                  <ul className="font-body mt-3 space-y-2 text-sm" style={{ color: "var(--ld-text-secondary)" }}>
                    {[
                      "Профилировать через диалог",
                      "Ранжировать проекты под гостя",
                      "Генерировать вопросы к проектам",
                      "Сравнивать проекты в таблице",
                      "Организовать обмен контактами",
                    ].map((item, i) => (
                      <li key={i} className="flex items-center gap-2">
                        <span style={{ color: "var(--ld-accent)" }} className="shrink-0">
                          <ArrowRight className="h-3 w-3" />
                        </span>
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              </Reveal>
            </div>

            {/* Right: chat mockup */}
            <div className="lg:col-span-3">
              <Reveal delay={150}>
                <div
                  className="overflow-hidden rounded-2xl"
                style={{
                  background: "var(--ld-surface)",
                  border: "1px solid var(--ld-border)",
                  boxShadow: "var(--ld-card-shadow-hover)",
                }}
              >
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
                    <div className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2" style={{ background: "#22c55e", borderColor: "var(--ld-surface)" }} />
                  </div>
                  <div>
                    <div className="font-display text-sm font-medium" style={{ color: "var(--ld-text)" }}>
                      Demo Day AI
                    </div>
                    <div className="font-body text-[10px]" style={{ color: "var(--ld-text-muted)" }}>
                      online
                    </div>
                  </div>
                </div>

                <div className="space-y-3 p-5">
                  <ChatBubble side="bot" text="Расскажите, что вас интересует на Demo Day?" delay={300} />
                  <ChatBubble side="user" text="Я HR-директор, ищу проекты по автоматизации найма и AI в HR" delay={500} />
                  <ChatBubble
                    side="bot"
                    text={"Нашёл 8 проектов. Ваш топ-3:\n\n1. AI Recruiter Assistant (94%)\n   📍 Зал 2 · HR, Agents\n\n2. Resume Screening Engine (87%)\n   📍 Зал 5 · NLP, HR\n\n3. Interview Copilot (82%)\n   📍 Зал 2 · LLM, Agents"}
                    delay={700}
                  />
                  <ChatBubble side="user" text="Подготовь вопросы к проекту #1" delay={900} />
                  <ChatBubble
                    side="bot"
                    text={"Вопросы к AI Recruiter Assistant:\n\n1. Какой % ложноположительных отсевов?\n2. Как система учитывает soft skills?\n3. Какие ATS поддерживаете?"}
                    delay={1100}
                  />
                </div>

                <div
                  className="flex items-center gap-2 px-4 py-3"
                  style={{ borderTop: "1px solid var(--ld-border-subtle)" }}
                >
                  <div
                    className="font-body flex-1 rounded-lg px-3 py-2 text-xs"
                    style={{ background: "var(--ld-bg-alt)", color: "var(--ld-text-muted)" }}
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
          </div>
        </div>
      </section>

      {/* ===================== HOW IT WORKS (for organizers) ===================== */}
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
              <SectionTag>Для организаторов</SectionTag>
            </Reveal>
            <Reveal delay={100}>
              <h2
                className="font-display mt-6 text-2xl font-medium tracking-tight sm:text-3xl"
                style={{ color: "var(--ld-text)" }}
              >
                Как подключить к вашему событию
              </h2>
            </Reveal>
          </div>

          <div className="mt-14 grid gap-8 sm:grid-cols-2">
            <div className="space-y-8">
              <StepItem
                number={1}
                title="Загрузите проекты"
                description="CSV/Excel с проектами, докладами или стендами. Система извлечёт теги и метаданные автоматически."
                delay={0}
              />
              <StepItem
                number={2}
                title="Настройте залы и расписание"
                description="Админ-панель для залов, слотов, тематик. AI поможет кластеризовать проекты по трекам."
                delay={100}
              />
              <StepItem
                number={3}
                title="Запустите бота"
                description="Поделитесь ссылкой на бота с участниками. Каждый получит персональную программу."
                delay={200}
              />
            </div>
            <div className="space-y-8">
              <StepItem
                number={4}
                title="Гости профилируются за 2 мин"
                description="AI-диалог на естественном языке. Бот задаёт уточняющие вопросы и извлекает интересы."
                delay={300}
              />
              <StepItem
                number={5}
                title="AI генерирует программу"
                description="Персональный топ проектов с рейтингом, Q&A-помощник, маршрут, сравнение."
                delay={400}
              />
              <StepItem
                number={6}
                title="Аналитика и follow-up"
                description="Дашборд организатора: популярные проекты, воронка, контакты. Данные для улучшения следующего события."
                delay={500}
              />
            </div>
          </div>

          <Reveal delay={600}>
            <div className="mt-12 text-center">
              <a
                href="/login"
                className="font-display inline-flex items-center gap-2 rounded-xl px-6 py-3 text-sm font-medium transition-all duration-200 hover:scale-[1.03]"
                style={{
                  background: "var(--ld-surface)",
                  color: "var(--ld-accent)",
                  border: "2px solid var(--ld-accent)",
                }}
              >
                <BarChart3 className="h-4 w-4" />
                Войти в админ-панель
                <ArrowRight className="h-4 w-4" />
              </a>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ===================== USE CASES ===================== */}
      <section
        className="relative py-24 px-6"
        style={{ borderTop: "1px solid var(--ld-border-subtle)" }}
      >
        <div className="mx-auto max-w-4xl">
          <div className="text-center">
            <Reveal>
              <SectionTag>Применение</SectionTag>
            </Reveal>
            <Reveal delay={100}>
              <h2
                className="font-display mt-6 text-2xl font-medium tracking-tight sm:text-3xl"
                style={{ color: "var(--ld-text)" }}
              >
                Для любого мероприятия с параллельными треками
              </h2>
            </Reveal>
          </div>

          <div className="mt-10 grid gap-4 sm:grid-cols-2">
            {[
              {
                icon: Clapperboard,
                title: "Demo Day / Pitch Day",
                desc: "Студенческие проекты, стартап-питчи, инвестиционные дни. Сотни проектов — каждый гость видит свой топ.",
              },
              {
                icon: Calendar,
                title: "Конференции",
                desc: "Научные и индустриальные конференции с параллельными секциями. Персональное расписание вместо 20-страничной программы.",
              },
              {
                icon: Brain,
                title: "Хакатоны",
                desc: "Финальные презентации: жюри и менторы получают подборку проектов под свою экспертизу и готовые вопросы.",
              },
              {
                icon: Building2,
                title: "Выставки и ярмарки",
                desc: "Промышленные выставки, карьерные ярмарки. Маршрут по стендам, контакт с экспонентами через бота.",
              },
            ].map((uc, i) => (
              <Reveal key={i} delay={i * 80}>
                <div
                  className="flex gap-4 rounded-xl p-5"
                  style={{
                    background: "var(--ld-surface)",
                    border: "1px solid var(--ld-border)",
                    boxShadow: "var(--ld-card-shadow)",
                  }}
                >
                  <div
                    className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg"
                    style={{ background: "var(--ld-accent-soft)", color: "var(--ld-accent)" }}
                  >
                    <uc.icon className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="font-display text-sm font-medium" style={{ color: "var(--ld-text)" }}>
                      {uc.title}
                    </h3>
                    <p className="font-body mt-1 text-sm leading-relaxed" style={{ color: "var(--ld-text-secondary)" }}>
                      {uc.desc}
                    </p>
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ===================== FAQ ===================== */}
      <section
        id="faq"
        className="relative py-20 px-6"
        style={{ borderTop: "1px solid var(--ld-border-subtle)" }}
      >
        <div className="mx-auto max-w-3xl">
          <div className="text-center">
            <Reveal>
              <SectionTag>FAQ</SectionTag>
            </Reveal>
            <Reveal delay={100}>
              <h2
                className="font-display mt-6 text-2xl font-medium tracking-tight sm:text-3xl"
                style={{ color: "var(--ld-text)" }}
              >
                Частые вопросы
              </h2>
            </Reveal>
          </div>

          <div className="mt-10 space-y-4">
            {[
              {
                q: "Для каких мероприятий подходит платформа?",
                a: "Любые события с параллельными треками: Demo Day, конференции, хакатоны, питч-сессии, научные симпозиумы, карьерные ярмарки. Масштаб — от 50 до 500+ проектов/докладов.",
              },
              {
                q: "Как это работает для организатора?",
                a: "Админ-панель: загрузите Excel/CSV с проектами → AI кластеризует по залам → система генерирует расписание → дашборд покрытия экспертами → автоматические напоминания участникам. Всё в одном месте.",
              },
              {
                q: "Как это работает для гостя?",
                a: "Telegram-бот: минута диалога → AI понимает интересы → персональный топ проектов с рейтингом релевантности → Q&A-подсказки → уведомления о сдвигах тайминга → follow-up после события.",
              },
              {
                q: "Чем лучше Google-таблицы или Notion?",
                a: "Таблица не масштабируется: при 100+ проектах в 6 залах гость видит менее 20%. Нет персонализации, нет напоминаний, нет аналитики. Наш бот решает навигацию за минуту вместо часа ручного поиска.",
              },
              {
                q: "Откуда берутся данные о проектах?",
                a: "Организатор загружает Excel/CSV через админ-панель. AI автоматически извлекает теги, описания, тематики. Можно подключить GitHub для технических проектов. Минимум ручной работы.",
              },
              {
                q: "Сколько это стоит?",
                a: "Гибкая модель: оплата за событие (от 100 000 ₽) или годовая подписка для регулярных мероприятий. Для университетов, акселераторов и крупных конференций — индивидуальные условия. Оставьте заявку — обсудим ваш кейс.",
              },
            ].map((item, i) => (
              <Reveal key={i} delay={i * 60}>
                <details
                  className="group rounded-xl p-5"
                  style={{
                    background: "var(--ld-surface)",
                    border: "1px solid var(--ld-border)",
                  }}
                >
                  <summary
                    className="font-display flex cursor-pointer items-center justify-between text-sm font-medium sm:text-base"
                    style={{ color: "var(--ld-text)" }}
                  >
                    {item.q}
                    <ChevronDown
                      className="h-4 w-4 shrink-0 transition-transform group-open:rotate-180"
                      style={{ color: "var(--ld-text-muted)" }}
                    />
                  </summary>
                  <p
                    className="font-body mt-3 text-sm leading-relaxed"
                    style={{ color: "var(--ld-text-secondary)" }}
                  >
                    {item.a}
                  </p>
                </details>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ===================== LEAD CAPTURE ===================== */}
      <section
        id="contact"
        className="relative py-20 px-6"
        style={{
          borderTop: "1px solid var(--ld-border-subtle)",
          background: "var(--ld-bg-alt)",
        }}
      >
        <div className="mx-auto max-w-2xl">
          <div className="text-center">
            <Reveal>
              <SectionTag>Связаться</SectionTag>
            </Reveal>
            <Reveal delay={100}>
              <h2
                className="font-display mt-6 text-2xl font-medium tracking-tight sm:text-3xl"
                style={{ color: "var(--ld-text)" }}
              >
                Обсудим ваше мероприятие
              </h2>
            </Reveal>
            <Reveal delay={150}>
              <p
                className="font-body mx-auto mt-3 max-w-lg text-sm sm:text-base"
                style={{ color: "var(--ld-text-secondary)" }}
              >
                Оставьте контакт — свяжемся в течение 24 часов и расскажем, как платформа решит задачи вашего события
              </p>
            </Reveal>
          </div>

          <Reveal delay={200}>
            <LeadCaptureForm />
          </Reveal>
        </div>
      </section>

      {/* ===================== TEAM ===================== */}
      <section
        id="team"
        className="relative py-24 px-6"
        style={{
          borderTop: "1px solid var(--ld-border-subtle)",
          background: "var(--ld-bg)",
        }}
      >
        <div className="mx-auto max-w-3xl">
          <div className="text-center">
            <Reveal>
              <SectionTag>О проекте</SectionTag>
            </Reveal>
            <Reveal delay={100}>
              <div className="mt-8 flex flex-col items-center gap-6 sm:flex-row sm:justify-center sm:gap-10">
                {/* ITMO Logo */}
                <a
                  href="https://itmo.ru"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-3 transition-opacity hover:opacity-80"
                >
                  <img
                    src="https://itmo.ru/file/pages/213/logo_na_plashke_russkiy_belyy.png"
                    alt="ITMO University"
                    className="h-10 w-auto dark:invert"
                  />
                </a>
                {/* AI ITMO Logo */}
                <a
                  href="https://ai.itmo.ru/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 transition-opacity hover:opacity-80"
                >
                  <div
                    className="flex h-10 w-10 items-center justify-center rounded-lg"
                    style={{ background: "var(--ld-accent)", color: "#fff" }}
                  >
                    <Brain className="h-5 w-5" />
                  </div>
                  <span
                    className="font-display text-lg font-semibold"
                    style={{ color: "var(--ld-text)" }}
                  >
                    AI ITMO
                  </span>
                </a>
              </div>
            </Reveal>
            <Reveal delay={150}>
              <p
                className="font-body mx-auto mt-6 max-w-lg text-sm sm:text-base"
                style={{ color: "var(--ld-text-secondary)" }}
              >
                Разработано в рамках{" "}
                <span style={{ color: "var(--ld-accent)" }}>AI Talent Camp 2026</span>
                {" "}— интенсива магистратуры{" "}
                <span style={{ color: "var(--ld-accent)" }}>«Искусственный интеллект» ИТМО</span>
              </p>
            </Reveal>
          </div>

          <Reveal delay={200}>
            <div className="mt-10 grid gap-3 sm:grid-cols-2">
              <TeamMember name="Дмитрий Горбунов" role="Тимлид, продукт, UX/UI" tag="DG" delay={0} telegram="grbn_dima" photo="/team/dima.jpg" />
              <TeamMember name="Анастасия Гапеева" role="UX/UI, фронтенд" tag="AG" delay={80} photo="/team/nastya.jpg" />
              <TeamMember name="Иван Александров" role="Разработка, бизнес-логика" tag="IA" delay={160} photo="/team/ivan.jpg" />
              <TeamMember name="Claude" role="AI-ассистент команды" tag="AI" delay={240} />
            </div>
          </Reveal>
        </div>
      </section>

      {/* ===================== FINAL CTA ===================== */}
      <section
        className="noise-overlay relative py-28 px-6"
        style={{
          borderTop: "1px solid var(--ld-border-subtle)",
        }}
      >
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
              Готовы попробовать?
            </h2>
          </Reveal>
          <Reveal delay={100}>
            <p
              className="font-body mx-auto mt-4 max-w-md"
              style={{ color: "var(--ld-text-secondary)" }}
            >
              Откройте бота и пройдите демо-сценарий на данных реального Demo Day AI Talent Hub.
              Бесплатно для образовательных мероприятий.
            </p>
          </Reveal>
          <Reveal delay={200}>
            <div className="mt-8 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
              <a
                href={BOT_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="font-display group inline-flex items-center gap-2 rounded-xl px-10 py-4 text-base font-medium transition-all duration-200 hover:scale-[1.03]"
                style={{
                  background: "var(--ld-accent)",
                  color: "#fff",
                  boxShadow: `0 8px 32px var(--ld-accent-glow)`,
                }}
              >
                <MessageCircle className="h-5 w-5" />
                Live Demo в Telegram
                <ArrowRight className="h-5 w-5 transition-transform group-hover:translate-x-0.5" />
              </a>
              <a
                href={GITHUB_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="font-display inline-flex items-center gap-2 rounded-xl px-6 py-4 text-sm font-medium transition-all duration-200 hover:scale-[1.03]"
                style={{
                  background: "var(--ld-surface)",
                  color: "var(--ld-text-secondary)",
                  border: "1px solid var(--ld-border)",
                }}
              >
                <Github className="h-4 w-4" />
                Документация
              </a>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ===================== FOOTER ===================== */}
      <footer
        className="py-10 px-6"
        style={{
          background: "var(--ld-bg-alt)",
          borderTop: "1px solid var(--ld-border-subtle)",
        }}
      >
        <div className="mx-auto max-w-6xl">
          <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
            {/* Brand */}
            <div className="sm:col-span-2 lg:col-span-1">
              <a
                href="#"
                className="font-display inline-flex items-center gap-2 text-lg font-semibold"
                style={{ color: "var(--ld-text)" }}
              >
                <img src="/logo.png" alt="EventAI" className="h-8 w-8 rounded-lg" />
                EventAI
              </a>
              <p
                className="font-body mt-3 text-sm leading-relaxed"
                style={{ color: "var(--ld-text-muted)" }}
              >
                AI-платформа для персонализации мероприятий с параллельными треками
              </p>
            </div>

            {/* Links */}
            <div>
              <h4
                className="font-display text-xs font-semibold uppercase tracking-wider"
                style={{ color: "var(--ld-text-secondary)" }}
              >
                Навигация
              </h4>
              <ul className="mt-3 space-y-2">
                {NAV_LINKS.map((link) => (
                  <li key={link.href}>
                    <a
                      href={link.href}
                      className="font-body text-sm transition-colors hover:opacity-80"
                      style={{ color: "var(--ld-text-muted)" }}
                    >
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>

            {/* Resources */}
            <div>
              <h4
                className="font-display text-xs font-semibold uppercase tracking-wider"
                style={{ color: "var(--ld-text-secondary)" }}
              >
                Ресурсы
              </h4>
              <ul className="mt-3 space-y-2">
                <li>
                  <a
                    href={GITHUB_URL}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-body inline-flex items-center gap-1.5 text-sm transition-colors hover:opacity-80"
                    style={{ color: "var(--ld-text-muted)" }}
                  >
                    <Github className="h-3.5 w-3.5" />
                    GitHub
                  </a>
                </li>
                <li>
                  <a
                    href={BOT_URL}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-body inline-flex items-center gap-1.5 text-sm transition-colors hover:opacity-80"
                    style={{ color: "var(--ld-text-muted)" }}
                  >
                    <MessageCircle className="h-3.5 w-3.5" />
                    Telegram Bot
                  </a>
                </li>
                <li>
                  <a
                    href="/login"
                    className="font-body inline-flex items-center gap-1.5 text-sm transition-colors hover:opacity-80"
                    style={{ color: "var(--ld-text-muted)" }}
                  >
                    <BarChart3 className="h-3.5 w-3.5" />
                    Админ-панель
                  </a>
                </li>
              </ul>
            </div>

            {/* Contact */}
            <div>
              <h4
                className="font-display text-xs font-semibold uppercase tracking-wider"
                style={{ color: "var(--ld-text-secondary)" }}
              >
                Связаться
              </h4>
              <ul className="mt-3 space-y-2">
                <li>
                  <a
                    href="https://t.me/grbn_dima"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-body text-sm transition-colors hover:opacity-80"
                    style={{ color: "var(--ld-text-muted)" }}
                  >
                    @grbn_dima
                  </a>
                </li>
                <li>
                  <a
                    href="#contact"
                    className="font-body text-sm transition-colors hover:opacity-80"
                    style={{ color: "var(--ld-text-muted)" }}
                  >
                    Оставить заявку
                  </a>
                </li>
              </ul>
            </div>
          </div>

          {/* Bottom */}
          <div
            className="mt-10 flex flex-col items-center justify-between gap-4 border-t pt-6 sm:flex-row"
            style={{ borderColor: "var(--ld-border-subtle)" }}
          >
            <p
              className="font-body text-xs"
              style={{ color: "var(--ld-text-muted)" }}
            >
              &copy; 2026 EventAI
            </p>
            <div className="flex items-center gap-4">
              <a
                href="https://itmo.ru"
                target="_blank"
                rel="noopener noreferrer"
                className="transition-opacity hover:opacity-70"
              >
                <img
                  src="https://itmo.ru/file/pages/213/logo_na_plashke_russkiy_belyy.png"
                  alt="ITMO"
                  className="h-6 w-auto opacity-60 dark:invert"
                />
              </a>
              <a
                href="https://ai.itmo.ru"
                target="_blank"
                rel="noopener noreferrer"
                className="font-display text-xs font-medium transition-opacity hover:opacity-70"
                style={{ color: "var(--ld-text-muted)" }}
              >
                AI Talent Camp 2026
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
