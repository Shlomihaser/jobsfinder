.PHONY: help up down restart logs migration migrate app install

help:
	@echo "Available commands:"
	@echo "  make up           - Start Docker containers"
	@echo "  make down         - Stop Docker containers"
	@echo "  make restart      - Restart Docker containers"
	@echo "  make logs         - View Docker logs"
	@echo "  make migration msg=\"...\" - Generate a new migration (usage: make migration msg=\"init\")"
	@echo "  make migrate      - Apply pending migrations to the database"
	@echo "  make app          - Run the FastAPI application locally"
	@echo "  make install      - Install Python dependencies"

up:
	docker-compose up -d

down:
	docker-compose down

restart: down up

logs:
	docker-compose logs -f

migration:
	alembic revision --autogenerate -m "$(msg)"

migrate:
	alembic upgrade head

app:
	uvicorn main:app --reload

install:
	pip install -r requirements.txt
