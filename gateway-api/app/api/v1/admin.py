import hashlib
import secrets
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.schemas.models import (
    ApiKey,
    AuditLog,
    Request as RequestModel,
    Tenant,
)

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _audit(db: Session, action: str, resource_type: str, resource_id: str, payload: dict = {}):
    db.add(
        AuditLog(
            actor="admin",
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            payload_json=payload,
            created_at=datetime.utcnow(),
        )
    )
    db.commit()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class TenantCreate(BaseModel):
    name: str
    daily_token_budget: int = 500_000
    monthly_cost_budget: int = 100
    default_sensitivity_policy: str = "public"
    description: Optional[str] = None


class TenantUpdate(BaseModel):
    daily_token_budget: Optional[int] = None
    monthly_cost_budget: Optional[int] = None
    default_sensitivity_policy: Optional[str] = None
    status: Optional[str] = None


class ApiKeyCreate(BaseModel):
    tenant_id: int
    name: str
    requests_per_minute: Optional[int] = 60
    daily_token_limit: Optional[int] = None
    allowed_models: Optional[List[str]] = None
    allowed_sensitivity_levels: Optional[List[str]] = ["public", "internal", "sensitive"]


class ApiKeyLimitsUpdate(BaseModel):
    requests_per_minute: Optional[int] = None
    daily_token_limit: Optional[int] = None
    allowed_models: Optional[List[str]] = None
    allowed_sensitivity_levels: Optional[List[str]] = None


# ---------------------------------------------------------------------------
# Tenant endpoints
# ---------------------------------------------------------------------------


@router.post("/tenants", status_code=201)
def create_tenant(body: TenantCreate, db: Session = Depends(get_db)):
    tenant = Tenant(
        name=body.name,
        status="active",
        daily_token_budget=body.daily_token_budget,
        monthly_cost_budget=body.monthly_cost_budget,
        default_sensitivity_policy=body.default_sensitivity_policy,
        description=body.description,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    _audit(db, "create_tenant", "tenant", tenant.id)
    return {
        "id": tenant.id,
        "name": tenant.name,
        "status": tenant.status,
        "daily_token_budget": tenant.daily_token_budget,
        "monthly_cost_budget": tenant.monthly_cost_budget,
        "default_sensitivity_policy": tenant.default_sensitivity_policy,
        "created_at": tenant.created_at,
    }


@router.get("/tenants")
def list_tenants(db: Session = Depends(get_db)):
    return db.query(Tenant).order_by(Tenant.id).all()


@router.get("/tenants/{tenant_id}")
def get_tenant(tenant_id: int, db: Session = Depends(get_db)):
    t = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return t


@router.patch("/tenants/{tenant_id}")
def update_tenant(tenant_id: int, body: TenantUpdate, db: Session = Depends(get_db)):
    t = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tenant not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(t, field, value)
    t.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(t)
    _audit(db, "update_tenant", "tenant", tenant_id, body.model_dump(exclude_none=True))
    return t


# ---------------------------------------------------------------------------
# API key endpoints
# ---------------------------------------------------------------------------


@router.post("/api-keys", status_code=201)
def create_api_key(body: ApiKeyCreate, db: Session = Depends(get_db)):
    tenant = db.query(Tenant).filter(Tenant.id == body.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    raw_key = f"llmgw-{secrets.token_urlsafe(32)}"
    api_key = ApiKey(
        tenant_id=body.tenant_id,
        name=body.name,
        key_hash=_hash_key(raw_key),
        status="active",
        requests_per_minute=body.requests_per_minute,
        daily_token_limit=body.daily_token_limit,
        allowed_models=body.allowed_models,
        allowed_sensitivity_levels=body.allowed_sensitivity_levels,
        created_at=datetime.utcnow(),
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    _audit(db, "create_api_key", "api_key", api_key.id)

    # The raw key is returned ONCE and not stored – treat it like a password
    return {
        "id": api_key.id,
        "name": api_key.name,
        "tenant_id": api_key.tenant_id,
        "key": raw_key,  # shown once
        "requests_per_minute": api_key.requests_per_minute,
        "daily_token_limit": api_key.daily_token_limit,
        "allowed_models": api_key.allowed_models,
        "allowed_sensitivity_levels": api_key.allowed_sensitivity_levels,
        "created_at": api_key.created_at,
    }


@router.get("/api-keys")
def list_api_keys(tenant_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(ApiKey)
    if tenant_id:
        q = q.filter(ApiKey.tenant_id == tenant_id)
    keys = q.order_by(ApiKey.id).all()
    # never expose key_hash
    return [
        {
            "id": k.id,
            "name": k.name,
            "tenant_id": k.tenant_id,
            "status": k.status,
            "requests_per_minute": k.requests_per_minute,
            "daily_token_limit": k.daily_token_limit,
            "allowed_models": k.allowed_models,
            "allowed_sensitivity_levels": k.allowed_sensitivity_levels,
            "created_at": k.created_at,
        }
        for k in keys
    ]


@router.patch("/api-keys/{key_id}/limits")
def update_api_key_limits(
    key_id: int, body: ApiKeyLimitsUpdate, db: Session = Depends(get_db)
):
    k = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not k:
        raise HTTPException(status_code=404, detail="API key not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(k, field, value)
    db.commit()
    db.refresh(k)
    _audit(db, "update_api_key_limits", "api_key", key_id, body.model_dump(exclude_none=True))
    return {"id": k.id, "requests_per_minute": k.requests_per_minute, "daily_token_limit": k.daily_token_limit}


@router.delete("/api-keys/{key_id}")
def revoke_api_key(key_id: int, db: Session = Depends(get_db)):
    k = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not k:
        raise HTTPException(status_code=404, detail="API key not found")
    k.status = "revoked"
    db.commit()
    _audit(db, "revoke_api_key", "api_key", key_id)
    return {"id": k.id, "status": "revoked"}


# ---------------------------------------------------------------------------
# Usage / analytics endpoints
# ---------------------------------------------------------------------------


@router.get("/usage/summary")
def usage_summary(db: Session = Depends(get_db)):
    """Platform-wide summary for today and all time."""
    today = date.today()

    total_requests = db.query(func.count(RequestModel.id)).scalar()

    today_row = (
        db.query(
            func.count(RequestModel.id).label("req"),
            func.coalesce(func.sum(RequestModel.prompt_tokens), 0).label("pt"),
            func.coalesce(func.sum(RequestModel.completion_tokens), 0).label("ct"),
            func.coalesce(func.sum(RequestModel.estimated_cost), 0.0).label("cost"),
        )
        .filter(func.date(RequestModel.created_at) == today)
        .one()
    )

    by_provider = (
        db.query(
            RequestModel.routed_provider,
            func.count(RequestModel.id).label("count"),
        )
        .filter(func.date(RequestModel.created_at) == today)
        .group_by(RequestModel.routed_provider)
        .all()
    )

    error_rate_row = (
        db.query(
            func.count(RequestModel.id).label("errors"),
        )
        .filter(
            func.date(RequestModel.created_at) == today,
            RequestModel.status_code >= 400,
        )
        .one()
    )

    return {
        "total_requests_all_time": total_requests,
        "today": str(today),
        "today_requests": today_row.req,
        "today_prompt_tokens": today_row.pt,
        "today_completion_tokens": today_row.ct,
        "today_total_tokens": today_row.pt + today_row.ct,
        "today_estimated_cost_usd": round(float(today_row.cost), 6),
        "today_errors": error_rate_row.errors,
        "today_by_provider": [
            {"provider": r.routed_provider, "count": r.count} for r in by_provider
        ],
    }


@router.get("/usage/by-tenant")
def usage_by_tenant(db: Session = Depends(get_db)):
    today = date.today()
    rows = (
        db.query(
            RequestModel.tenant_id,
            func.count(RequestModel.id).label("requests"),
            func.coalesce(func.sum(RequestModel.prompt_tokens + RequestModel.completion_tokens), 0).label("tokens"),
            func.coalesce(func.sum(RequestModel.estimated_cost), 0.0).label("cost"),
        )
        .filter(func.date(RequestModel.created_at) == today)
        .group_by(RequestModel.tenant_id)
        .all()
    )
    return [
        {
            "tenant_id": r.tenant_id,
            "today_requests": r.requests,
            "today_tokens": r.tokens,
            "today_estimated_cost_usd": round(float(r.cost), 6),
        }
        for r in rows
    ]


@router.get("/requests")
def list_requests(
    limit: int = 50,
    offset: int = 0,
    tenant_id: Optional[int] = None,
    provider: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(RequestModel).order_by(RequestModel.created_at.desc())
    if tenant_id:
        q = q.filter(RequestModel.tenant_id == tenant_id)
    if provider:
        q = q.filter(RequestModel.routed_provider == provider)
    rows = q.offset(offset).limit(limit).all()
    return [
        {
            "request_id": r.request_id,
            "tenant_id": r.tenant_id,
            "api_key_id": r.api_key_id,
            "requested_model": r.requested_model,
            "routed_provider": r.routed_provider,
            "routed_model": r.routed_model,
            "sensitivity_level": r.sensitivity_level,
            "prompt_tokens": r.prompt_tokens,
            "completion_tokens": r.completion_tokens,
            "estimated_cost_usd": r.estimated_cost,
            "latency_ms": r.latency_ms,
            "status_code": r.status_code,
            "error_type": r.error_type,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.get("/requests/{request_id}")
def get_request(request_id: str, db: Session = Depends(get_db)):
    r = db.query(RequestModel).filter(RequestModel.request_id == request_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Request not found")
    return r


# ---------------------------------------------------------------------------
# Policy endpoint
# ---------------------------------------------------------------------------


@router.patch("/policies/{tenant_id}")
def update_tenant_policy(
    tenant_id: int,
    default_sensitivity_policy: str,
    db: Session = Depends(get_db),
):
    t = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tenant not found")
    t.default_sensitivity_policy = default_sensitivity_policy
    t.updated_at = datetime.utcnow()
    db.commit()
    _audit(db, "update_policy", "tenant", tenant_id, {"default_sensitivity_policy": default_sensitivity_policy})
    return {"tenant_id": tenant_id, "default_sensitivity_policy": t.default_sensitivity_policy}
