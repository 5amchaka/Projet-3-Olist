.PHONY: help install download etl dashboard launch launch-force launch-quick launch-with-tests launch-with-all-tests launch-with-verify health test test-integration test-all verify

help:
	@echo "Targets disponibles:"
	@echo "  make install           # Creer l'environnement + installer les dependances"
	@echo "  make download          # Telecharger et valider les 9 CSV Olist"
	@echo "  make etl               # Executer le pipeline ETL complet"
	@echo "  make dashboard         # Lancer le dashboard NiceGUI"
	@echo "  make launch                # Launcher automatise (one-command)"
	@echo "  make launch-force          # Launcher avec rebuild complet"
	@echo "  make launch-quick          # Launcher en mode rapide (skip si possible)"
	@echo "  make launch-with-tests     # Launcher avec tests unitaires"
	@echo "  make launch-with-all-tests # Launcher avec tous les tests"
	@echo "  make launch-with-verify    # Launcher avec verification CSV"
	@echo "  make health                # Diagnostic systeme"
	@echo "  make test              # Tests hors integration"
	@echo "  make test-integration  # Tests d'integrite CSV <-> DW"
	@echo "  make test-all          # Tous les tests"
	@echo "  make verify            # Verifier l'analyse CSV via csvkit"

install:
	uv venv && uv sync

download:
	bash scripts/download_dataset.sh

etl:
	uv run python -m src.etl

dashboard:
	uv run --extra dashboard python -m src.dashboard

test:
	uv run python -m pytest tests/ -v -m "not integration"

test-integration:
	uv run python -m pytest tests/test_pipeline_integrity.py -v

test-all:
	uv run python -m pytest tests/ -v

verify:
	bash scripts/verify_csv_analysis.sh

launch:
	uv run python launch.py --theme simplon

launch-force:
	uv run python launch.py --theme simplon --force

launch-quick:
	uv run python launch.py --theme simplon --skip-download --skip-etl

launch-with-tests:
	uv run python launch.py --theme simplon --run-tests

launch-with-all-tests:
	uv run python launch.py --theme simplon --run-all-tests

launch-with-verify:
	uv run python launch.py --theme simplon --verify-csv

health:
	uv run python launch.py --health-check-only
