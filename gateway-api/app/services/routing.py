from typing import Optional

from app.providers.base import BaseProviderAdapter

# Task type classification
CHEAP_TASK_TYPES = {"classification", "rewrite", "summarize", "extraction"}
STRONG_TASK_TYPES = {"reasoning", "planning", "code", "analysis"}

# Model presets per provider
CHEAP_MODELS: dict[str, str] = {
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.5-flash",
    "mock": "mock-fast",
}
STRONG_MODELS: dict[str, str] = {
    "openai": "gpt-4o",
    "gemini": "gemini-2.5-pro",
    "mock": "mock-gpt",
}

# For sensitive data, prefer a private/local model; mock stands in here
SENSITIVE_PROVIDER = "mock"


class RoutingService:
    """
    Resolves (provider, model) from a request's model field and metadata.

    Rules (applied in order):
    1. Sensitive data → SENSITIVE_PROVIDER only.
    2. Explicit model name → find matching adapter.
    3. model="auto" + cheap task → cheapest capable model.
    4. model="auto" + strong task (or unknown) → strongest capable model.
    """

    def __init__(self, adapters: list[BaseProviderAdapter]) -> None:
        self.adapters: dict[str, BaseProviderAdapter] = {
            a.provider_name: a for a in adapters
        }

    def resolve(
        self,
        requested_model: str,
        task_type: Optional[str] = None,
        sensitivity_level: Optional[str] = None,
        allowed_models: Optional[list[str]] = None,
    ) -> tuple[str, str]:
        """
        Return (provider_name, model_name).
        Raises ValueError if no adapter can satisfy the request.
        """
        # Rule 1: sensitive data must stay on the designated private provider
        if sensitivity_level == "sensitive":
            provider = SENSITIVE_PROVIDER
            if provider not in self.adapters:
                raise ValueError(
                    f"Sensitive routing requires provider '{provider}' but it is not registered."
                )
            model = STRONG_MODELS.get(provider, "mock-gpt")
            return provider, model

        # Rule 2: explicit model request
        if requested_model != "auto":
            for provider_name, adapter in self.adapters.items():
                if adapter.supports_model(requested_model):
                    if allowed_models and requested_model not in allowed_models:
                        raise ValueError(
                            f"Model '{requested_model}' is not in the allowlist for this key."
                        )
                    return provider_name, requested_model
            raise ValueError(
                f"No registered adapter supports model '{requested_model}'."
            )

        # Rule 3 & 4: auto-routing
        task = (task_type or "").lower()
        prefer_cheap = task in CHEAP_TASK_TYPES

        # Provider priority: openai > gemini > mock (real before fake)
        for provider_name in ("openai", "gemini", "mock"):
            if provider_name not in self.adapters:
                continue
            model = (CHEAP_MODELS if prefer_cheap else STRONG_MODELS).get(provider_name)
            if model is None:
                continue
            if allowed_models and model not in allowed_models:
                continue
            return provider_name, model

        raise ValueError("No adapter available for auto-routing.")
