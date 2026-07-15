import pytest
from app.services.policy import PolicyService


@pytest.fixture
def policy():
    return PolicyService()


class TestPolicyService:
    # Model allowlist tests
    def test_no_allowlist_permits_all(self, policy):
        assert policy.check_model_allowlist("gpt-4o", None) is True
        assert policy.check_model_allowlist("gpt-4o", []) is True

    def test_allowlist_permits_matching_model(self, policy):
        assert policy.check_model_allowlist("gpt-4o-mini", ["gpt-4o-mini", "mock-fast"]) is True

    def test_allowlist_blocks_unlisted_model(self, policy):
        assert policy.check_model_allowlist("gpt-4o", ["gpt-4o-mini"]) is False

    def test_auto_always_passes_allowlist(self, policy):
        assert policy.check_model_allowlist("auto", ["gpt-4o-mini"]) is True

    # Sensitivity tests
    def test_no_sensitivity_restriction_permits_all(self, policy):
        assert policy.check_sensitivity("sensitive", None) is True
        assert policy.check_sensitivity("sensitive", []) is True

    def test_sensitivity_permits_matching_level(self, policy):
        assert policy.check_sensitivity("internal", ["public", "internal"]) is True

    def test_sensitivity_blocks_higher_level(self, policy):
        assert policy.check_sensitivity("sensitive", ["public", "internal"]) is False
