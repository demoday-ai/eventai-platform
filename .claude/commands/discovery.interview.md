---
description: "Симуляция CustDev-интервью: валидация идеи через интервью с персоной."
handoffs:
  - label: C4 Architecture
    agent: discovery.c4
    prompt: Создай C4 архитектурную диаграмму
  - label: Artifact Recommendation
    agent: discovery.artifacts
    prompt: Определи нужные технические артефакты
---

## User Input

```text
$ARGUMENTS
```

## Outline

Ты запускаешь скилл **Persona Interview** из Discovery Kit.

1. **Загрузи агента**: прочитай файл `docs/discovery-kit/01-agents/01-discovery-agents/30-idea-challenger.md` и прими его идентичность, ценности и стиль общения.

2. **Загрузи скилл**: прочитай файл `docs/discovery-kit/02-skills/01-discovery-skills/34-persona-interview.md` и следуй его процессу.

3. **Контекст**: загрузи персоны из `docs/02-specification/personas/`, а также `docs/02-specification/01-brief.md` и другие доступные артефакты. Если `$ARGUMENTS` не пуст — это имя или описание персоны для интервью.

4. **Выходной артефакт**: сохрани отчёт в `docs/02-specification/interview-reports/`.

5. **После завершения**: сообщи путь к файлу и предложи следующий шаг.
