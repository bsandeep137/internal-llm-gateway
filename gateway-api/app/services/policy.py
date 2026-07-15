from typing import Optional


class PolicyService:
    """
    Lightweight policy enforcement – allowlists and sensitivity checks.
    All methods are synchronous and stateless; they receive their data
    from the already-loaded ApiKey ORM object.
    """

    def check_model_allowlist(
        self,
        requested_model: str,
        allowed_models: Optional[list],
    ) -> bool:
        """
        Return True if the requested model is in the allowlist.
        A value of None means "all models allowed".
        "auto" is always permitted (the router will pick a concrete model later).
        """
        if not allowed_models:
            return True
        if requested_model == "auto":
            return True
        return requested_model in allowed_models

    def check_sensitivity(
        self,
        sensitivity_level: str,
        allowed_sensitivity_levels: Optional[list],
    ) -> bool:
        """
        Return True if the sensitivity level is permitted for this key.
        A value of None means "all levels allowed".
        """
        if not allowed_sensitivity_levels:
            return True
        return sensitivity_level in allowed_sensitivity_levels
