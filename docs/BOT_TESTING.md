# Тестирование бота через CLI

Локальный CLI к живому боту: реальные БД, Redis, OpenRouter (deepseek). Без Telegram.

## Префлайт

```bash
cd ~/Desktop/demoday-core
docker compose ps | grep -E 'bot-1|botcli|db'   # должно быть 3 строки Up
```

Если что-то лежит:
```bash
docker compose up -d db bot botcli
```

## Запуск

```bash
cd ~/Desktop/demoday-core
bash scripts/botcli.sh
```

Откроется интерактивный терминал. Пиши команды/сообщения, бот отвечает в реальном времени.

## Что писать в терминале

| Ввод | Действие |
|---|---|
| `/start` | начать диалог |
| `/help`, `/support`, `/rebuild`, `/profile` | команды |
| `Меня интересует NLP` | обычное сообщение боту |
| `@role:guest:student` | клик по inline-кнопке (берётся `@<callback_data>` из вывода) |
| `!state` | текущее FSM состояние |
| `!data` | FSM data |
| `!quit` | выход |

После каждого ответа бота видны его кнопки в формате `[текст] -> @callback_data`. Чтобы "нажать" -- введи `@callback_data`.

## Полный гостевой flow (пример)

```
You: /start
Bot: Привет! ... Выберите роль:
  [Студент] -> @role:guest:student
  [Бизнес-партнёр] -> @role:business
  ...

You: @role:guest:student
Bot: Расскажите о ваших интересах ...

You: NLP, LLM, бизнес-применения, ассистенты
Bot: ... уточняющий вопрос ...

You: чат-боты для поддержки клиентов
Bot: Ваш профиль: ...
  [Все верно] -> @profile:confirm
  [Заново] -> @profile:retry

You: @profile:confirm
Bot: Программа подобрана. #1 ... #2 ...
```

## Роли (callbacks из главного меню)

```
@role:guest:student      студент
@role:guest:applicant    абитуриент
@role:business           бизнес-партнёр
@role:guest:other        другое
@role:shortcut           без онбординга, сразу программа
```

## Если что-то сломалось

```bash
# Логи бота (без шума /health)
docker compose logs bot --tail 100 | grep -vE 'GET /health|aiohttp.access'

# Прямой SQL
docker compose exec db psql -U demoday demoday

# Полная очистка состояния тестового user_id=777 в БД
docker compose exec db psql -U demoday demoday -c "DELETE FROM users WHERE telegram_user_id = '777'"

# Перезапуск бота
docker compose restart bot

# Полный rebuild после изменений в bot/src/
docker compose up -d --build bot botcli
```

## Параллельные сессии для нескольких агентов

`botcli.sh` хардкодит user_id=777, поэтому **одна интерактивная сессия за раз**. Для параллельных тестов используй per-session обёртку:

```bash
bash scripts/botchat.sh agent-1 '/start'
bash scripts/botchat.sh agent-1 '@role:guest:student'
bash scripts/botchat.sh agent-2 '/start'    # независимый user_id, можно параллельно
```

**Правила параллелизма:**
- Разные `<session>` -- полностью изолированы (свой user_id, FSM, /tmp dir). Гонять параллельно = OK.
- Внутри одного `<session>` -- **только последовательно**. `chat.py` использует общие файлы `/tmp/eventai_<session>/{input,output,lock}`. Параллельные `!state` + `!reset` на одном session гарантированно сломают состояние wrapper'а.

`botchat.sh` -- неинтерактивный, шаг = вызов. По умолчанию использует локальный `docker-compose.yml`. Для прод-хоста переопределить: `COMPOSE_FILE=docker-compose.prod.yml bash scripts/botchat.sh ...`.

## Что важно знать

- **Каждый ответ бота = вызов OpenRouter** (deepseek-v3.2, ~3-5 сек). Стоит копейки, не флуди.
- **БД персистентна.** Между запусками сессия user_id=777 копится. Если нужен чистый старт -- DELETE из users (см. выше) или меняй USER_ID в `bot/scripts/cli_bot.py`.
- **Демо данные:** 294 проекта Demo Day, даты сдвинуты на 2027 чтобы slot-фильтр не выкидывал прошлое.
- **Прод сейчас погашен.** Локальный бот один держит polling на проде-токене @demoday_ai_talent_hub_test_bot.
