---
description: "Написание брифа проекта: сбор требований через итеративный диалог с Бизнес-аналитиком."
handoffs:
  - label: User Story Map
    agent: discovery.usm
    prompt: Создай User Story Map на основе брифа
    send: true
  - label: Clarify Spec
    agent: speckit.clarify
    prompt: Уточни спецификацию
---

## User Input

```text
$ARGUMENTS
```

## Outline

Ты запускаешь скилл **Brief Writing** из Discovery Kit.

1. **Загрузи агента**: прочитай файл `docs/discovery-kit/01-agents/01-discovery-agents/10-business-analyst.md` и прими его идентичность, ценности и стиль общения.

2. **Загрузи скилл**: прочитай файл `docs/discovery-kit/02-skills/01-discovery-skills/11-brief-writing.md` и следуй его процессу (Clarification Loop → фазы 1-5).

3. **Контекст проекта**: если `$ARGUMENTS` не пуст, используй его как начальное описание идеи. Если пуст — спроси пользователя описать идею.

4. **Существующие артефакты**: проверь `docs/02-specification/` на наличие уже созданных документов. Используй их как контекст, если релевантно.

5. **Выходной артефакт**: сохрани финальный бриф в `docs/02-specification/01-brief.md`.

6. **После завершения**: сообщи пользователю путь к файлу и предложи следующий шаг — User Story Map (`/discovery.usm`).
