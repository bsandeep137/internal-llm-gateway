import time
import os
import httpx
from app.providers.base import BaseProviderAdapter, ChatRequest, ChatResponse

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

SUPPORTED_MODELS = {
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-2.0-flash",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
}

# Map OpenAI-style roles to Gemini roles
_ROLE_MAP = {
    "user": "user",
    "assistant": "model",
    "system": "user",  # Gemini doesn't have a system role; prepend as first user turn
}


class GeminiAdapter(BaseProviderAdapter):
    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY", "")

    @property
    def provider_name(self) -> str:
        return "gemini"

    def supports_model(self, model: str) -> bool:
        return model in SUPPORTED_MODELS

    async def chat(self, request: ChatRequest) -> ChatResponse:
        # Convert messages to Gemini's `contents` format
        contents = []
        system_parts = []

        for msg in request.messages:
            if msg.role == "system":
                # Collect system instructions to prepend as first user message
                system_parts.append(msg.content)
            else:
                contents.append({
                    "role": _ROLE_MAP.get(msg.role, "user"),
                    "parts": [{"text": msg.content}],
                })

        # Prepend system prompt as a user turn if present
        if system_parts:
            system_text = "\n".join(system_parts)
            contents.insert(0, {"role": "user", "parts": [{"text": system_text}]})

        body: dict = {"contents": contents}

        generation_config: dict = {}
        if request.max_tokens is not None:
            generation_config["maxOutputTokens"] = request.max_tokens
        if request.temperature is not None:
            generation_config["temperature"] = request.temperature
        if generation_config:
            body["generationConfig"] = generation_config

        url = f"{GEMINI_API_BASE}/{request.model}:generateContent?key={self._api_key}"

        start = time.monotonic()
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=body)
            resp.raise_for_status()
        latency_ms = int((time.monotonic() - start) * 1000)

        data = resp.json()
        candidate = data["candidates"][0]
        content_text = candidate["content"]["parts"][0]["text"]

        usage = data.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", 0)
        completion_tokens = usage.get("candidatesTokenCount", 0)

        return ChatResponse(
            provider=self.provider_name,
            model=request.model,
            content=content_text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
        )
