.DEFAULT_GOAL := help

help: ## Lista comandos
	@awk 'BEGIN{FS=":.*##"} /^[a-zA-Z_-]+:.*##/ {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Instala deps locais (sem docker)
	python -m venv .venv && .venv/bin/pip install -e ".[dev]"

up: ## Sobe o container em dev
	docker compose up --build

down: ## Derruba o container
	docker compose down

logs: ## Tail dos logs
	docker compose logs -f api

shell: ## Shell dentro do container
	docker compose exec api bash

test: ## Roda testes
	docker compose exec api pytest

lint: ## Roda ruff
	docker compose exec api ruff check app

format: ## Formata
	docker compose exec api ruff format app

prod-build: ## Build imagem prod com tag
	docker build -t avu-api:$${TAG:-latest} .

prod-deploy: ## Sobe em prod (na VPS)
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

.PHONY: help install up down logs shell test lint format prod-build prod-deploy
