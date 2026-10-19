# ECC-SETUP — Everything Claude Code для этого проекта

Используем ECC как плагин Claude Code, но только нужный набор: пайплайн задач, Python, TypeScript/React, тесты, ревью, безопасность. Всё остальное не ставим, чтобы не раздувать контекст и не расходиться в командах между участниками.

## Установка (каждый участник, один раз)

```
/plugin marketplace add https://github.com/affaan-m/ECC
/plugin install ecc@ecc
/ecc:configure-ecc
```

В мастере `configure-ecc` выбирать профиль **core**, затем ограничить набор так:

**Skills (включить):**
`tdd-workflow`, `verification-loop`, `python-patterns`, `python-testing`, `api-design`, `database-migrations`, `postgres-patterns`, `frontend-patterns`, `vite-patterns`, `e2e-testing`, `security-review`, `search-first`

**Agents (включить):**
`planner`, `architect`, `tdd-guide`, `code-reviewer`, `python-reviewer`, `typescript-reviewer`, `database-reviewer`, `security-reviewer`, `refactor-cleaner`, `build-error-resolver`, `doc-updater`

**Commands, которыми пользуемся:**
`/ecc:plan`, `/ecc:tdd-workflow`, `/ecc:refactor-clean`, `/ecc:verification-loop`, `/ecc:code-review`, `/ecc:quality-gate`, `/ecc:python-review`, `/ecc:test-coverage`, `/ecc:security-scan`, `/ecc:checkpoint`, `/ecc:update-docs`

Отключить: всё для Go, Rust, Java, Kotlin, C++, Swift, PHP, Django, Laravel, Spring, HarmonyOS, PyTorch/MLE, multi-* оркестрацию, continuous-learning/instincts, pm2, model-route. Legacy-шимы (`/tdd`, `/verify`, `/e2e`, `/orchestrate`) не включать — в пайплайне используются skill-имена `/ecc:tdd-workflow` и `/ecc:verification-loop`.

Альтернатива без мастера (ручная установка, не совмещать с плагином):
```
./install.sh --profile core --target claude \
  --skills tdd-workflow,verification-loop,python-patterns,python-testing,api-design,database-migrations,postgres-patterns,frontend-patterns,vite-patterns,e2e-testing,security-review,search-first
```

## Rules (плагин их не распространяет — копируем в репозиторий)

```
git clone --depth 1 https://github.com/affaan-m/ECC /tmp/ecc
mkdir -p .claude/rules/ecc
cp -R /tmp/ecc/rules/common .claude/rules/ecc/
cp -R /tmp/ecc/rules/python .claude/rules/ecc/
cp -R /tmp/ecc/rules/typescript .claude/rules/ecc/
```

Копировать целыми директориями. Коммитим `.claude/rules/ecc/` в репозиторий, чтобы у всех четверых были одинаковые правила. Там, где rules ECC противоречат `CLAUDE.md` проекта (например, по комментариям в коде или по формату коммитов), приоритет у `CLAUDE.md`.

## Hooks

Плагин подключает `hooks/hooks.json` сам (Claude Code ≥ 2.1). В `.claude/settings.json` проекта задаём:

```json
{
  "env": {
    "ECC_HOOK_PROFILE": "standard",
    "ECC_DISABLED_HOOKS": "pre:bash:tmux-reminder",
    "ECC_SESSION_START_MAX_CHARS": "6000"
  }
}
```

Не копировать `hooks.json` в `settings.json` вручную — хуки запустятся дважды.

## Память ECC и память проекта

Память проекта — `.claude/memory/` (см. `CLAUDE.md`). Функции ECC `continuous-learning` и `instincts` не включаем: четыре человека и пять дней — ручной `MEMORY.md` надёжнее.

## Проверка установки

```
node scripts/ecc.js doctor          # из клона ECC, если ставили вручную
/ecc:plan "smoke: проверить пайплайн на пустой задаче"
```

План должен появиться в plan mode и остановиться в ожидании подтверждения — это и есть проверка, что команды и хуки на месте.
