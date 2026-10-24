---
name: task
description: Run the Alpha Impact task pipeline from docs/PIPELINE.md — /task takes the user's next task from docs/TEAM.md, /task AH-<n> runs that task (branch, Jira, plan, TDD, checks, review, PR with reviewer), /task Ревью AH-<n> reviews and merges its PR. Use when the user types /task.
argument-hint: "[AH-<n> | Ревью AH-<n> | task description]"
---

Read `docs/PIPELINE.md` in full, then execute it for: $ARGUMENTS

- Empty arguments mean the next task from the user's queue; «Ревью AH-<n>» means the section «Ревью и мерж».
- Where a step differs by agent, use the Claude Code column.
- Track the steps as todos. Stop only at the pipeline's stops: plan, push, merge.
- Step 0 switches branches and cannot run in plan mode: if plan mode is on, write the plan first and do step 0 right after approval.
