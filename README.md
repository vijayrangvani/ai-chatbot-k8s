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

## Deploy to Kubernetes
Tested on Docker Desktop's Kubernetes. Manifests are in `k8s/`, numbered in apply order.

```bash
# 1. Secret (02-secret.yaml is git-ignored). Replace BOTH CHANGE_ME values with the same password.
cp k8s/02-secret.yaml.example k8s/02-secret.yaml

# 2. Build the api image
docker build -t ai-chatbot-api:0.1 .

# 3. Copy the image into the cluster node. Docker Desktop's node has its own image store, so
#    `imagePullPolicy: Never` can't see your local images. Repeat after every rebuild.
#    Node name: `kubectl get nodes`
docker save ai-chatbot-api:0.1 | docker exec -i desktop-control-plane ctr -n k8s.io images import -

# 4. Deploy and wait for the pods
kubectl apply -f k8s/
kubectl -n ai-chatbot rollout status deploy/ollama
kubectl -n ai-chatbot rollout status deploy/api

# 5. Pull the model once (stored on the ollama PVC, survives pod restarts)
kubectl -n ai-chatbot exec deploy/ollama -- ollama pull qwen2.5:1.5b

# 6. Try it
kubectl -n ai-chatbot port-forward svc/api 8000:80   # then: curl localhost:8000/health
```

After rebuilding the image: repeat step 3, then `kubectl -n ai-chatbot rollout restart deploy/api`.

## Known limitations
- **Readiness = liveness (`/health`):** it doesn't check the database, so pods stay Ready and get traffic while Postgres is down.
- **No startup ordering:** on a fresh cluster the api can crash-loop until Postgres is ready, and both replicas run `create_all` at the same time.
- **No authentication:** the NodePort exposes `/chat`, and anyone who can reach it can read any session's history by its `session_id`.
- **No `securityContext`:** containers don't enforce non-root or drop privileges; Ollama runs as root.
- **No network isolation:** no NetworkPolicy and no Redis password, so any pod in the cluster can reach db, redis and ollama.

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
