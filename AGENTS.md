# Alpha Impact — rules for coding agents

This file is the single source of rules for every agent: Codex reads it directly, Claude Code and Gemini CLI through the one-line imports in `CLAUDE.md` and `GEMINI.md`. Never add rules to those two files and never restate these rules elsewhere — link here.

Alpha Impact — a service in the Alfa-Business internet bank that turns news and Alfa-Bank research into a personal feed of events that matter to a large company, each explained by the case's six questions with every claim marked fact / bank view / AI and sourced. The feed lives on the main screen (mandatory); the same events also appear next to an operation form when they touch it, and in a browser extension — one API, three containers. Details: `docs/CONCEPT.md`, current state: `docs/SUMMARY.md`. Alfa-Bank hackathon (case «Новостная аналитика для принятия бизнес-решений»). Team of 3, Jira Kanban `KAN` (each issue title starts with its backlog number `AH-<n>`), 5-day deadline. Docs, commits, PRs and Jira: Russian. Code, identifiers and tests: English.

## Where to look

Read what the task needs, not everything up front.

| Need | File |
|---|---|
| Task text and acceptance criteria («Готово, когда») | `docs/BACKLOG.md`, block `AH-<n>` (wins over Jira) |
| How to run any task: steps, stops, checklists, check commands | `docs/PIPELINE.md` |
| Product idea and demo flow | `docs/CONCEPT.md`, `docs/DEMO.md` |
| Services, request flow, layout, security | `docs/ARCHITECTURE.md`, the section you touch |
| Schemas and ports | `backend/shared/contracts/` (code is the source); `docs/CONTRACTS.md` before touching them |
| Team decisions not visible in code | `docs/DECISIONS.md` (rules and index) and every file in `docs/decisions/` |
| Dataset and bank report facts | `docs/DATA.md` |
| Who owns what and in which order | `docs/TEAM.md` |
| Project essence, goals and current state in one page | `docs/SUMMARY.md` |

## Stack (fixed, do not change)

- Backend: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 + Alembic, PostgreSQL 16 + pgvector, httpx, `uv` (`uv.lock` is the lock file), pytest + pytest-asyncio, ruff, mypy (strict for `shared/`), import-linter
- Frontend: React 18 + Vite + TypeScript, npm workspaces, Vitest, Playwright for e2e; browser extension on Manifest V3
- LLM: only models from the case allow-list via `apps/services/llm` (Gemma 4 26B A4B, GLM-5.3-Flash, Qwen3.6 35B A3B, DeepSeek-V4.1-Flash, Qwen3-VL-30B-A3B, Kimi-K2.6). No other model, no external AI service, no agent framework. Exception: embeddings come from a local `multilingual-e5` model inside `apps/services/llm` (the case key has no embedding model); it is used only for `embed`, never for generation, and spends no LLM budget. Daily budget ≈ 500 RUB — every LLM call goes through the gateway's token counter and cache.
- Infra: Docker Compose, GitHub Actions; one command runs everything: `docker compose up -d --build`

## Layout (fixed)

```
backend/                  Python monolith; run uv, pytest and alembic from here; .env lives in the repo root (--env-file ../.env)
  main.py                 composition root: DI container, service registration, gateway router
  apps/services/<name>/   one isolated service per business capability
  shared/                 contracts/ (schemas and ports — the only thing services share), db/, di/, config/
  scripts/ data/ tests/unit/ tests/integration/
frontend/                 npm workspace; run npm from here
  application/            React + Vite mock of Alfa-Business that embeds InsightPanel
  app-plugin/             InsightPanel library + MV3 browser extension
  tests/e2e/              Playwright
docs/                     SUMMARY, CONCEPT, ARCHITECTURE, CONTRACTS, PIPELINE, BACKLOG, TEAM, DEMO, DECISIONS (+ decisions/ per member), DATA, design/ (tokens, principles, screenshots)
```

Paths `apps/…`, `shared/…`, `scripts/…`, `data/…`, `tests/unit`, `tests/integration` in docs are relative to `backend/`; `application/`, `app-plugin/`, `tests/e2e` are relative to `frontend/`.

## Service isolation (hard rule)

- A service imports only its own package, `shared.contracts`, `shared.config`, `shared.db` (not `shared.db.migrations`), `shared.di`, the standard library and third-party packages. Never another service.
- Cross-service calls go through a port (`typing.Protocol`) from `shared/contracts/ports.py`, resolved from the DI container.
- Every service exposes only `register(container)` from its `__init__.py`.
- Tables belong to their service; other services' tables are read only through the owner's port.
- Enforced by import-linter (`backend/pyproject.toml`) through `tests/unit/test_import_boundaries.py`; it stays green.
- Contracts (`shared/contracts`, `docs/CONTRACTS.md`) change only in a task of type `contract`. If your task needs a contract change, stop and tell the user.

## Domain rules that tests must enforce

- `counterparty_context` returns only aggregates: industry class, region, size bucket, share in the client's own flows, confidence. Never identifiers, amounts or products of another company.
- Every claim in an `InsightCard` carries `type ∈ {fact, bank, ai}` and a `source_ref`. A card with an unsourced claim is rejected by the critic.
- A `bank` claim must quote an existing `HouseViewClaim` id; superseded claims are never cited as current.
- `silent: true` is a valid and expected response; the UI shows it explicitly.
- Prompts receive features and aggregates, never raw table rows and never anything from `df_Fid_Uid_link` (persons).
- The agent only reads and computes. No tool mutates bank data or forms.

## Code and tests

- Clean Architecture, SOLID; the simplest solution that satisfies the task — never overcomplicate
- Maximum 500 lines per file; no comments in code
- Implement only what the approved plan says; no defaults or fallbacks without explicit approval
- Unit, integration and e2e tests are required; all tests pass before committing
- No secrets in code: configuration comes from `.env` (never committed; the template is `.env.example`)
- A new dependency needs a line in `THIRD_PARTY_NOTICES.md` and an updated lock file (`uv.lock`, `package-lock.json`)
- Generated files are never edited by hand: `backend/shared/contracts/openapi/*.json` and `frontend/app-plugin/src/types/*.ts` except `index.ts` — regenerate them

## Tools

- Allowed: git, uv, npm and npx, docker compose; `gh` only for the branch and PR operations of the pipeline; `winget` and `docker info` only in `/setup`
- Built-in agent features named in `docs/PIPELINE.md`: Claude Code plan mode, `/simplify`, `/code-review` without flags, `/security-review`
- Entry points: `/task` and `/setup` in Claude Code and Gemini CLI, `$task` and `$setup` in Codex
- Jira via the Atlassian MCP is part of the pipeline (assignee, status, PR link); no MCP → suggest `/setup`
- Everything else — web search, other MCPs, plugins, skills — only on the user's direct request in the current session

## Git

- `main` is production, `dev` is integration. Never commit or push to them, never delete, force-push or rebase them. GitHub does not enforce this on our plan — you are the guard.
- One task = one branch from an up-to-date `dev`: `<prefix>/AH-<n>-<slug>` (prefixes per task type in `docs/PIPELINE.md`). PR into `dev`, title `AH-<n> · <название>`, description in Russian: what was done / how to verify / risks.
- `dev` → `main` only by a release PR on the owner's command; the release commit gets the tag the jury receives.
- Commit only at pipeline steps or when the user asks. Commit messages: Russian natural-language list (`- Добавить …`), no `feat:` or `fix:` prefixes, no `Co-Authored-By`, no agent attribution.
- Never force-push. Merge only in the review mode of `docs/PIPELINE.md` after the reviewer's yes (merge commit). Ask before pushing, deleting another branch or rewriting history.

## Workflow

- Every change follows `docs/PIPELINE.md`, whether the user runs `/task`, `$task` or just describes the task.
- Hard stops: after the plan and before push; in review mode, before merge. Nothing else waits for the user.
- A task is done only when the checks in `docs/PIPELINE.md` are green.
- Checks fail in code outside your task → don't fix it in your branch; stop and tell the user.

## Knowledge

- A new team decision → one dated line appended to your own file in `docs/decisions/` (index: `docs/DECISIONS.md`); never write into another member's file; old lines are never rewritten. A new dataset fact → `docs/DATA.md`.
- Machine-specific notes (ports, local tools) stay in your agent's personal memory outside git: Claude auto-memory or `CLAUDE.local.md`, `~/.codex/AGENTS.md`, `~/.gemini/GEMINI.md`. Never create `AGENTS.override.md`: Codex would ignore this file.

## Definition of done

- Plan approved; tests written first where `docs/PIPELINE.md` requires TDD; the checks are green
- Contracts unchanged, or changed in a `contract` task
- No new dependency without a line in `THIRD_PARTY_NOTICES.md`
- README instructions still work: `docker compose up -d --build` on a clean clone
- PR into `dev` is open with a reviewer; the Jira issue is «В процессе проверки» with the PR link
