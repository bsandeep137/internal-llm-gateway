import re

# Compiled patterns for PII detection
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
_PHONE = re.compile(
    r"\b(\+?1[\s\-.]?)?(\(?\d{3}\)?[\s\-.]?)?\d{3}[\s\-.]?\d{4}\b"
)
_CARD = re.compile(r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b")
_SSN = re.compile(r"\b\d{3}[\s\-]?\d{2}[\s\-]?\d{4}\b")


class RedactionService:
    """
    Regex-based PII redaction applied to prompt text before forwarding
    to external providers.
    """

    _RULES: list[tuple[re.Pattern, str]] = [
        (_EMAIL, "[EMAIL]"),
        (_CARD, "[CARD]"),  # card before phone to avoid partial match overlap
        (_PHONE, "[PHONE]"),
        (_SSN, "[SSN]"),
    ]

    def redact(self, text: str) -> tuple[str, int]:
        """
        Apply all redaction rules to *text*.
        Returns (redacted_text, total_replacements_count).
        """
        total = 0
        for pattern, placeholder in self._RULES:
            text, n = pattern.subn(placeholder, text)
            total += n
        return text, total

    def redact_messages(
        self, messages: list[dict]
    ) -> tuple[list[dict], int]:
        """
        Redact the 'content' field of each message dict.
        Returns (new_messages, total_redaction_count).
        """
        total = 0
        result = []
        for msg in messages:
            content, n = self.redact(msg.get("content", ""))
            total += n
            result.append({**msg, "content": content})
        return result, total
