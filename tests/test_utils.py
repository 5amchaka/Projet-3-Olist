"""Tests pour le module utils."""

import pandas as pd

from src.etl.utils import safe_mode


class TestSafeMode:
    def test_returns_mode_when_available(self):
        s = pd.Series(["a", "b", "a", "c"])
        assert safe_mode(s) == "a"

    def test_returns_default_when_all_nan(self):
        s = pd.Series([None, None, None])
        assert safe_mode(s) == "unknown"

    def test_custom_default(self):
        s = pd.Series([None, None])
        assert safe_mode(s, default="not_defined") == "not_defined"
