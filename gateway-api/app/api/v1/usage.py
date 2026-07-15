from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_current_api_key, get_db
from app.schemas.models import ApiKey, Request as RequestModel

router = APIRouter()


@router.get("/usage/me")
async def usage_me(
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Return today's usage stats for the authenticated API key."""
    today = date.today()

    today_requests = (
        db.query(func.count(RequestModel.id))
        .filter(
            RequestModel.api_key_id == api_key.id,
            func.date(RequestModel.created_at) == today,
        )
        .scalar()
    )

    row = (
        db.query(
            func.coalesce(func.sum(RequestModel.prompt_tokens), 0).label("pt"),
            func.coalesce(func.sum(RequestModel.completion_tokens), 0).label("ct"),
            func.coalesce(func.sum(RequestModel.estimated_cost), 0.0).label("cost"),
        )
        .filter(
            RequestModel.api_key_id == api_key.id,
            func.date(RequestModel.created_at) == today,
        )
        .one()
    )

    return {
        "api_key_id": api_key.id,
        "api_key_name": api_key.name,
        "tenant_id": api_key.tenant_id,
        "today": str(today),
        "today_requests": today_requests,
        "today_prompt_tokens": row.pt,
        "today_completion_tokens": row.ct,
        "today_total_tokens": row.pt + row.ct,
        "today_estimated_cost_usd": round(float(row.cost), 6),
        "limits": {
            "requests_per_minute": api_key.requests_per_minute,
            "daily_token_limit": api_key.daily_token_limit,
        },
    }
