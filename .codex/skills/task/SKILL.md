---
name: task
description: Run the project task pipeline for a backlog task (AH-<n>) in alfa-insight — branch, plan, TDD, commits, cleanup, verification, review, manual check, PR into dev. Use when the user writes $task followed by an AH key or a task description, e.g. $task Выполни задачу AH-10.
---

# Task pipeline

Run the pipeline from `AGENTS.md` → "Task pipeline" for the task in the arguments. `AGENTS.md` is the source of truth (it mirrors `CLAUDE.md`); `docs/PIPELINE.md` holds the same steps with checklists; this skill is the entry point.

## 1. Find the task

- Extract the key `AH-<n>` from the arguments (e.g. "Выполни задачу AH-10"). No key → treat the text as a free-form description and ask ONE question whether to add it to the backlog first.
- Read the task block in `docs/tasks/BACKLOG.md`: epic, day, type, "Зависит от", "Что сделать", "Готово, когда".
- Check "Зависит от"; if a dependency is not done, say so and ask whether to proceed.
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

The type is in the task block. If it contradicts the description, ask ONE question first. Slug: English kebab-case, 2–4 words.

## 3. Checklist

Do these in order. Never skip a stop.

0. Branch: `git switch dev && git pull && git switch -c <prefix>/AH-<n>-<slug>`. Dirty working tree → stop and ask.
1. Plan: list files to touch, tests to write, contracts involved, risks, and the acceptance criteria from "Готово, когда". **STOP and wait for approval.** (docs/chore: skip.)
2. TDD: write the tests first and show them failing (`make test` / Vitest), then implement until green. Pure JSX layout: render test + `npm run build`.
3. Commit.
4. Cleanup by the checklist in `docs/PIPELINE.md`: ≤ 500 lines per file, no comments, nothing beyond the plan, no unapproved defaults or fallbacks, no duplication across services.
5. Commit if anything changed.
6. Verification: run `make check` (ruff, mypy, import-linter, pytest, npm test, npm run build) and fix until green.
7. Commit if verification required fixes.
8. Review by the checklist in `docs/PIPELINE.md` (import boundaries, contracts untouched, every Claim has source_ref, no counterparty identifiers, LLM only via the llm service, THIRD_PARTY_NOTICES); apply fixes; `make check` again. **STOP: ask the user for a manual check** of what tests cannot verify.
9. Commit.
10. **STOP: ask before pushing.** On "yes": `git push -u origin <branch>`, `gh pr create --base dev --title "AH-<n> · <название>"`, description = what was done / how to verify ("Готово, когда" as a checklist) / risks.

## Rules

- Commit messages: natural-language list (`- Добавить ...`), no agent attribution, never commit to `dev`/`main`.
- Contracts in `shared/contracts` change only through the `contract` type.
- If tests fail at any step, fix before moving on; report honestly if something could not be verified.
- No tools beyond git, gh, make, uv, npm unless the user asks.
