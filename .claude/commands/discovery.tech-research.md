---
description: "Deep Tech Research: глубокое исследование технологий для обоснованного выбора стека."
handoffs:
  - label: ADR
    agent: discovery.adr
    prompt: Зафиксируй решения в ADR
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

Ты запускаешь скилл **Tech Research** из Discovery Kit.

1. **Загрузи агента**: прочитай файл `docs/discovery-kit/01-agents/02-solution-design-agents/40-solution-architect.md` и прими его идентичность, ценности и стиль общения.

2. **Загрузи скилл**: прочитай файл `docs/discovery-kit/02-skills/02-solution-design-skills/43-tech-research.md` и следуй его процессу.

3. **Контекст**: загрузи все доступные артефакты из `docs/02-specification/`. Если `$ARGUMENTS` не пуст — это тема/вопрос для исследования.

4. **Выходной артефакт**: сохрани результат в `docs/02-specification/tech-research.md`.

5. **После завершения**: сообщи путь к файлу и предложи ADR (`/discovery.adr`).
