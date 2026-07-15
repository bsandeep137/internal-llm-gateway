import pytest
from app.services.redaction import RedactionService


@pytest.fixture
def svc():
    return RedactionService()


class TestRedactionService:
    def test_redacts_email(self, svc):
        text, n = svc.redact("Contact me at john@example.com for details.")
        assert "[EMAIL]" in text
        assert "john@example.com" not in text
        assert n >= 1

    def test_redacts_credit_card(self, svc):
        text, n = svc.redact("Card: 4111 1111 1111 1111 was used.")
        assert "[CARD]" in text
        assert n >= 1

    def test_redacts_multiple_pii(self, svc):
        text, n = svc.redact(
            "Email test@test.org and card 4111-1111-1111-1111."
        )
        assert n >= 2
        assert "test@test.org" not in text

    def test_no_pii_returns_original(self, svc):
        original = "Hello world, how are you today?"
        text, n = svc.redact(original)
        assert text == original
        assert n == 0

    def test_redact_messages(self, svc):
        msgs = [
            {"role": "user", "content": "My email is alice@corp.com"},
            {"role": "system", "content": "No PII here"},
        ]
        result, total = svc.redact_messages(msgs)
        assert total >= 1
        assert "alice@corp.com" not in result[0]["content"]
        assert result[1]["content"] == "No PII here"
