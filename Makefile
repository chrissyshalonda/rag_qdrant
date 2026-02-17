COMPOSE_FILE=deploy/docker-compose.yaml

.PHONY: help build up down restart ps logs init-db ingest

help: ## Показать справку
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Собрать все Docker-образы
	docker compose -f $(COMPOSE_FILE) build

up: ## Запустить все сервисы в фоне
	docker compose -f $(COMPOSE_FILE) up -d

down: ## Остановить и удалить контейнеры
	docker compose -f $(COMPOSE_FILE) down

restart: ## Перезапустить сервисы
	docker compose -f $(COMPOSE_FILE) restart

ps: ## Статус контейнеров
	docker compose -f $(COMPOSE_FILE) ps

logs: ## Посмотреть логи всех сервисов
	docker compose -f $(COMPOSE_FILE) logs -f

init-airflow: ## Инициализировать базу данных Airflow и создать админа
	docker compose -f $(COMPOSE_FILE) run --rm airflow-webserver airflow db init
	docker compose -f $(COMPOSE_FILE) run --rm airflow-webserver airflow users create \
		--username admin --password admin --firstname Admin --lastname User \
		--role Admin --email admin@example.com

ingest: ## Запустить процесс загрузки документов (через профиль tools)
	docker compose -f $(COMPOSE_FILE) --profile tools run --rm ingest