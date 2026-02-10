---
description: "Lean Canvas: формирование одностраничной бизнес-модели через конструктивный челлендж."
handoffs:
  - label: Market Research
    agent: discovery.market-research
    prompt: Проведи анализ рынка и конкурентов
    send: true
  - label: Personas
    agent: discovery.personas
    prompt: Создай персоны пользователей
---

## User Input

```text
$ARGUMENTS
```

## Outline

Ты запускаешь скилл **Lean Canvas** из Discovery Kit.

1. **Загрузи агента**: прочитай файл `docs/discovery-kit/01-agents/01-discovery-agents/30-idea-challenger.md` и прими его идентичность, ценности и стиль общения.

2. **Загрузи скилл**: прочитай файл `docs/discovery-kit/02-skills/01-discovery-skills/31-lean-canvas.md` и следуй его процессу.

3. **Контекст**: загрузи `docs/02-specification/01-brief.md` как основной источник. Если `$ARGUMENTS` не пуст, учти дополнительные указания.

4. **Выходной артефакт**: сохрани результат в `docs/02-specification/05-lean-canvas.md`.

5. **После завершения**: сообщи путь к файлу и предложи следующий шаг — Market Research (`/discovery.market-research`).
