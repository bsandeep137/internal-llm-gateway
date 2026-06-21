# Internal LLM Gateway

A self-hosted gateway for routing, authenticating, and monitoring requests to multiple LLM providers.

## Structure

```
internal-llm-gateway/
├── gateway-api/     # FastAPI backend
├── admin-ui/        # Admin dashboard
├── infra/           # Docker Compose, Prometheus, Grafana
├── demo-client/     # CLI demo client
└── docs/            # Architecture and API docs
```

## Quick Start

```bash
cd infra
docker compose up --build
```

The API will be available at `http://localhost:8000`.
