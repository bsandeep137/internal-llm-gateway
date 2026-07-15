from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class ChatRequest:
    model: str
    messages: list[ChatMessage]
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None


@dataclass
class ChatResponse:
    provider: str
    model: str
    content: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int


class BaseProviderAdapter(ABC):
    """Abstract interface every provider adapter must implement."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier for this provider (e.g. 'openai', 'mock')."""

    @abstractmethod
    def supports_model(self, model: str) -> bool:
        """Return True if this adapter can serve the requested model."""

    @abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Send a chat completion request and return a normalised response."""
