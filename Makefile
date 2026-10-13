# Short names for commands you run 20 times a day. `make help` lists them.
# NOTE: indentation in Makefiles must be a TAB, not spaces.
.PHONY: help install run test lint format check docker

help:            ## list commands
	@grep -E '^[a-z]+:.*##' Makefile | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

install:         ## create venv deps + git hooks
	pip install -e ".[dev]"
	pre-commit install

run:             ## start the API with auto-reload
	uvicorn app.main:app --reload

test:            ## run tests
	pytest

lint:            ## check style / bugs
	ruff check .

format:          ## auto-fix formatting and imports
	ruff format .
	ruff check --fix .

check: lint test ## what CI runs

docker:          ## build and run the image
	docker build -t app .
	docker run --rm -p 8000:8000 --env-file .env app
