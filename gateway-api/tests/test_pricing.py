import pytest
from app.services.pricing import estimate_price, PriceEstimate
from unittest.mock import MagicMock


def make_db_with_config(cost_in=0.005, cost_out=0.015):
    config = MagicMock()
    config.cost_input_per_1k = cost_in
    config.cost_output_per_1k = cost_out

    db = MagicMock()
    query = MagicMock()
    query.filter.return_value.first.return_value = config
    db.query.return_value = query
    return db


class TestPricingService:
    def test_basic_cost_calculation(self):
        db = make_db_with_config(cost_in=0.005, cost_out=0.015)
        result = estimate_price("openai", "gpt-4o", 1000, 500, db)
        assert result is not None
        assert result.input_cost == pytest.approx(0.005, rel=1e-3)
        assert result.output_cost == pytest.approx(0.0075, rel=1e-3)
        assert result.total_cost == pytest.approx(0.0125, rel=1e-3)

    def test_returns_none_for_unknown_model(self):
        db = MagicMock()
        query = MagicMock()
        query.filter.return_value.first.return_value = None
        db.query.return_value = query
        result = estimate_price("unknown", "nonexistent", 100, 100, db)
        assert result is None

    def test_zero_cost_for_mock_provider(self):
        db = make_db_with_config(cost_in=0.0, cost_out=0.0)
        result = estimate_price("mock", "mock-gpt", 500, 200, db)
        assert result is not None
        assert result.total_cost == 0.0
