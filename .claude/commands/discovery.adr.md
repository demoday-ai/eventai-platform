---
description: "Architecture Decision Records: фиксация архитектурных решений с обоснованием."
handoffs:
  - label: C4 Architecture
    agent: discovery.c4
    prompt: Создай C4 архитектурную диаграмму
  - label: ER Diagram
    agent: discovery.er
    prompt: Создай ER-диаграмму
---

## User Input

```text
$ARGUMENTS
```

## Outline

Ты запускаешь скилл **ADR (Architecture Decision Records)** из Discovery Kit.

1. **Загрузи агента**: прочитай файл `docs/discovery-kit/01-agents/02-solution-design-agents/40-solution-architect.md` и прими его идентичность, ценности и стиль общения.

2. **Загрузи скилл**: прочитай файл `docs/discovery-kit/02-skills/02-solution-design-skills/44-adr.md` и следуй его процессу.

3. **Контекст**: загрузи все доступные артефакты из `docs/02-specification/`. Если `$ARGUMENTS` не пуст — это описание решения для фиксации.

4. **Выходные артефакты**: сохрани ADR в `docs/02-specification/adr/` (нумерация: `001-*.md`, `002-*.md` и т.д.).

5. **После завершения**: сообщи путь к файлу и предложи следующий шаг.
