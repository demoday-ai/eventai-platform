# AI Talent Camp 2026 -- Команда "ЯСНОПОНЯТНО"

## Команда

- **Дмитрий Горбунов** (@grbn_dima) -- хастлер/хипстер. Тимлид, бизнес, продукт, UX/UI
- **Анастасия Гапеева** -- хипстер/хакер. UX/UI, фронтенд, разработка
- **Иван Александров** -- хакер/хастлер. Разработка, техническая реализация, бизнес-логика

## Я -- Claude (ассистент команды)

Я полноценный участник команды. Подключён к групповому чату "ЯСНОПОНЯТНО" в Telegram через бота @ai_talent_camp_gorbunov_bot.

### Как я работаю с чатом

- **Бот** (`demoday-core/telegram-log/bot.py`) работает в фоне и логирует все сообщения в `messages.json`
- Когда кто-то пишет `@ai_talent_camp_gorbunov_bot` -- сообщение попадает ещё и в `pending.json`
- Дмитрий говорит мне "проверь чат" -- я читаю логи и отвечаю
- Отправляю сообщения через `python send.py "текст"` или `python send.py "текст" --reply-to <ID>`
- Все файлы бота: `demoday-core/telegram-log/`

### Что я умею для команды

- Писать и отлаживать код
- Проектировать архитектуру
- Работать с Terraform-инфраструктурой проекта
- Отвечать на вопросы коллег в чате
- Проводить code review

## Проект: AI Talent Camp Infrastructure

Terraform-инфраструктура для AI-хакатона на Yandex Cloud.

**Репозиторий:** `ai-talent-camp-2026-infra/`

### Архитектура

- **Edge/NAT VM** (2 vCPU, 4GB RAM) -- единственная точка входа с публичным IP
  - Traefik (Docker) -- reverse proxy, TLS passthrough
  - Xray (systemd) -- прозрачное проксирование AI API через TPROXY
  - NAT (iptables) -- маршрутизация обычного трафика
- **Team VMs** (4 vCPU, 8GB RAM, 65GB SSD) -- по одной на команду, в private subnet
- **Домены:** `teamXX.camp.aitalenthub.ru`

### Сеть

- Public subnet: `192.168.1.0/24` (Edge VM)
- Private subnet: `10.20.0.0/24` (Team VMs)
- Весь исходящий трафик из private subnet идёт через Edge VM
- AI API трафик прозрачно проксируется через Xray

### Terraform-модули

| Модуль | Назначение |
|--------|-----------|
| `network` | VPC и подсети |
| `security` | Security groups |
| `routing` | Route tables |
| `edge` | Edge/NAT VM |
| `team_vm` | VM для команд |
| `team-credentials` | SSH ключи |
| `config-sync` | Синхронизация конфигов |

### Стек

- Terraform + Yandex Cloud
- Ubuntu 22.04 LTS
- Traefik v3.0 (Docker)
- Xray (systemd, TPROXY)
- cloud-init для автоматизации

## Структура репозиториев

```
AI Talent Camp/
├── ai-talent-camp-2026-infra/    # Terraform IaC (git)
│   ├── modules/                  # 7 Terraform-модулей
│   ├── environments/dev/         # Dev-окружение
│   ├── templates/                # Traefik, Xray, SSH шаблоны
│   ├── docs/                     # Документация
│   └── secrets/                  # SSH ключи (gitignored)
│
└── demoday-core/                 # Основной проект команды (git)
    └── telegram-log/             # Telegram-бот для связи с Claude
        ├── bot.py                # Логирование сообщений
        ├── send.py               # Отправка сообщений в чат
        ├── messages.json         # Лог сообщений
        ├── pending.json          # Вопросы с @mention
        └── .env                  # BOT_TOKEN
```

## Рабочие соглашения

- Основной язык общения: русский
- Чат команды: Telegram, группа "ЯСНОПОНЯТНО"
- Триггер для Claude в чате: `@ai_talent_camp_gorbunov_bot`
- Бот должен быть запущен на ПК Дмитрия (`python bot.py`)
