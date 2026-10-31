.PHONY: run dev test seed up down lint clean

run:
	python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

dev:
	python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

seed:
	python scripts/seed.py

test:
	python -m pytest backend/tests/ -v

up:
	docker compose up --build -d

down:
	docker compose down

clean:
	rm -f surakshavani.db
	find . -type d -name __pycache__ -exec rm -rf {} +

