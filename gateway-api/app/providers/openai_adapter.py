import time
import os
import httpx
from app.providers.base import BaseProviderAdapter, ChatRequest, ChatResponse

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

SUPPORTED_MODELS = {
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-3.5-turbo",
}


class OpenAIAdapter(BaseProviderAdapter):
    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")

    @property
    def provider_name(self) -> str:
        return "openai"

    def supports_model(self, model: str) -> bool:
        return model in SUPPORTED_MODELS

    async def chat(self, request: ChatRequest) -> ChatResponse:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": request.model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
        }
        if request.max_tokens is not None:
            body["max_tokens"] = request.max_tokens
        if request.temperature is not None:
            body["temperature"] = request.temperature

        start = time.monotonic()
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(OPENAI_API_URL, json=body, headers=headers)
            resp.raise_for_status()
        latency_ms = int((time.monotonic() - start) * 1000)

        data = resp.json()
        choice = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        return ChatResponse(
            provider=self.provider_name,
            model=data.get("model", request.model),
            content=choice,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            latency_ms=latency_ms,
        )
