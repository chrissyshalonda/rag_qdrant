COMPOSE_FILE=deploy/docker-compose.yaml

.PHONY: help build up down restart ps logs init-db ingest

help: ## Показать справку
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build-docling: ## Собрать образ с docling (нужен перед ingest)
	docker build -f deploy/Dockerfile.docling -t rag_qdrant-docling:latest .

build: ## Собрать все Docker-образы
	docker compose -f $(COMPOSE_FILE) -p rag_qdrant build
	$(MAKE) -C db_manager build

build-without-docling:
	docker compose -f $(COMPOSE_FILE) -p rag_qdrant build

up: ## Запустить все сервисы в фоне
	docker compose -f $(COMPOSE_FILE) -p rag_qdrant up -d

down: ## Остановить и удалить контейнеры
	docker compose -f $(COMPOSE_FILE) -p rag_qdrant down

restart: ## Перезапустить сервисы
	docker compose -f $(COMPOSE_FILE) -p rag_qdrant up restart

ps: ## Статус контейнеров
	docker compose -f $(COMPOSE_FILE) -p rag_qdrant ps

logs: ## Посмотреть логи всех сервисов
	docker compose -f $(COMPOSE_FILE) -p rag_qdrant logs -f

base:
	docker compose -f deploy/docker-compose.yaml -p rag_qdrant up -d postgres qdrant

init-airflow:
	docker compose -f $(COMPOSE_FILE) -p rag_qdrant run --rm airflow-webserver bash -c "\
		airflow db migrate && \
		airflow users create \
		--username admin \
		--password admin \
		--firstname Admin \
		--lastname User \
		--role Admin \
		--email admin@example.com"

ingest: ## Запустить процесс загрузки документов через db_manager
	$(MAKE) -C db_manager ingest