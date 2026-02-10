---
description: "API Inventory: список всех API endpoints с описанием."
handoffs:
  - label: Sequence Diagrams
    agent: discovery.sequences
    prompt: Создай диаграммы взаимодействий
  - label: Information Architecture
    agent: discovery.ia
    prompt: Спроектируй информационную архитектуру
---

## User Input

```text
$ARGUMENTS
```

## Outline

Ты запускаешь скилл **API Inventory** из Discovery Kit.

1. **Загрузи агента**: прочитай файл `docs/discovery-kit/01-agents/02-solution-design-agents/40-solution-architect.md` и прими его идентичность, ценности и стиль общения.

2. **Загрузи скилл**: прочитай файл `docs/discovery-kit/02-skills/02-solution-design-skills/47-api-inventory.md` и следуй его процессу.

3. **Контекст**: загрузи `docs/02-specification/02-user-story-map.md`, `docs/02-specification/07-c4-architecture.md`, `docs/02-specification/08-er-diagram.md` (если существуют). Если `$ARGUMENTS` не пуст, учти дополнительные указания.

4. **Выходной артефакт**: сохрани результат в `docs/02-specification/10-api-inventory.md`.

5. **После завершения**: сообщи путь к файлу и предложи следующий шаг.
