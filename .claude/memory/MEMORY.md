---
name: memory-index
description: Индекс памяти проекта alfa-insight. Читать в начале каждой сессии.
metadata:
  type: reference
---

# MEMORY

Память проекта хранится здесь и коммитится. Один файл — одна тема. Не дублировать то, что уже есть в коде, git-истории, `CLAUDE.md` или `docs/`.

| Файл | Тип | О чём |
|---|---|---|
| `project-decisions.md` | project | Решения, принятые командой, которых нет в docs (с датой) |
| `feedback-pipeline.md` | feedback | Что пошло не так в пайплайне задач и как это учитывать |
| `reference-data.md` | reference | Факты о датасете и отчётах банка, которые постоянно нужны |

## Формат файла

```
---
name: <slug>
description: <одна строка>
metadata:
  type: project | feedback | reference | user
---

<тело>

**Why:** <почему это важно>          ← обязательно для project и feedback
**How to apply:** <как применять>    ← обязательно для project и feedback
```
