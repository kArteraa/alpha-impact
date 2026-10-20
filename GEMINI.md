# Project Instructions (GEMINI.md — mirror of CLAUDE.md for Gemini CLI)

Project: **alfa-insight** — "Аналитика в момент действия" for Alfa-Bank hackathon (case "Новостная аналитика для принятия бизнес-решений").
Read `docs/CONCEPT.md`, `docs/ARCHITECTURE.md`, `docs/CONTRACTS.md` before any task. The single backlog is `docs/tasks/BACKLOG.md`; who does what and in which order is `docs/TEAM.md`; the agent-neutral pipeline with checklists is `docs/PIPELINE.md`. This file is mirrored in `AGENTS.md` (Codex) and `GEMINI.md` (Gemini CLI) — change all three together.
Team: 4 people, Jira Kanban (project key `AH`), 5-day deadline. Language of docs, commits and Jira: Russian. Language of code, identifiers and tests: English.

## Development Workflow

- Enter plan mode before any action: new feature, bugfix, debugging
- Never implement functionality that wasn't explicitly planned
- Never stop until feature/fix is verified done by tests
- Commit only after task is verified by tests
- Review written code at each checkpoint

## Code Quality

- Clean Architecture, SOLID principles
- Maximum 500 lines per file
- No comments in code
- Simplest solution that satisfies requirements — never overcomplicate

## Testing

- Unit, integration, and e2e tests required
- All tests must pass before committing

## Git

- Natural language commit messages, simple lists
- No feat:, fix:, or conventional commit prefixes
- No Co-Authored-By lines

## Restrictions

- Do not use skills, MCPs, or plugins unless explicitly asked
- Do not add functionality beyond what was planned
- Do not add defaults or fallbacks without explicit approval

The explicit allow-list for this project (counts as "explicitly asked"):
- the `/task` command; there is no ECC for Gemini — steps 2, 4, 6, 8 are done by hand with the checklists in `docs/PIPELINE.md`
- GitHub CLI `gh` — only for branch, PR and branch-protection operations named in a plan step
Everything else (web search, other MCPs, other plugins) requires a direct request from the user in the current session.

## Stack (fixed, do not change)

- Backend: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 + Alembic, PostgreSQL 16 + pgvector, httpx, `uv` for dependencies (`uv.lock` is the lock file), pytest + pytest-asyncio, ruff, mypy (strict for `shared/`)
- Frontend: React 18 + Vite + TypeScript, npm workspaces, Vitest, Playwright for e2e; browser extension on Manifest V3
- LLM: only models from the case allow-list via `apps/services/llm` (Gemma 4 26B A4B, GLM-5.3-Flash, Qwen3.6 35B A3B, DeepSeek-V4.1-Flash, Qwen3-VL-30B-A3B, Kimi-K2.6). No other model, no external AI service, no agent framework. Daily budget ≈ 500 RUB — every LLM call goes through the gateway's token counter and cache.
- Infra: Docker Compose, GitHub Actions, one command to run everything (`make up`)

## Project structure (fixed)

```
backend/                     Python monolith; run uv, pytest and alembic from this folder
  main.py                    composition root: builds the DI container, registers every service by its contract, mounts the gateway router
  apps/services/<name>/      one isolated service per business capability (see docs/ARCHITECTURE.md)
  shared/
    contracts/               Pydantic schemas and `typing.Protocol` ports — the ONLY thing services may import from each other
    db/                      SQLAlchemy engine, session factory, Alembic migrations, table models
    di/                      DI container, registration helpers
    config/                  pydantic-settings, env parsing
  scripts/ data/ tests/unit tests/integration
frontend/                    npm workspace; run npm from this folder
  application/               React + Vite: mock of Alfa-Business (main screen, payment, deposit, loan) that embeds InsightPanel
  app-plugin/                React + Vite: InsightPanel library + browser extension (MV3) built from the same component
  tests/e2e/                 Playwright
docs/                        CONCEPT, ARCHITECTURE, CONTRACTS, PIPELINE, TEAM, ECC-SETUP, DEMO, tasks/BACKLOG
```

Paths `apps/…`, `shared/…`, `scripts/…`, `data/…`, `tests/unit`, `tests/integration` in docs and the backlog are relative to `backend/`; `application/`, `app-plugin/`, `tests/e2e` are relative to `frontend/`.

## Service isolation (hard rule)

- A service may import only its own package, `shared.contracts`, `shared.config`, `shared.db` (for its own repositories) and the standard library / third-party packages.
- A service never imports another service. Cross-service calls go through a port (`typing.Protocol`) from `shared/contracts/ports.py`, resolved from the DI container.
- Every service exposes `register(container)` in its `__init__.py` and nothing else public.
- Changing a contract is a separate task: update `shared/contracts`, update every implementation, update `docs/CONTRACTS.md`, add a contract test in `tests/integration/contracts/`.
- Import rules are enforced by `tests/unit/test_import_boundaries.py` (grimp/import-linter); the test must stay green.

## Domain rules that tests must enforce

- `counterparty_context` returns only aggregates: industry class, region, size bucket, share in the client's own flows, confidence. Never identifiers, amounts or products of another company.
- Every claim in an `InsightCard` carries `type ∈ {fact, bank, ai}` and a `source_ref`. A card with an unsourced claim is rejected by the critic.
- A `bank` claim must quote an existing `HouseViewClaim` id; superseded claims are never cited as current.
- `silent: true` is a valid and expected response; the UI shows it explicitly.
- Prompts receive features and aggregates, never raw table rows and never anything from `df_Fid_Uid_link` (persons).
- The agent only reads and computes. No tool mutates bank data or forms.

## Task pipeline (mandatory for every task in this project)

The user starts a task with `/task Выполни задачу AH-<n>` (command in `.gemini/commands/task.toml`) or just describes it — either way follow this pipeline. The task text and its acceptance criteria ("Готово, когда") come from `docs/tasks/BACKLOG.md`.

**Task types** (infer from the description; if unclear, ask one question before creating the branch):

| Type | Branch | Step 2 (TDD) |
|---|---|---|
| New feature | `feat/AH-<n>-<name>` | write tests for the new behavior (RED), then implement (GREEN) |
| Bug | `fix/AH-<n>-<name>` | first a regression test that reproduces the bug and fails, then the fix |
| Change existing behavior | `feat/` or `fix/` by meaning | update existing tests to the new spec first, then change the code |
| Refactor | `refactor/AH-<n>-<name>` | no new tests; suite is green before and after, behavior unchanged |
| Contract change | `feat/AH-<n>-contract-<name>` | contract test first, then every implementation |
| Docs / config only | `docs/…` or `chore/…` | skip TDD; still commit + verification |

TDD applies to services, `shared/` and front-end logic (hooks, state, API client). For pure JSX layout, step 2 is: Vitest render test + `npm run build` green.

**Steps:**
0. Branch from an up-to-date `dev` (`git switch dev && git pull && git switch -c <prefix>/AH-<n>-<name>`). Jira status is moved by the human in the Kanban.
1. Write the plan (files, tests, contracts, risks, acceptance criteria). **Stop — wait for the user to approve the plan.**
2. TDD by hand: tests first, show them failing, then implement until green.
3. Commit.
4. Cleanup by the checklist in `docs/PIPELINE.md`.
5. Commit (skip if nothing changed).
6. Verification: `make check` (ruff + mypy + import-linter + pytest + npm test + npm run build) until green.
7. Commit (only if verification required fixes).
8. Review by the checklist in `docs/PIPELINE.md` → apply fixes → `make check` again. **Stop — ask the user for a manual check** of anything a test cannot verify (UI feel, demo flow, LLM output quality).
9. Commit.
10. **Stop — ask before pushing.** On "yes": push the branch and open a PR into `dev` with the Jira key in the title; the human moves the Jira task to "Review".

Commit messages: natural-language list format, never agent attribution.

## Git

- **Never add `Co-Authored-By` trailers or any agent attribution to commits or PR descriptions.** The commit author is the user only.
- `main` and `dev` are protected — never commit or push to them directly. Each task gets its own branch from an up-to-date `dev` (`feat/…`, `fix/…`, `refactor/…`, `test/…`, `docs/…`, `chore/…`), PRs go into `dev`. `dev` → `main` only by a release PR before the deadline; the release commit gets the tag the jury receives.
- Commit only when the user asks or a plan step says so.
- Branch and PR titles start with the Jira key (`AH-12`).

## Persistent Memory

Project memory lives in the repo at `.claude/memory/` (committed, travels across machines; Codex and Gemini users read the same folder). At the start of a session read `.claude/memory/MEMORY.md` — the index. Each memory file has YAML frontmatter (`name`, `description`, `metadata.type` ∈ {project, feedback, reference, user}); `feedback`/`project` bodies end with `**Why:**` and `**How to apply:**` lines. Don't store what code or git history already records.

## Definition of done for any task

- Plan approved, tests written first, `make check` green
- Contract unchanged, or changed through the contract-change pipeline
- No new dependency without a line in `THIRD_PARTY_NOTICES.md`
- README run instructions still valid (`make up` from a clean clone)
- Jira task has the PR link in a comment (when Jira updates were requested)
