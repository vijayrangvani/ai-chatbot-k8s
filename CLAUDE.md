# Project notes for AI coding assistants (keep under ~50 lines)

## Commands
- Install: `make install` · Run: `make run` · Test: `make test` · Lint/format: `make format`
- Before saying a task is done: `make check` must pass.

## Structure
- `src/app/` application code (`main.py` entry, `config.py` settings from env)
- `tests/` pytest; every new endpoint gets a test
- `docs/decisions.md` record of design decisions

## Rules
- Settings come from env via `app.config.get_settings()`; never hard-code secrets or URLs.
- Small, reviewable changes. Explain non-obvious code with a short comment on WHY.
- Don't add a dependency without saying why it's needed.
