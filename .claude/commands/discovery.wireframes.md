---
description: "Wireframes: Unicode-схемы экранов для визуализации UI."
handoffs:
  - label: Validate
    agent: discovery.validate
    prompt: Проверь консистентность всех артефактов
    send: true
  - label: Build Plan
    agent: speckit.plan
    prompt: Создай план реализации
---

## User Input

```text
$ARGUMENTS
```

## Outline

Ты запускаешь скилл **Wireframe Spec** из Discovery Kit.

1. **Загрузи агента**: прочитай файл `docs/discovery-kit/01-agents/02-solution-design-agents/50-product-designer.md` и прими его идентичность, ценности и стиль общения.

2. **Загрузи скилл**: прочитай файл `docs/discovery-kit/02-skills/02-solution-design-skills/52-wireframe-spec.md` и следуй его процессу.

3. **Контекст**: загрузи `docs/02-specification/06-information-architecture.md`, `docs/02-specification/02-user-story-map.md`, `docs/02-specification/personas/` (если существуют). Если `$ARGUMENTS` не пуст — это описание конкретного экрана.

4. **Выходные артефакты**: сохрани wireframes в `docs/02-specification/wireframes/` (по одному файлу на экран).

5. **После завершения**: сообщи пути к файлам и предложи Validate (`/discovery.validate`) или Build Plan (`/speckit.plan`).
