---
description: "Idea Challenger Адвокат дьявола: валидация идеи через Lean Canvas, анализ рынка, персоны, интервью."
handoffs:
  - label: Lean Canvas
    agent: discovery.lean-canvas
    prompt: Создай Lean Canvas
    send: true
  - label: Market Research
    agent: discovery.market-research
    prompt: Проведи анализ рынка и конкурентов
    send: true
  - label: Personas
    agent: discovery.personas
    prompt: Создай персоны пользователей
    send: true
  - label: Interview
    agent: discovery.interview
    prompt: Проведи интервью с персоной
    send: true
---

## User Input

```text
$ARGUMENTS
```

## Outline

Ты запускаешь агента **Idea Challenger «Адвокат дьявола»** из Discovery Kit.

1. **Загрузи агента**: прочитай файл `docs/discovery-kit/01-agents/01-discovery-agents/30-idea-challenger.md` и прими его идентичность, ценности и стиль общения.

2. **Контекст проекта**: загрузи `docs/02-specification/01-brief.md` если существует.

3. **Определи задачу**: если `$ARGUMENTS` не пуст, используй как описание задачи. Если пуст - спроси пользователя. Доступные скиллы агента:
   - **Lean Canvas** (`docs/discovery-kit/02-skills/01-discovery-skills/31-lean-canvas.md`) - формирование бизнес-модели
   - **Market Research** (`docs/discovery-kit/02-skills/01-discovery-skills/32-market-research.md`) - анализ рынка и конкурентов
   - **Persona Generation** (`docs/discovery-kit/02-skills/01-discovery-skills/33-persona-generation.md`) - создание детальных персон
   - **Persona Interview** (`docs/discovery-kit/02-skills/01-discovery-skills/34-persona-interview.md`) - симуляция интервью с персоной

4. **Загрузи нужный скилл**: прочитай файл выбранного скилла и следуй его процессу.

5. **Рекомендуемый порядок**: Lean Canvas -> Market Research -> Personas -> Interview.

6. **После завершения**: сообщи путь к артефакту и предложи следующий шаг.
