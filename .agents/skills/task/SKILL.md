---
name: task
description: Run the Alpha Impact task pipeline from docs/PIPELINE.md — $task takes the user's next task from docs/TEAM.md, $task AH-<n> runs that task (branch, Jira, plan, TDD, checks, review, PR with reviewer), $task Ревью AH-<n> reviews and merges its PR. Use when the user writes $task.
---

Read `docs/PIPELINE.md` in full, then execute it for the text the user wrote after `$task`.

- Empty text means the next task from the user's queue; «Ревью AH-<n>» means the section «Ревью и мерж».
- Where a step differs by agent, use the Codex column.
- Do the steps in order. Stop only at the pipeline's stops: plan, push, merge.
