---
description: "Artifact Validator: проверка консистентности всех discovery-артефактов перед передачей в разработку."
handoffs:
  - label: Build Plan
    agent: speckit.plan
    prompt: Создай план реализации
  - label: Create Spec
    agent: speckit.specify
    prompt: Создай спецификацию для разработки
---

## User Input

```text
$ARGUMENTS
```

## Outline

Ты запускаешь скилл **Artifact Validator** из Discovery Kit.

1. **Загрузи скилл**: прочитай файл `docs/discovery-kit/02-skills/02-solution-design-skills/61-artifact-validator.md` и следуй его процессу. Этот скилл — standalone, без агента.

2. **Загрузи все артефакты**: прочитай все файлы из `docs/02-specification/` (включая подпапки `personas/`, `wireframes/`, `adr/`, `interview-reports/`).

3. **Выполни валидацию**: проверь консистентность между артефактами по процессу из скилла.

4. **Выходной артефакт**: сохрани отчёт валидации в `docs/02-specification/11-validation-report.md`.

5. **После завершения**: сообщи результаты и предложи исправления, если найдены несоответствия. Если всё ок — предложи перейти к разработке (`/speckit.plan`).
