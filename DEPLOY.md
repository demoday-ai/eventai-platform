# Deployment Guide

## Инфраструктура AI Talent Camp 2026

- **Edge/NAT VM**: Traefik reverse proxy на `bastion.camp.aitalenthub.ru`
- **Team VM**: 4 vCPU, 8GB RAM, 65GB SSD, private subnet
- **Домен**: `team10.camp.aitalenthub.ru` (или другой номер команды)

## Pre-requisites

1. **Docker** и **Docker Compose** установлены на Team VM
2. **Traefik network** создана: `docker network create traefik-public`
3. SSH доступ к Team VM через bastion
4. Git repository клонирован на VM

## Deployment Steps

### 1. Подготовка окружения

```bash
# Подключиться к Team VM через bastion
ssh -J bastion.camp.aitalenthub.ru team10.camp.aitalenthub.ru

# Клонировать репозиторий (если еще не сделано)
cd ~
git clone https://github.com/AI-Talent-Camp-2026/demoday-ai.git
cd demoday-ai

# Создать production .env файлы
cp .env.prod.example .env.prod
cp backend/.env.example backend/.env

# Отредактировать .env.prod и backend/.env
nano .env.prod
nano backend/.env
```

### 2. Настройка переменных окружения

**`.env.prod`:**
```bash
DOMAIN=team10.camp.aitalenthub.ru  # Ваш домен
POSTGRES_USER=demoday
POSTGRES_PASSWORD=<strong-random-password>
POSTGRES_DB=demoday
VITE_APP_NAME=Demo Day Admin
```

**`backend/.env`:**
```bash
# Database
DATABASE_URL=postgresql+asyncpg://demoday:<password>@db:5432/demoday

# Security
SECRET_KEY=<generate-long-random-string>  # Используйте: openssl rand -hex 32

# Organizers (Telegram User IDs)
ORGANIZER_TELEGRAM_IDS=123456789,987654321

# OpenRouter API (для clustering)
OPENROUTER_API_KEY=<your-key>
OPENROUTER_BASE_URL=http://xray:8080/v1  # Через Xray proxy на Edge VM

# Telegram Bot
BOT_TOKEN=<your-bot-token>
TELEGRAM_WEBHOOK_URL=https://team10.camp.aitalenthub.ru/api/v1/telegram/webhook
```

### 3. Создать Traefik network (если не создана)

```bash
docker network create traefik-public
```

### 4. Запустить сервисы

```bash
# Build и запуск в production режиме
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build

# Проверить статус
docker compose -f docker-compose.prod.yml ps

# Проверить логи
docker compose -f docker-compose.prod.yml logs -f
```

### 5. Инициализация базы данных

```bash
# Запустить миграции
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# (Опционально) Загрузить seed data для тестирования
docker compose -f docker-compose.prod.yml exec backend python -m app.scripts.seed
```

### 6. Проверка deployment

```bash
# Health check
curl https://team10.camp.aitalenthub.ru/health

# API health check
curl https://team10.camp.aitalenthub.ru/api/v1/health

# Проверить логи
docker compose -f docker-compose.prod.yml logs frontend
docker compose -f docker-compose.prod.yml logs backend
docker compose -f docker-compose.prod.yml logs db
```

### 7. Telegram Bot webhook

```bash
# Установить webhook для бота (после деплоя)
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://team10.camp.aitalenthub.ru/api/v1/telegram/webhook"}'

# Проверить webhook
curl "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo"
```

## Maintenance

### Обновление кода

```bash
cd ~/demoday-ai

# Остановить сервисы
docker compose -f docker-compose.prod.yml down

# Обновить код
git pull

# Пересобрать и запустить
docker compose -f docker-compose.prod.yml up -d --build

# Применить миграции (если есть новые)
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### Просмотр логов

```bash
# Все логи
docker compose -f docker-compose.prod.yml logs -f

# Конкретный сервис
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f frontend
```

### Backup базы данных

```bash
# Создать backup
docker compose -f docker-compose.prod.yml exec db pg_dump -U demoday demoday > backup_$(date +%Y%m%d_%H%M%S).sql

# Восстановить backup
docker compose -f docker-compose.prod.yml exec -T db psql -U demoday demoday < backup_20260203_120000.sql
```

### Restart сервисов

```bash
# Restart всех сервисов
docker compose -f docker-compose.prod.yml restart

# Restart конкретного сервиса
docker compose -f docker-compose.prod.yml restart backend
```

## Monitoring

### Health Checks

- Frontend: `https://team10.camp.aitalenthub.ru/health`
- Backend API: `https://team10.camp.aitalenthub.ru/api/v1/health`
- Database: проверяется автоматически через Docker healthcheck

### Resource Usage

```bash
# CPU/Memory usage
docker stats

# Disk usage
df -h
docker system df
```

## Troubleshooting

### Frontend не отвечает

```bash
# Проверить статус
docker compose -f docker-compose.prod.yml ps frontend

# Проверить логи
docker compose -f docker-compose.prod.yml logs frontend

# Restart
docker compose -f docker-compose.prod.yml restart frontend
```

### Backend errors

```bash
# Проверить логи
docker compose -f docker-compose.prod.yml logs backend

# Проверить database connection
docker compose -f docker-compose.prod.yml exec backend python -c "from app.database import engine; print(engine.url)"

# Проверить миграции
docker compose -f docker-compose.prod.yml exec backend alembic current
```

### Database issues

```bash
# Проверить статус
docker compose -f docker-compose.prod.yml ps db

# Подключиться к DB
docker compose -f docker-compose.prod.yml exec db psql -U demoday demoday

# Проверить размер БД
docker compose -f docker-compose.prod.yml exec db psql -U demoday -c "\l+"
```

## Security Notes

1. **Не коммитить** `.env.prod` и `backend/.env` в git
2. Использовать **сильные пароли** для POSTGRES_PASSWORD и SECRET_KEY
3. Ограничить ORGANIZER_TELEGRAM_IDS только реальными организаторами
4. Регулярно делать **backup** базы данных
5. Мониторить **логи** на подозрительную активность

## Architecture

```
Internet → Traefik (Edge VM) → Frontend (nginx) → Backend (FastAPI) → PostgreSQL
                                      ↓
                                  Static files
```

- **Traefik**: HTTPS termination, routing, Let's Encrypt certificates
- **Frontend**: React SPA + nginx (proxy /api/ to backend)
- **Backend**: FastAPI + SQLAlchemy + Alembic
- **Database**: PostgreSQL 16

## Useful Links

- Team VM: `team10.camp.aitalenthub.ru`
- Bastion: `bastion.camp.aitalenthub.ru`
- Repository: https://github.com/AI-Talent-Camp-2026/demoday-ai
- Infrastructure: https://github.com/AI-Talent-Camp-2026/ai-talent-camp-2026-infra
