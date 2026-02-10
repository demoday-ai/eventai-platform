---
description: "Генерация персон: создание детальных портретов целевых пользователей."
handoffs:
  - label: Persona Interview
    agent: discovery.interview
    prompt: Проведи симуляцию интервью с персоной
    send: true
  - label: C4 Architecture
    agent: discovery.c4
    prompt: Создай C4 архитектурную диаграмму
---

## User Input

```text
$ARGUMENTS
```

## Outline

Ты запускаешь скилл **Persona Generation** из Discovery Kit.

1. **Загрузи агента**: прочитай файл `docs/discovery-kit/01-agents/01-discovery-agents/30-idea-challenger.md` и прими его идентичность, ценности и стиль общения.

2. **Загрузи скилл**: прочитай файл `docs/discovery-kit/02-skills/01-discovery-skills/33-persona-generation.md` и следуй его процессу.

3. **Контекст**: загрузи `docs/02-specification/01-brief.md`, `docs/02-specification/02-user-story-map.md` и `docs/02-specification/05-lean-canvas.md` (если существуют). Если `$ARGUMENTS` не пуст, учти дополнительные указания.

4. **Выходные артефакты**: сохрани персоны в `docs/02-specification/personas/` (по одному файлу на персону).

5. **После завершения**: сообщи пути к файлам и предложи Persona Interview (`/discovery.interview`).
