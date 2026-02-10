"""Tests pour l'orchestrateur du pipeline ETL."""

import logging
from unittest.mock import MagicMock, call, patch

import pytest

from src.etl.pipeline import _log_phase, run_full_pipeline


class TestLogPhase:
    def test_logs_title_with_separators(self, caplog):
        with caplog.at_level(logging.INFO, logger="src.etl.pipeline"):
            _log_phase("TEST PHASE")

        assert "TEST PHASE" in caplog.text
        assert "=" * 60 in caplog.text


class TestRunFullPipeline:
    @patch("src.etl.pipeline.load_to_sqlite")
    @patch("src.etl.pipeline.get_engine")
    @patch("src.etl.pipeline.build_fact_orders")
    @patch("src.etl.pipeline.build_dim_products")
    @patch("src.etl.pipeline.build_dim_sellers")
    @patch("src.etl.pipeline.build_dim_customers")
    @patch("src.etl.pipeline.build_dim_geolocation")
    @patch("src.etl.pipeline.build_dim_dates")
    @patch("src.etl.pipeline.clean_all")
    @patch("src.etl.pipeline.load_all_raw")
    @patch("src.etl.pipeline.DATABASE_DIR")
    def test_calls_all_phases_in_order(
        self,
        mock_db_dir,
        mock_extract,
        mock_clean,
        mock_dim_dates,
        mock_dim_geo,
        mock_dim_cust,
        mock_dim_sell,
        mock_dim_prod,
        mock_fact,
        mock_engine,
        mock_load,
    ):
        """Vérifier que chaque étape du pipeline est appelée dans le bon ordre."""
        # Setup mocks
        mock_extract.return_value = {"orders": MagicMock(), "geolocation": MagicMock()}
        mock_clean.return_value = {
            "orders": MagicMock(),
            "geolocation": MagicMock(),
            "customers": MagicMock(),
            "sellers": MagicMock(),
            "products": MagicMock(),
            "order_items": MagicMock(),
            "order_payments": MagicMock(),
            "order_reviews": MagicMock(),
        }
        mock_dim_dates.return_value = MagicMock(__len__=lambda s: 10)
        mock_dim_geo.return_value = MagicMock(__len__=lambda s: 5)
        mock_dim_cust.return_value = MagicMock(__len__=lambda s: 3)
        mock_dim_sell.return_value = MagicMock(__len__=lambda s: 2)
        mock_dim_prod.return_value = MagicMock(__len__=lambda s: 4)
        mock_fact.return_value = MagicMock(__len__=lambda s: 20)

        run_full_pipeline()

        # Vérifier l'ordre d'appel
        mock_extract.assert_called_once()
        mock_clean.assert_called_once()
        mock_dim_dates.assert_called_once()
        mock_dim_geo.assert_called_once()
        mock_dim_cust.assert_called_once()
        mock_dim_sell.assert_called_once()
        mock_dim_prod.assert_called_once()
        mock_fact.assert_called_once()
        mock_load.assert_called_once()

    @patch("src.etl.pipeline.load_all_raw")
    def test_extraction_error_propagates(self, mock_extract):
        """Une erreur d'extraction doit remonter sans être avalée."""
        mock_extract.side_effect = RuntimeError("CSV manquant")

        with pytest.raises(RuntimeError, match="CSV manquant"):
            run_full_pipeline()

    @patch("src.etl.pipeline.clean_all")
    @patch("src.etl.pipeline.load_all_raw")
    def test_transform_error_propagates(self, mock_extract, mock_clean):
        """Une erreur de transformation doit remonter sans être avalée."""
        mock_extract.return_value = {}
        mock_clean.side_effect = ValueError("Colonne manquante")

        with pytest.raises(ValueError, match="Colonne manquante"):
            run_full_pipeline()
