"""
Integration-style tests for the chat completions endpoint.
Uses FastAPI's TestClient with the mock adapter so no real DB or Redis is needed.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from app.main import app
from app.providers.base import ChatResponse


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_api_key():
    key = MagicMock()
    key.id = 1
    key.tenant_id = 1
    key.name = "test-key"
    key.status = "active"
    key.requests_per_minute = 60
    key.daily_token_limit = 100_000
    key.allowed_models = None
    key.allowed_sensitivity_levels = ["public", "internal", "sensitive"]
    key.tenant = MagicMock()
    key.tenant.daily_token_budget = 500_000
    return key


@pytest.fixture
def mock_provider_response():
    return ChatResponse(
        provider="mock",
        model="mock-gpt",
        content="Hello from mock!",
        prompt_tokens=10,
        completion_tokens=5,
        latency_ms=50,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestChatEndpoint:
    def test_requires_auth(self):
        client = TestClient(app)
        resp = client.post("/v1/chat/completions", json={"messages": [{"role": "user", "content": "hi"}]})
        assert resp.status_code == 422  # missing Authorization header

    def test_rejects_invalid_key(self):
        client = TestClient(app)
        resp = client.post(
            "/v1/chat/completions",
            json={"messages": [{"role": "user", "content": "hi"}]},
            headers={"Authorization": "Bearer invalid-key"},
        )
        assert resp.status_code == 401

    @patch("app.api.v1.chat.RateLimitService")
    @patch("app.api.v1.chat.UsageService")
    @patch("app.api.v1.chat.get_current_api_key")
    def test_successful_completion(
        self,
        mock_get_key,
        mock_usage_cls,
        mock_rl_cls,
        mock_api_key,
        mock_provider_response,
    ):
        mock_get_key.return_value = mock_api_key

        mock_rl = AsyncMock()
        mock_rl.check_requests_per_minute = AsyncMock(return_value=True)
        mock_rl.check_token_budget = AsyncMock(return_value=(True, "ok"))
        mock_rl.record_token_usage = AsyncMock()
        mock_rl_cls.return_value = mock_rl

        mock_usage = MagicMock()
        mock_usage.record_request = MagicMock()
        mock_usage.log_event = MagicMock()
        mock_usage_cls.return_value = mock_usage

        with patch("app.api.v1.chat._ADAPTERS") as mock_adapters_list:
            mock_adapter = AsyncMock()
            mock_adapter.provider_name = "mock"
            mock_adapter.supports_model = MagicMock(return_value=True)
            mock_adapter.chat = AsyncMock(return_value=mock_provider_response)
            mock_adapters_list.__iter__ = MagicMock(return_value=iter([mock_adapter]))

            from app.api.v1.chat import _ADAPTERS as real_adapters
            # patch the routing service to use our mock adapter
            with patch("app.api.v1.chat.RoutingService") as mock_routing_cls:
                mock_routing = MagicMock()
                mock_routing.resolve = MagicMock(return_value=("mock", "mock-gpt"))
                mock_routing.adapters = {"mock": mock_adapter}
                mock_routing_cls.return_value = mock_routing

                client = TestClient(app)
                resp = client.post(
                    "/v1/chat/completions",
                    json={
                        "model": "auto",
                        "messages": [{"role": "user", "content": "Hello!"}],
                    },
                    headers={"Authorization": "Bearer test-key"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["object"] == "chat.completion"
        assert "choices" in data
        assert data["gateway"]["routed_provider"] == "mock"
