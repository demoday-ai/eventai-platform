---
description: "C4 Architecture: создание C4 Context + Container диаграммы в Mermaid."
handoffs:
  - label: ER Diagram
    agent: discovery.er
    prompt: Создай ER-диаграмму
    send: true
  - label: API Inventory
    agent: discovery.api
    prompt: Создай список API endpoints
---

## User Input

```text
$ARGUMENTS
```

## Outline

Ты запускаешь скилл **C4 Diagrams** из Discovery Kit.

1. **Загрузи агента**: прочитай файл `docs/discovery-kit/01-agents/02-solution-design-agents/40-solution-architect.md` и прими его идентичность, ценности и стиль общения.

2. **Загрузи скилл**: прочитай файл `docs/discovery-kit/02-skills/02-solution-design-skills/42-c4-diagrams.md` и следуй его процессу.

3. **Контекст**: загрузи `docs/02-specification/01-brief.md`, `docs/02-specification/02-user-story-map.md`, `docs/02-specification/04-nfr.md` (если существуют). Если `$ARGUMENTS` не пуст, учти дополнительные указания.

4. **Выходной артефакт**: сохрани результат в `docs/02-specification/07-c4-architecture.md`.

5. **После завершения**: сообщи путь к файлу и предложи ER Diagram (`/discovery.er`) или API Inventory (`/discovery.api`).
