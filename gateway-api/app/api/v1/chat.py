import time
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_api_key, get_db
from app.core.metrics import (
    BUDGET_REJECTIONS_TOTAL,
    LLM_COST_DOLLARS_TOTAL,
    LLM_LATENCY_SECONDS,
    LLM_REQUESTS_TOTAL,
    LLM_TOKENS_TOTAL,
    POLICY_REJECTIONS_TOTAL,
    RATE_LIMIT_REJECTIONS_TOTAL,
    REDACTIONS_TOTAL,
)
from app.core.redis import get_redis
from app.providers.base import (
    ChatMessage as ProviderMessage,
    ChatRequest as ProviderRequest,
)
from app.providers.gemini_adapter import GeminiAdapter
from app.providers.mock_adapter import MockAdapter
from app.providers.openai_adapter import OpenAIAdapter
from app.schemas.models import ApiKey
from app.services.policy import PolicyService
from app.services.pricing import estimate_price
from app.services.rate_limit import RateLimitService
from app.services.redaction import RedactionService
from app.services.routing import RoutingService
from app.services.usage import UsageService

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class MessageSchema(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "auto"
    messages: List[MessageSchema]
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    task_type: Optional[str] = None  # "summarize" | "code" | "reasoning" | …


# ---------------------------------------------------------------------------
# Provider registry (built once per process)
# ---------------------------------------------------------------------------


def _build_adapters():
    adapters = [MockAdapter()]
    if settings.openai_api_key:
        adapters.append(OpenAIAdapter(settings.openai_api_key))
    if settings.gemini_api_key:
        adapters.append(GeminiAdapter(settings.gemini_api_key))
    return adapters


_ADAPTERS = _build_adapters()


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/chat/completions")
async def chat_completions(
    body: ChatCompletionRequest,
    request: Request,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
    x_data_sensitivity: Optional[str] = Header(
        default="public", alias="x-data-sensitivity"
    ),
):
    """
    OpenAI-compatible chat completions endpoint.

    Gateway flow
    ------------
    1. Policy: model allowlist check
    2. Policy: sensitivity level check
    3. Rate-limit: requests-per-minute
    4. Route: resolve provider + model
    5. Redact: strip PII for internal/sensitive traffic
    6. Budget: pre-flight token estimate
    7. Call: forward to provider adapter
    8. Record: persist usage + update Redis counters
    9. Return: OpenAI-compatible response
    """
    request_id: str = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    sensitivity: str = (x_data_sensitivity or "public").lower()

    policy_svc = PolicyService()
    rate_svc = RateLimitService(get_redis())
    redaction_svc = RedactionService()
    usage_svc = UsageService()
    routing_svc = RoutingService(_ADAPTERS)

    # 1. Model allowlist
    if not policy_svc.check_model_allowlist(body.model, api_key.allowed_models):
        POLICY_REJECTIONS_TOTAL.labels(reason="model_not_allowed").inc()
        usage_svc.log_event(
            db,
            request_id=request_id,
            event_type="policy_reject",
            payload={"reason": "model_not_allowed", "requested": body.model},
        )
        raise HTTPException(
            status_code=403,
            detail=f"Model '{body.model}' is not in the allowlist for this API key.",
        )

    # 2. Sensitivity check
    if not policy_svc.check_sensitivity(sensitivity, api_key.allowed_sensitivity_levels):
        POLICY_REJECTIONS_TOTAL.labels(reason="sensitivity_not_allowed").inc()
        raise HTTPException(
            status_code=403,
            detail=f"Sensitivity level '{sensitivity}' is not permitted for this API key.",
        )

    # 3. Rate limiting
    if api_key.requests_per_minute:
        within_limit = await rate_svc.check_requests_per_minute(
            api_key.id, api_key.requests_per_minute
        )
        if not within_limit:
            RATE_LIMIT_REJECTIONS_TOTAL.labels().inc()
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Retry after a minute.",
                headers={"Retry-After": "60"},
            )

    # 4. Routing
    try:
        provider_name, model_name = routing_svc.resolve(
            body.model,
            task_type=body.task_type,
            sensitivity_level=sensitivity,
            allowed_models=api_key.allowed_models,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # 5. Redaction
    messages = [m.model_dump() for m in body.messages]
    redaction_count = 0
    if sensitivity in ("sensitive", "internal"):
        messages, redaction_count = redaction_svc.redact_messages(messages)
        if redaction_count:
            REDACTIONS_TOTAL.labels(sensitivity=sensitivity).inc(redaction_count)

    # 6. Pre-flight token budget (rough estimate: 2 tokens per word)
    estimated_tokens = sum(len(m["content"].split()) * 2 for m in messages)
    tenant = api_key.tenant  # loaded via relationship
    budget_ok, budget_reason = await rate_svc.check_token_budget(
        api_key.id,
        api_key.tenant_id,
        estimated_tokens,
        api_key.daily_token_limit,
        tenant.daily_token_budget if tenant else None,
    )
    if not budget_ok:
        BUDGET_REJECTIONS_TOTAL.labels(reason=budget_reason).inc()
        raise HTTPException(
            status_code=402,
            detail=budget_reason.replace("_", " ").capitalize() + ".",
        )

    # 7. Call provider
    adapter = routing_svc.adapters[provider_name]
    provider_messages = [
        ProviderMessage(role=m["role"], content=m["content"]) for m in messages
    ]
    provider_req = ProviderRequest(
        model=model_name,
        messages=provider_messages,
        max_tokens=body.max_tokens,
        temperature=body.temperature,
    )

    t_start = time.monotonic()
    status_code = 200
    error_type: str | None = None

    try:
        provider_resp = await adapter.chat(provider_req)
    except Exception as exc:
        latency_s = time.monotonic() - t_start
        status_code = 502
        error_type = type(exc).__name__
        LLM_REQUESTS_TOTAL.labels(provider=provider_name, model=model_name, status="error").inc()
        LLM_LATENCY_SECONDS.labels(provider=provider_name, model=model_name).observe(latency_s)
        usage_svc.record_request(
            db,
            request_id=request_id,
            tenant_id=api_key.tenant_id,
            api_key_id=api_key.id,
            requested_model=body.model,
            routed_provider=provider_name,
            routed_model=model_name,
            sensitivity_level=sensitivity,
            prompt_tokens=0,
            completion_tokens=0,
            latency_ms=int((time.monotonic() - t_start) * 1000),
            status_code=status_code,
            error_type=error_type,
        )
        raise HTTPException(status_code=502, detail=f"Provider error: {exc}")

    latency_ms = int((time.monotonic() - t_start) * 1000)
    total_tokens = provider_resp.prompt_tokens + provider_resp.completion_tokens

    # 8. Record usage
    await rate_svc.record_token_usage(api_key.id, api_key.tenant_id, total_tokens)

    # Prometheus metrics – success path
    LLM_REQUESTS_TOTAL.labels(provider=provider_name, model=model_name, status="success").inc()
    LLM_LATENCY_SECONDS.labels(provider=provider_name, model=model_name).observe(latency_ms / 1000)
    LLM_TOKENS_TOTAL.labels(provider=provider_name, model=model_name, type="prompt").inc(provider_resp.prompt_tokens)
    LLM_TOKENS_TOTAL.labels(provider=provider_name, model=model_name, type="completion").inc(provider_resp.completion_tokens)

    price = estimate_price(
        provider_name,
        model_name,
        provider_resp.prompt_tokens,
        provider_resp.completion_tokens,
        db,
    )

    if price and price.total_cost:
        LLM_COST_DOLLARS_TOTAL.labels(provider=provider_name, model=model_name).inc(price.total_cost)

    usage_svc.record_request(
        db,
        request_id=request_id,
        tenant_id=api_key.tenant_id,
        api_key_id=api_key.id,
        requested_model=body.model,
        routed_provider=provider_name,
        routed_model=model_name,
        sensitivity_level=sensitivity,
        prompt_tokens=provider_resp.prompt_tokens,
        completion_tokens=provider_resp.completion_tokens,
        latency_ms=latency_ms,
        status_code=status_code,
        estimated_cost=price.total_cost if price else None,
        error_type=error_type,
    )

    # 9. OpenAI-compatible response
    return {
        "id": f"chatcmpl-{request_id}",
        "object": "chat.completion",
        "model": model_name,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": provider_resp.content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": provider_resp.prompt_tokens,
            "completion_tokens": provider_resp.completion_tokens,
            "total_tokens": total_tokens,
        },
        "gateway": {
            "request_id": request_id,
            "routed_provider": provider_name,
            "routed_model": model_name,
            "latency_ms": latency_ms,
            "redaction_count": redaction_count,
            "estimated_cost_usd": price.total_cost if price else None,
        },
    }
