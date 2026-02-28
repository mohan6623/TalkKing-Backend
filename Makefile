.PHONY: dev test lint

dev:
	uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

test:
	pytest tests/ -v --tb=short

lint:
	python -m py_compile app/main.py
