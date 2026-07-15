from dataclasses import dataclass
from typing import Optional
from sqlalchemy.orm import Session
from app.schemas.models import ProviderConfig


@dataclass
class PriceEstimate:
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float


def estimate_price(
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    db: Session,
) -> Optional[PriceEstimate]:
    """
    Look up cost_input_per_1k / cost_output_per_1k from provider_configs
    and return a cost breakdown. Returns None if the provider/model is not found.
    """
    config = (
        db.query(ProviderConfig)
        .filter(
            ProviderConfig.provider_name == provider,
            ProviderConfig.model_name == model,
            ProviderConfig.is_active == True,
        )
        .first()
    )

    if config is None:
        return None

    input_cost = (prompt_tokens / 1000) * (config.cost_input_per_1k or 0.0)
    output_cost = (completion_tokens / 1000) * (config.cost_output_per_1k or 0.0)

    return PriceEstimate(
        provider=provider,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        input_cost=round(input_cost, 6),
        output_cost=round(output_cost, 6),
        total_cost=round(input_cost + output_cost, 6),
    )
