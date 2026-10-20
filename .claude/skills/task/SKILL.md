---
name: task
description: Run the Alpha Impact task pipeline from docs/PIPELINE.md for a backlog task AH-<n> or a free-form task description — task and branch, plan, TDD, cleanup, checks, review, manual check, PR into dev. Use when the user types /task, e.g. /task Выполни задачу AH-7.
argument-hint: AH-<n> or task description
---

Read `docs/PIPELINE.md` in full, then execute it for: $ARGUMENTS

- Where a step differs by agent, use the Claude Code column.
- Track steps 0–10 as todos and never skip a stop.
- Step 0 switches branches and cannot run in plan mode: if plan mode is on, write the plan first and do step 0 right after approval.
