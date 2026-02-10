"""Tests pour le module extract."""

from unittest.mock import patch

import pandas as pd
import pytest

from src.etl.extract import load_raw_csv, load_all_raw


class TestLoadRawCsv:
    def test_valid_dataset(self, tmp_path):
        """Charger un CSV valide retourne le bon DataFrame."""
        csv_content = "col_a,col_b\n1,hello\n2,world\n"
        csv_file = tmp_path / "olist_customers_dataset.csv"
        csv_file.write_text(csv_content)

        with patch("src.etl.extract.RAW_DIR", tmp_path), \
             patch("src.etl.extract.CSV_FILES", {"customers": csv_file.name}):
            df = load_raw_csv("customers")

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert list(df.columns) == ["col_a", "col_b"]

    def test_invalid_name_raises_key_error(self):
        """Un nom de dataset inexistant lève KeyError."""
        with pytest.raises(KeyError):
            load_raw_csv("nom_inexistant")

    def test_missing_file_raises_error(self, tmp_path):
        """Un fichier CSV absent lève FileNotFoundError."""
        with patch("src.etl.extract.RAW_DIR", tmp_path), \
             patch("src.etl.extract.CSV_FILES", {"customers": "absent.csv"}):
            with pytest.raises(FileNotFoundError):
                load_raw_csv("customers")


class TestLoadAllRaw:
    def test_returns_all_datasets(self, tmp_path):
        """load_all_raw retourne un dict avec les 9 datasets."""
        fake_csv_files = {}
        for name in [
            "customers", "geolocation", "orders", "order_items",
            "order_payments", "order_reviews", "products", "sellers",
            "category_translation",
        ]:
            csv_file = tmp_path / f"{name}.csv"
            csv_file.write_text("id,value\n1,a\n")
            fake_csv_files[name] = csv_file.name

        with patch("src.etl.extract.RAW_DIR", tmp_path), \
             patch("src.etl.extract.CSV_FILES", fake_csv_files):
            result = load_all_raw()

        assert isinstance(result, dict)
        assert len(result) == 9
        for name, df in result.items():
            assert isinstance(df, pd.DataFrame)
            assert len(df) == 1
