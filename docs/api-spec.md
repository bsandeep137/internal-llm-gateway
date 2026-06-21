# API Specification

## Base URL

`http://localhost:8000`

## Endpoints

### `GET /health`
Returns the health status of the gateway.

**Response**
```json
{ "status": "ok" }
```

### `POST /v1/completions`
Send a completion request to the configured LLM provider.

**Request Body**
```json
{
  "prompt": "string",
  "model": "string"
}
```
