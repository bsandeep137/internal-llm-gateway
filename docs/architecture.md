# Architecture

## Overview

The Internal LLM Gateway is a self-hosted proxy that provides a unified API interface over multiple LLM providers, with authentication, rate limiting, cost tracking, and observability.

## Components

- **gateway-api** — FastAPI backend handling routing, auth, rate limiting, and provider abstraction.
- **admin-ui** — Web dashboard for managing API keys, viewing usage, and configuring routing rules.
- **infra** — Docker Compose stack with Prometheus and Grafana for metrics/monitoring.
- **demo-client** — CLI tool for testing the gateway locally.
