---
name: task
description: Run the Alpha Impact task pipeline from docs/PIPELINE.md for a backlog task AH-<n> or a free-form task description — task and branch, plan, TDD, cleanup, checks, review, manual check, PR into dev. Use when the user writes $task, e.g. $task Выполни задачу AH-7.
---

Read `docs/PIPELINE.md` in full, then execute it for the text the user wrote after `$task`.

- Where a step differs by agent, use the Codex column.
- Do the steps in order and never skip a stop.
