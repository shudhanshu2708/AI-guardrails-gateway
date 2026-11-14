.PHONY: install test eval backend frontend up down

install:
	cd backend && pip install -r requirements-dev.txt
	cd frontend && npm install

test:
	cd backend && python -m pytest -q

eval:
	cd backend && python -m app.evals.cli --max-asr 0.05 --min-tcr 0.85

backend:
	cd backend && uvicorn app.main:create_app --factory --reload --port 8000

frontend:
	cd frontend && npm run dev

up:
	docker compose up --build

down:
	docker compose down
