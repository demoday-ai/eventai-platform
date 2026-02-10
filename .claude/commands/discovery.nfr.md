---
description: "Сбор нефункциональных требований: Performance, Security, Scalability и другие атрибуты качества."
handoffs:
  - label: Lean Canvas
    agent: discovery.lean-canvas
    prompt: Создай Lean Canvas для валидации бизнес-модели
  - label: C4 Architecture
    agent: discovery.c4
    prompt: Создай C4 архитектурную диаграмму
---

## User Input

```text
$ARGUMENTS
```

## Outline

Ты запускаешь скилл **NFR Collection** из Discovery Kit.

1. **Загрузи агента**: прочитай файл `docs/discovery-kit/01-agents/01-discovery-agents/20-system-analyst.md` и прими его идентичность, ценности и стиль общения.

2. **Загрузи скилл**: прочитай файл `docs/discovery-kit/02-skills/01-discovery-skills/21-nfr-collection.md` и следуй его процессу.

3. **Контекст**: загрузи `docs/02-specification/01-brief.md` и `docs/02-specification/02-user-story-map.md`. Если `$ARGUMENTS` не пуст, учти дополнительные указания.

4. **Выходной артефакт**: сохрани результат в `docs/02-specification/04-nfr.md`.

5. **После завершения**: сообщи путь к файлу и предложи следующий шаг.
