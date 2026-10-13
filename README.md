# Project name

> One sentence: what this does and for whom.

<!-- Demo GIF or screenshot here. Recruiters look at this first. -->

## Problem
What real problem does this solve? Who has it? Why do existing approaches fall short?

## Architecture
```
client -> FastAPI -> (DB / LLM / queue ...)
```
Short explanation of each component and how a request flows through.

## Tech stack
| Layer | Choice | Why |
|---|---|---|
| API | FastAPI | |
| ... | | |

## Run locally
```bash
python -m venv .venv && source .venv/bin/activate
cp .env.example .env
make install
make run          # http://localhost:8000/docs
make test
```

## Not building an API?
This starter defaults to FastAPI because most AI projects end up served behind an API. For a CLI tool, data pipeline, batch job or notebook-style project, keep everything else (tests, lint, CI, pre-commit, docs) and change 4 things:

1. **Dependencies:** in `pyproject.toml`, remove `fastapi` and `uvicorn[standard]` (keep `pydantic-settings`) and add what you need, e.g. `pandas`, `langgraph`, `qdrant-client`. Remove `httpx` from `dev` if nothing uses it.
2. **Entry point:** replace `src/app/main.py` with a plain function:
   ```python
   """Entry point. Run: make run  (or: python -m app.main)"""

   import logging

   from app.config import get_settings

   log = logging.getLogger(__name__)


   def run() -> int:
       settings = get_settings()
       logging.basicConfig(level=settings.log_level)
       log.info("starting %s", settings.app_name)
       # your pipeline / agent / job here
       return 0


   if __name__ == "__main__":
       raise SystemExit(run())
   ```
   Need command-line arguments? Copy the argparse pattern from `engineering-templates/python/cli_script.py`.
3. **Test:** replace `tests/test_health.py` with a direct call:
   ```python
   from app.main import run


   def test_run_succeeds():
       assert run() == 0
   ```
4. **Run + Docker:** in the `Makefile`, change `run` to `python -m app.main`. Delete the `Dockerfile` and the CI `docker build` step if nothing gets deployed; otherwise change its `CMD` to `["python", "-m", "app.main"]` and drop `EXPOSE 8000`.

Then run `make check`: it should pass before your first real commit.

## Key decisions & trade-offs
See [docs/decisions.md](docs/decisions.md). Summarise the 2–3 most important here.

## What I'd do next
Honest limitations and the next improvements (shows engineering judgement).
