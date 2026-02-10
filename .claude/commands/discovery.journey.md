---
description: "Создание User Journey Map: визуализация пути пользователя в Mermaid."
handoffs:
  - label: NFR
    agent: discovery.nfr
    prompt: Собери нефункциональные требования
  - label: Lean Canvas
    agent: discovery.lean-canvas
    prompt: Создай Lean Canvas
---

## User Input

```text
$ARGUMENTS
```

## Outline

Ты запускаешь скилл **User Journey Map** из Discovery Kit.

1. **Загрузи агента**: прочитай файл `docs/discovery-kit/01-agents/01-discovery-agents/10-business-analyst.md` и прими его идентичность, ценности и стиль общения.

2. **Загрузи скилл**: прочитай файл `docs/discovery-kit/02-skills/01-discovery-skills/13-user-journey-map.md` и следуй его процессу.

3. **Контекст**: загрузи `docs/02-specification/01-brief.md` и `docs/02-specification/02-user-story-map.md` как источники. Если `$ARGUMENTS` не пуст, учти дополнительные указания.

4. **Выходной артефакт**: сохрани результат в `docs/02-specification/03-user-journey-map.md`.

5. **После завершения**: сообщи путь к файлу и предложи следующий шаг — NFR (`/discovery.nfr`).
