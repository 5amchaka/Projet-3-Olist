.PHONY: help install download etl test test-integration test-all

help:
	@echo "Targets disponibles:"
	@echo "  make install           # Creer l'environnement + installer les dependances"
	@echo "  make download          # Telecharger et valider les 9 CSV Olist"
	@echo "  make etl               # Executer le pipeline ETL complet"
	@echo "  make test              # Tests hors integration"
	@echo "  make test-integration  # Tests d'integrite CSV <-> DW"
	@echo "  make test-all          # Tous les tests"

install:
	uv venv && uv sync

download:
	bash scripts/download_dataset.sh

etl:
	uv run python -m src.etl

test:
	uv run python -m pytest tests/ -v -m "not integration"

test-integration:
	uv run python -m pytest tests/test_pipeline_integrity.py -v

test-all:
	uv run python -m pytest tests/ -v
