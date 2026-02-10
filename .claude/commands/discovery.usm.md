---
description: "Создание User Story Map: карта пользовательских сценариев на основе брифа."
handoffs:
  - label: User Journey Map
    agent: discovery.journey
    prompt: Создай User Journey Map на основе USM
    send: true
  - label: NFR
    agent: discovery.nfr
    prompt: Собери нефункциональные требования
---

## User Input

```text
$ARGUMENTS
```

## Outline

Ты запускаешь скилл **User Story Mapping** из Discovery Kit.

1. **Загрузи агента**: прочитай файл `docs/discovery-kit/01-agents/01-discovery-agents/10-business-analyst.md` и прими его идентичность, ценности и стиль общения.

2. **Загрузи скилл**: прочитай файл `docs/discovery-kit/02-skills/01-discovery-skills/12-user-story-mapping.md` и следуй его процессу.

3. **Контекст**: загрузи `docs/02-specification/01-brief.md` как основной источник. Если `$ARGUMENTS` не пуст, учти дополнительные указания.

4. **Существующие артефакты**: проверь `docs/02-specification/` на наличие других документов для контекста.

5. **Выходной артефакт**: сохрани результат в `docs/02-specification/02-user-story-map.md`.

6. **После завершения**: сообщи путь к файлу и предложи следующий шаг — User Journey Map (`/discovery.journey`) или NFR (`/discovery.nfr`).
