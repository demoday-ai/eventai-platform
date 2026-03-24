# Frontend

Админка EventAI для организаторов событий. Приложение написано на React 19 + TypeScript + Vite и
работает поверх backend API из `backend/app/main.py`.

## Что есть в UI

- dashboard с метриками и статусами подготовки события
- импорт данных, теги, кластеризация и распределение проектов
- работа с экспертами, покрытием залов и расписанием
- messaging, participants, guests, projects, settings, audit log

Маршруты приложения собраны в `src/App.tsx`, общая раскладка — в `src/components/layout/`.

## Стек

- React 19
- TypeScript
- Vite
- React Router
- TanStack Query
- Tailwind CSS
- Testing Library + Vitest

## Команды

```bash
npm install
npm run dev
npm run build
npm run test
```

По умолчанию frontend ожидает API по `/api/v1`. В Docker Compose приложение собирается с
`VITE_API_URL=/api/v1`.
