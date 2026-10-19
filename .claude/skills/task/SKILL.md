---
name: task
description: Run the project task pipeline for a backlog task (AH-<n>) in alfa-insight — branch, plan, TDD, commits, cleanup, verification, review, manual check, PR into dev. Use when the user types /task "<AH key or description>", e.g. /task "Выполни задачу AH-7".
---

# Task pipeline

Run the pipeline from `CLAUDE.md` → "Task pipeline" for the task in the arguments. `CLAUDE.md` is the source of truth; `docs/PIPELINE.md` is the agent-neutral version of the same steps; this skill is the entry point and the checklist.

## 1. Find the task

- Extract the key `AH-<n>` from the arguments (Russian or English wording, e.g. "Выполни задачу AH-7"). If there is no key, treat the arguments as a free-form task description and ask ONE question (AskUserQuestion) whether to create it in the backlog first.
- Read the task block in `docs/tasks/BACKLOG.md`: epic, day, type, "Зависит от", "Что сделать", "Готово, когда". If Jira MCP is available and the user asked for Jira updates, also read the issue.
- Check "Зависит от": if a dependency is not Done/Review (ask the user if unsure), say so and ask whether to proceed anyway.
- Announce in one line: key, type, branch name.

## 2. Classify the task

| Type | Branch | TDD step |
|---|---|---|
| feat | `feat/AH-<n>-<slug>` | tests for the new behavior first (RED → GREEN) |
| fix | `fix/AH-<n>-<slug>` | failing regression test that reproduces the bug, then fix |
| change existing behavior | `feat/` or `fix/` by meaning | update existing tests to the new spec, then code |
| refactor | `refactor/AH-<n>-<slug>` | no new tests; green before and after |
| contract | `feat/AH-<n>-contract-<slug>` | contract test → every implementation → `docs/CONTRACTS.md` |
| docs / chore | `docs/AH-<n>-<slug>` or `chore/AH-<n>-<slug>` | skip plan and TDD; commit + verification still required |

The type is in the task block ("Тип:"). If it contradicts the description, ask ONE question before doing anything else. Slug: English kebab-case, 2–4 words.

## 3. Checklist

Track these as todos and do them in order. Never skip a stop.

0. Branch: `git switch dev && git pull && git switch -c <prefix>/AH-<n>-<slug>`. If the working tree is dirty, stop and ask what to do with the changes. If the user asked for Jira updates: move the issue to In Progress.
1. Invoke `ecc:plan` with the task text and its "Готово, когда" as acceptance criteria. **STOP for plan approval.** (docs/chore: skip.)
2. Invoke `ecc:tdd-workflow`: RED → GREEN. Backend: `make test`. Frontend logic: Vitest. Pure JSX layout: render test + `npm run build`.
3. Commit.
4. Invoke `ecc:refactor-clean`. Respect: ≤ 500 lines per file, no comments, nothing beyond the plan, no unapproved defaults or fallbacks.
5. Commit if anything changed.
6. Invoke `ecc:verification-loop` with `make check` (ruff, mypy, import-linter, pytest, npm test, npm run build).
7. Commit if verification required fixes.
8. Invoke `ecc:code-review`, apply fixes, run `ecc:verification-loop` again. Check the review list in `docs/PIPELINE.md` (import boundaries, contracts untouched, every Claim has source_ref, no counterparty identifiers, LLM only via the llm service, THIRD_PARTY_NOTICES). **STOP: ask the user for a manual check** of what tests cannot verify (UI, demo flow, card text quality).
9. Commit.
10. **STOP: ask before pushing.** On "yes": `git push -u origin <branch>`, `gh pr create --base dev --title "AH-<n> · <название>"`, description = what was done / how to verify ("Готово, когда" as a checklist) / risks. If the user asked for Jira updates: move the issue to Review and add the PR link as a comment.

## Rules

- Commit messages: natural-language list (`- Добавить ...`), no Claude attribution, never commit to `dev`/`main`.
- Contracts in `shared/contracts` change only through the `contract` type.
- If tests fail at any step, fix before moving on; report honestly if something could not be verified.
- Do not use skills, MCPs or plugins beyond the ECC commands above, Jira MCP for statuses, and `gh`.
