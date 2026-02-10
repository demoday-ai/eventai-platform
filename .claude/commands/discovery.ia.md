---
description: "Information Architecture: проектирование структуры интерфейса, навигации и sitemap."
handoffs:
  - label: Wireframes
    agent: discovery.wireframes
    prompt: Создай wireframes экранов
    send: true
  - label: Validate
    agent: discovery.validate
    prompt: Проверь консистентность всех артефактов
---

## User Input

```text
$ARGUMENTS
```

## Outline

Ты запускаешь скилл **Information Architecture** из Discovery Kit.

1. **Загрузи агента**: прочитай файл `docs/discovery-kit/01-agents/02-solution-design-agents/50-product-designer.md` и прими его идентичность, ценности и стиль общения.

2. **Загрузи скилл**: прочитай файл `docs/discovery-kit/02-skills/02-solution-design-skills/51-information-architecture.md` и следуй его процессу.

3. **Контекст**: загрузи `docs/02-specification/02-user-story-map.md`, `docs/02-specification/03-user-journey-map.md`, `docs/02-specification/personas/` (если существуют). Если `$ARGUMENTS` не пуст, учти дополнительные указания.

4. **Выходной артефакт**: сохрани результат в `docs/02-specification/06-information-architecture.md`.

5. **После завершения**: сообщи путь к файлу и предложи Wireframes (`/discovery.wireframes`).
