import pytest
from app.services.routing import RoutingService
from app.providers.mock_adapter import MockAdapter


@pytest.fixture
def routing():
    return RoutingService([MockAdapter()])


class TestRoutingService:
    def test_auto_cheap_task(self, routing):
        provider, model = routing.resolve("auto", task_type="summarize")
        assert provider == "mock"
        assert model == "mock-fast"

    def test_auto_strong_task(self, routing):
        provider, model = routing.resolve("auto", task_type="code")
        assert provider == "mock"
        assert model == "mock-gpt"

    def test_auto_unknown_task_defaults_to_strong(self, routing):
        provider, model = routing.resolve("auto", task_type="unknown_task")
        assert provider == "mock"
        assert model == "mock-gpt"

    def test_explicit_model(self, routing):
        provider, model = routing.resolve("mock-fast")
        assert provider == "mock"
        assert model == "mock-fast"

    def test_explicit_unsupported_model_raises(self, routing):
        with pytest.raises(ValueError, match="No registered adapter supports"):
            routing.resolve("gpt-nonexistent")

    def test_sensitive_data_routes_to_mock(self, routing):
        provider, model = routing.resolve("auto", sensitivity_level="sensitive")
        assert provider == "mock"

    def test_allowlist_blocks_model(self, routing):
        with pytest.raises(ValueError, match="not in the allowlist"):
            routing.resolve("mock-gpt", allowed_models=["mock-fast"])

    def test_allowlist_allows_model(self, routing):
        provider, model = routing.resolve("mock-fast", allowed_models=["mock-fast"])
        assert model == "mock-fast"

    def test_auto_respects_allowlist(self, routing):
        # only mock-gpt allowed → auto should still work (picks from strong)
        provider, model = routing.resolve("auto", task_type="code", allowed_models=["mock-gpt"])
        assert model == "mock-gpt"

    def test_no_adapters_raises(self):
        svc = RoutingService([])
        with pytest.raises(ValueError, match="No adapter available"):
            svc.resolve("auto")
