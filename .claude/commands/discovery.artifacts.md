---
description: "Рекомендация артефактов: определение, какие технические документы нужны проекту."
handoffs:
  - label: C4 Architecture
    agent: discovery.c4
    prompt: Создай C4 архитектурную диаграмму
    send: true
  - label: Tech Research
    agent: discovery.tech-research
    prompt: Проведи исследование технологий
---

## User Input

```text
$ARGUMENTS
```

## Outline

Ты запускаешь скилл **Artifact Recommendation** из Discovery Kit.

1. **Загрузи агента**: прочитай файл `docs/discovery-kit/01-agents/02-solution-design-agents/40-solution-architect.md` и прими его идентичность, ценности и стиль общения.

2. **Загрузи скилл**: прочитай файл `docs/discovery-kit/02-skills/02-solution-design-skills/41-artifact-recommendation.md` и следуй его процессу.

3. **Контекст**: загрузи все доступные артефакты из `docs/02-specification/`. Если `$ARGUMENTS` не пуст, учти дополнительные указания.

4. **Выходной артефакт**: сохрани рекомендации в `docs/02-specification/artifact-recommendations.md`.

5. **После завершения**: сообщи путь к файлу и предложи конкретные следующие шаги из рекомендаций.
