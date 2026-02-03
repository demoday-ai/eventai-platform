# Quickstart: Organizer Web Admin

## Prerequisites

- Node.js 18+
- npm 9+
- Backend запущен на `localhost:8000`

## Setup

```bash
# 1. Перейти в папку frontend
cd frontend

# 2. Установить зависимости
npm install

# 3. Скопировать env
cp .env.example .env

# 4. Запустить dev server
npm run dev
```

Открыть http://localhost:5173

## Mock Login

Для входа использовать Telegram ID из списка организаторов.

Тестовые ID (захардкожены в dev):
- `123456789`
- `987654321`

## Scripts

```bash
npm run dev      # Dev server с HMR
npm run build    # Production build
npm run preview  # Preview production build
npm run lint     # ESLint
npm run format   # Prettier
```

## Project Structure

```
src/
├── api/         # API клиент и типы
├── components/  # React компоненты
├── pages/       # Страницы (роуты)
├── hooks/       # Custom hooks
├── lib/         # Утилиты
└── App.tsx      # Root компонент
```

## Key Files

| Файл | Описание |
|------|----------|
| `src/api/client.ts` | HTTP клиент с auth |
| `src/hooks/useAuth.ts` | Auth state и методы |
| `src/pages/Login.tsx` | Страница входа |
| `src/pages/Dashboard.tsx` | Главный дашборд |

## Environment Variables

```env
VITE_API_URL=http://localhost:8000/api/v1
VITE_APP_NAME=Demo Day Admin
```

## Adding shadcn components

```bash
npx shadcn@latest add button
npx shadcn@latest add card
npx shadcn@latest add table
npx shadcn@latest add input
```
