.PHONY: up down logs api-test eval ingest seed

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

api-test:
	cd apps/api && pytest

eval:
	python scripts/eval/run_eval.py

ingest:
	python scripts/ingest_guidelines.py

seed:
	python scripts/seed_demo_data.py
