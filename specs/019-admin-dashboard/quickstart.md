# Quickstart: Dashboard и прогресс

**Feature**: 019-admin-dashboard
**Date**: 2026-02-09

## Prerequisites

- Node.js 18+, npm 9+
- Python 3.12+
- PostgreSQL 16 running
- Backend запущен на `localhost:8000` (с миграциями)
- Frontend dependencies installed

## Setup

### Backend

```bash
# 1. Checkout branch
git checkout 019-admin-dashboard

# 2. Install dependencies
cd backend
pip install -e ".[dev]"

# 3. Run migrations (добавляет поле source в users)
alembic upgrade head

# 4. Start backend
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env   # VITE_API_BASE_URL=http://localhost:8000/api/v1
npm run dev
```

Открыть http://localhost:5173

## Demo Flow

### Сценарий 1: Empty State (US-1)

1. Убедиться, что нет активного события (или чистая БД)
2. Открыть Dashboard → http://localhost:5173/
3. **Ожидание**: центрированная карточка «Нет активного мероприятия» + кнопка «Перейти к импорту»
4. Global Stepper — все 3 фазы серые (not_started)

### Сценарий 2: Global Stepper + Quick Action (US-2, US-3)

1. Создать событие через Import → вкладка «Событие»
2. Загрузить проекты, студентов, экспертов
3. **Ожидание**: Stepper — фаза «Данные» зелёная, остальные серые
4. Quick Action: «Запустите кластеризацию по залам» + кнопка «Перейти»
5. Одобрить кластеризацию → Stepper обновляется

### Сценарий 3: Метрики и обратный отсчёт (US-4, US-5)

1. Загрузить данные (проекты, студенты, эксперты, партнёры)
2. **Ожидание**: 5 карточек метрик с корректными числами
3. Дата мероприятия + обратный отсчёт в днях

### Сценарий 4: Таблица покрытия (US-6)

1. Одобрить кластеризацию (появятся залы)
2. Назначить экспертов по залам
3. **Ожидание**: таблица с 5-уровневой шкалой:
   - 0 экспертов → «Пробел» (красный)
   - 1 эксперт → «Частично» (жёлтый)
   - 2 эксперта → «Покрыт» (зелёный)
   - 3 эксперта → «Отлично» (зелёный)
   - \>3 экспертов → «Перебор» (синий/серый)

### Сценарий 5: Auto-refresh (US-7)

1. Открыть Dashboard в двух вкладках
2. В одной — загрузить новые проекты
3. **Ожидание**: через 30-60 сек другая вкладка обновит метрики без мерцания

## API Endpoints

```bash
# Dashboard metrics (расширенный)
curl http://localhost:8000/api/v1/admin/dashboard \
  -H "Authorization: Bearer <token>"

# Pipeline status (новый)
curl http://localhost:8000/api/v1/admin/pipeline-status \
  -H "Authorization: Bearer <token>"

# Room coverage
curl http://localhost:8000/api/v1/admin/coverage \
  -H "Authorization: Bearer <token>"
```

## Run Tests

```bash
# Backend
cd backend
pytest tests/test_admin_dashboard.py -v

# Frontend
cd frontend
npm test -- Dashboard
```

## Key Files

| Файл | Описание |
|------|----------|
| `backend/app/api/admin/dashboard.py` | Роуты dashboard + pipeline-status |
| `backend/app/services/admin/dashboard_service.py` | Бизнес-логика: метрики, pipeline, coverage |
| `backend/app/schemas/admin.py` | Pydantic-схемы ответов |
| `frontend/src/pages/Dashboard.tsx` | Главная страница Dashboard |
| `frontend/src/components/dashboard/` | Под-компоненты: EmptyState, GlobalStepper, QuickAction, MetricCards, EventCountdown, CoverageTable |
| `frontend/src/components/layout/AppLayout.tsx` | Layout с GlobalStepper в header |
| `frontend/src/hooks/usePipelineStatus.ts` | TanStack Query hook для pipeline-status |
| `frontend/src/lib/api-client.ts` | API-клиент: getPipelineStatus(), getDashboard() |
