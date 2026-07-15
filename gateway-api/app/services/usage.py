from datetime import datetime

from sqlalchemy.orm import Session

from app.schemas.models import Request as RequestModel, RequestEvent


class UsageService:
    """Persist request-level telemetry and lifecycle events."""

    def record_request(
        self,
        db: Session,
        *,
        request_id: str,
        tenant_id: int,
        api_key_id: int,
        requested_model: str,
        routed_provider: str,
        routed_model: str,
        sensitivity_level: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: int,
        status_code: int,
        estimated_cost: float | None = None,
        error_type: str | None = None,
    ) -> RequestModel:
        record = RequestModel(
            request_id=request_id,
            tenant_id=tenant_id,
            api_key_id=api_key_id,
            requested_model=requested_model,
            routed_provider=routed_provider,
            routed_model=routed_model,
            sensitivity_level=sensitivity_level,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            status_code=status_code,
            estimated_cost=estimated_cost,
            error_type=error_type,
            created_at=datetime.utcnow(),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def log_event(
        self,
        db: Session,
        *,
        request_id: str,
        event_type: str,
        payload: dict,
    ) -> None:
        event = RequestEvent(
            request_id=request_id,
            event_type=event_type,
            payload_json=payload,
            created_at=datetime.utcnow(),
        )
        db.add(event)
        db.commit()
