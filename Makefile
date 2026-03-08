.PHONY: install lint format typecheck test run-control compose-up

install:
	pip install -e .[dev]

lint:
	ruff check .

format:
	black .

typecheck:
	mypy services

test:
	pytest

run-control:
	uvicorn services.control_api.app.main:app --reload --port 8000

compose-up:
	docker compose up --build
