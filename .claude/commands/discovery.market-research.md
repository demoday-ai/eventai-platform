---
description: "Deep Market Research: глубокий анализ рынка и конкурентов."
handoffs:
  - label: Personas
    agent: discovery.personas
    prompt: Создай персоны пользователей
    send: true
  - label: Persona Interview
    agent: discovery.interview
    prompt: Проведи симуляцию интервью с персоной
---

## User Input

```text
$ARGUMENTS
```

## Outline

Ты запускаешь скилл **Market Research** из Discovery Kit.

1. **Загрузи агента**: прочитай файл `docs/discovery-kit/01-agents/01-discovery-agents/30-idea-challenger.md` и прими его идентичность, ценности и стиль общения.

2. **Загрузи скилл**: прочитай файл `docs/discovery-kit/02-skills/01-discovery-skills/32-market-research.md` и следуй его процессу.

3. **Контекст**: загрузи `docs/02-specification/01-brief.md` и `docs/02-specification/05-lean-canvas.md` (если существует). Если `$ARGUMENTS` не пуст, учти дополнительные указания.

4. **Выходной артефакт**: сохрани результат в `docs/02-specification/market-research.md`.

5. **После завершения**: сообщи путь к файлу и предложи следующий шаг — Personas (`/discovery.personas`).
