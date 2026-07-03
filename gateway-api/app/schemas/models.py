from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float, JSON, ForeignKey

Base = declarative_base()

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    status = Column(String(50), nullable=False)
    daily_token_budget = Column(Integer, nullable=False)
    monthly_cost_budget = Column(Integer, nullable=False)
    default_sensitivity_policy = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    key_hash = Column(String(255), unique=True, nullable=False)
    status = Column(String(50), nullable=False)
    requests_per_minute = Column(Integer, nullable=True)
    daily_token_limit = Column(Integer, nullable=True)
    allowed_models = Column(JSON, nullable=True)
    allowed_sensitivity_levels = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False)

    tenant = relationship("Tenant", backref="api_keys")


class ProviderConfig(Base):
    __tablename__ = "provider_configs"

    id = Column(Integer, primary_key=True, index=True)
    provider_name = Column(String(255), nullable=False)
    model_name = Column(String(255), nullable=False)
    endpoint = Column(String(500), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    cost_input_per_1k = Column(Float, nullable=True)
    cost_output_per_1k = Column(Float, nullable=True)
    max_context_tokens = Column(Integer, nullable=True)


class Request(Base):
    __tablename__ = "requests"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=True, index=True)
    request_id = Column(String(255), unique=True, nullable=False, index=True)
    requested_model = Column(String(255), nullable=True)
    routed_provider = Column(String(255), nullable=True)
    routed_model = Column(String(255), nullable=True)
    sensitivity_level = Column(String(50), nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    estimated_cost = Column(Float, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    status_code = Column(Integer, nullable=True)
    error_type = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False)

    tenant = relationship("Tenant", backref="requests")
    api_key = relationship("ApiKey", backref="requests")


class RequestEvent(Base):
    __tablename__ = "request_events"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(255), ForeignKey("requests.request_id"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False)
    payload_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False)


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    period_type = Column(String(50), nullable=False)  # "daily" | "monthly"
    token_budget = Column(Integer, nullable=True)
    cost_budget = Column(Float, nullable=True)
    alert_threshold_percent = Column(Integer, nullable=True, default=80)

    tenant = relationship("Tenant", backref="budgets")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor = Column(String(255), nullable=True)
    action = Column(String(255), nullable=False)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(255), nullable=True)
    payload_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False)

