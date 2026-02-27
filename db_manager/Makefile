.PHONY: build run ingest help

help:
	@echo "Available targets:"
	@echo "  build   - Build the db_manager docker image"
	@echo "  run     - Run the init_db.py script in a container"
	@echo "  ingest  - Alias for run"

build:
	docker build -t db_manager:latest .

run:
	docker run --rm --env-file ../.env.database -v $(CURDIR)/../data:/app/data db_manager:latest

ingest: run
