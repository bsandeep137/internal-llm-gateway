import time
from app.providers.base import BaseProviderAdapter, ChatRequest, ChatResponse

MOCK_MODELS = {"mock-gpt", "mock-fast", "mock-slow"}


class MockAdapter(BaseProviderAdapter):
    """
    Deterministic offline adapter for local development and testing.
    Echoes back the last user message and returns fixed token counts.
    """

    @property
    def provider_name(self) -> str:
        return "mock"

    def supports_model(self, model: str) -> bool:
        return model in MOCK_MODELS

    async def chat(self, request: ChatRequest) -> ChatResponse:
        last_user = next(
            (m.content for m in reversed(request.messages) if m.role == "user"),
            "",
        )
        reply = f"[mock] Echo: {last_user}"

        simulated_latency = 50 if request.model != "mock-slow" else 500
        time.sleep(simulated_latency / 1000)

        prompt_tokens = sum(len(m.content.split()) for m in request.messages)
        completion_tokens = len(reply.split())

        return ChatResponse(
            provider=self.provider_name,
            model=request.model,
            content=reply,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=simulated_latency,
        )
