# =============================================================================
# pyweather — automação do projeto
#   * Gestão de dependências Python via uv
#   * Qualidade (format, lint, mypy, testes) via scripts/sh
#   * Orquestração Docker Compose
# =============================================================================
.DEFAULT_GOAL := help
SHELL := /usr/bin/env bash

PROJECT      	:= pyweather
COMPOSE_FILE 	:= infra/docker/docker-compose.yml
COMPOSE      	:= docker compose -f $(COMPOSE_FILE) -p gntech-$(PROJECT)
ETL_MODULE_DIR	:= ./services/etl
API_MODULE_DIR	:= ./service/api

# Alvo dos scripts de qualidade: etl | api | all  (ex.: make test TARGET=api)
TARGET ?= all
# Serviço do Compose para logs/restart/shell (ex.: make logs SERVICE=etl)
SERVICE ?=

.PHONY: help
help: ## Lista os comandos disponíveis
	@awk 'BEGIN {FS = ":.*##"; printf "\nUso: make \033[36m<alvo>\033[0m [TARGET=etl|api|all] [SERVICE=etl|api|database]\n"} \
		/^[a-zA-Z0-9_-]+:.*##/ { printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2 } \
		/^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) }' $(MAKEFILE_LIST)

##@ Dependências (uv)
.PHONY: install install-etl install-api lock upgrade
install: ## Instala todas as dependências (dev + etl + api) a partir do uv.lock
	uv sync --locked --all-groups

install-etl: ## Instala apenas as dependências do ETL (+ dev)
	uv sync --locked --no-default-groups --group etl --group dev

install-api: ## Instala apenas as dependências da API (+ dev)
	uv sync --locked --no-default-groups --group api --group dev

lock: ## Atualiza o uv.lock respeitando os limites do pyproject.toml
	uv lock

upgrade: ## Atualiza todas as dependências para as versões mais recentes permitidas
	uv lock --upgrade

##@ Qualidade
.PHONY: format format-check lint typecheck test qa
format: ## Formata o código (Ruff)           — TARGET=etl|api|all
	scripts/sh/format.sh $(TARGET)

format-check: ## Verifica a formatação           — TARGET=etl|api|all
	scripts/sh/format.sh $(TARGET) --check

lint: ## Linting (Ruff)                        — TARGET=etl|api|all
	scripts/sh/lint.sh $(TARGET)

typecheck: ## Tipagem estática (Mypy strict)   — TARGET=etl|api|all
	scripts/sh/typecheck.sh $(TARGET)

test: ## Testes unitários + cobertura ≥ 80%   — TARGET=etl|api|all
	scripts/sh/test.sh $(TARGET)

qa: format-check lint typecheck test ## Executa toda a esteira de qualidade

##@ Documentação
.PHONY: docs docs-check docs-render
docs: ## Sincroniza os blocos Mermaid dos .md com docs/md/diagramas/*.mmd
	scripts/sh/docs.sh

docs-check: ## Falha se algum bloco Mermaid estiver desatualizado
	scripts/sh/docs.sh --check

docs-render: ## Renderiza os .mmd em SVG (requer mmdc) para validar a sintaxe
	scripts/sh/docs.sh --render

##@ Execução local (sem Docker)
.PHONY: migrate etl-run etl-serve api-dev
migrate: ## Aplica as migrações do banco (requer POSTGRES_* no ambiente)
	uv run --directory $(ETL_MODULE_DIR) python -m pyweather_etl migrate

etl-run: ## Executa uma extração única do ETL
	uv run --directory $(ETL_MODULE_DIR) python -m pyweather_etl run

etl-serve: ## Executa o ETL em loop (migra e agenda extrações)
	uv run --directory $(ETL_MODULE_DIR) python -m pyweather_etl serve

api-dev: ## Sobe a API com autoreload em http://localhost:8000/docs
	uv run --directory $(API_MODULE_DIR) uvicorn pyweather_api.main:app --reload --app-dir $(API_MODULE_DIR)

##@ Smoke tests (Postman/Newman)
.PHONY: smoke smoke-up smoke-run smoke-down smoke-logs smoke-local
smoke: ## Stack completa em contêineres + collection Postman (sobe, testa e derruba)
	scripts/sh/smoke.sh all

smoke-up: ## Sobe a stack de smoke (database, mock-openweather, etl, api)
	scripts/sh/smoke.sh up

smoke-run: ## Executa a collection (Newman) contra a stack de smoke já no ar
	scripts/sh/smoke.sh run

smoke-down: ## Derruba a stack de smoke e remove o volume
	scripts/sh/smoke.sh down

smoke-logs: ## Mostra os logs da stack de smoke
	scripts/sh/smoke.sh logs

smoke-local: ## Mesma collection, environment local (http://localhost:8000), via npx
	scripts/sh/smoke.sh local

##@ Docker Compose
.PHONY: docker-build up down restart ps logs shell clean-docker
docker-build: ## Constrói as imagens (gntech/pyweather-*:latest)
	$(COMPOSE) build

up: ## Sobe todos os serviços em segundo plano
	$(COMPOSE) up -d --build

down: ## Para e remove os contêineres (mantém o volume do banco)
	$(COMPOSE) down

restart: ## Reinicia um serviço                — SERVICE=etl|api|database
	$(COMPOSE) restart $(SERVICE)

ps: ## Lista o estado dos serviços
	$(COMPOSE) ps

logs: ## Acompanha logs (todos ou SERVICE=...)
	$(COMPOSE) logs -f --tail=100 $(SERVICE)

shell: ## Abre um shell no serviço              — SERVICE=etl|api|database
	@test -n "$(SERVICE)" || (echo "Informe SERVICE=etl|api|database" && exit 2)
	$(COMPOSE) exec $(SERVICE) sh

clean-docker: ## Remove contêineres, imagens locais e VOLUMES (apaga os dados!)
	$(COMPOSE) down --volumes --rmi local
