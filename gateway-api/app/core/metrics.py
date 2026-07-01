"""
Central Prometheus metrics registry for the LLM Gateway.
Import from here to avoid duplicate metric registration on hot-reload.
"""
from prometheus_client import Counter, Histogram, Gauge

# ---------------------------------------------------------------------------
# HTTP layer
# ---------------------------------------------------------------------------

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# ---------------------------------------------------------------------------
# LLM gateway
# ---------------------------------------------------------------------------

LLM_REQUESTS_TOTAL = Counter(
    "llm_requests_total",
    "LLM chat completion requests",
    ["provider", "model", "status"],
)

LLM_TOKENS_TOTAL = Counter(
    "llm_tokens_total",
    "LLM tokens used",
    ["provider", "model", "type"],  # type: prompt | completion
)

LLM_COST_DOLLARS_TOTAL = Counter(
    "llm_cost_dollars_total",
    "Estimated LLM cost in USD",
    ["provider", "model"],
)

LLM_LATENCY_SECONDS = Histogram(
    "llm_latency_seconds",
    "Provider call latency",
    ["provider", "model"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

POLICY_REJECTIONS_TOTAL = Counter(
    "policy_rejections_total",
    "Requests rejected by policy",
    ["reason"],
)

BUDGET_REJECTIONS_TOTAL = Counter(
    "budget_rejections_total",
    "Requests rejected by budget",
    ["reason"],
)

RATE_LIMIT_REJECTIONS_TOTAL = Counter(
    "rate_limit_rejections_total",
    "Requests rejected by rate limit",
    [],
)

REDACTIONS_TOTAL = Counter(
    "redactions_total",
    "PII items redacted from prompts",
    ["sensitivity"],
)
