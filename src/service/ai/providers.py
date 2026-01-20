"""
AI Provider implementations.

Supports multiple AI backends:
- OpenAI (GPT-4, GPT-3.5)
- Ollama (local models like llama3.2, mistral, etc.)
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class AIResponse:
    """AI response wrapper."""

    content: str
    model: str
    provider: str
    tokens_used: int | None = None
    finish_reason: str | None = None


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        ...

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> AIResponse:
        """
        Generate AI response.

        Args:
            prompt: User prompt
            system: System prompt (optional)
            temperature: Creativity (0-1)
            max_tokens: Maximum response tokens

        Returns:
            AIResponse with generated content
        """
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if provider is available."""
        ...


class OpenAIProvider(AIProvider):
    """OpenAI (ChatGPT) provider."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        return "openai"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=60.0,
            )
        return self._client

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> AIResponse:
        """Generate response using OpenAI API."""
        client = await self._get_client()

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await client.post(
                "/chat/completions",
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()

            return AIResponse(
                content=data["choices"][0]["message"]["content"],
                model=self.model,
                provider=self.name,
                tokens_used=data.get("usage", {}).get("total_tokens"),
                finish_reason=data["choices"][0].get("finish_reason"),
            )
        except httpx.HTTPError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
        except (KeyError, IndexError) as e:
            logger.error(f"OpenAI response parsing error: {e}")
            raise

    async def is_available(self) -> bool:
        """Check if OpenAI API is accessible."""
        if not self.api_key:
            return False
        try:
            client = await self._get_client()
            response = await client.get("/models")
            return response.status_code == 200
        except Exception:
            return False

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


class OllamaProvider(AIProvider):
    """Ollama (local LLM) provider."""

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "llama3.2",
    ):
        self.host = host.rstrip("/")
        self.model = model
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        return "ollama"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.host,
                timeout=120.0,  # Ollama can be slow
            )
        return self._client

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> AIResponse:
        """Generate response using Ollama API."""
        client = await self._get_client()

        try:
            response = await client.post(
                "/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "system": system or "",
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()

            return AIResponse(
                content=data.get("response", ""),
                model=self.model,
                provider=self.name,
                tokens_used=data.get("eval_count"),
                finish_reason="stop" if data.get("done") else None,
            )
        except httpx.HTTPError as e:
            logger.error(f"Ollama API error: {e}")
            raise
        except (KeyError, ValueError) as e:
            logger.error(f"Ollama response parsing error: {e}")
            raise

    async def is_available(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            if response.status_code != 200:
                return False

            data = response.json()
            models = [m.get("name", "").split(":")[0] for m in data.get("models", [])]
            return self.model.split(":")[0] in models
        except Exception:
            return False

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


class AIService:
    """
    AI Service with fallback support.

    Tries providers in order until one succeeds.
    """

    def __init__(self, providers: list[AIProvider] | None = None):
        self.providers = providers or []
        self._available_provider: AIProvider | None = None

    def add_provider(self, provider: AIProvider):
        """Add a provider to the list."""
        self.providers.append(provider)

    async def get_available_provider(self) -> AIProvider | None:
        """Get first available provider."""
        for provider in self.providers:
            if await provider.is_available():
                return provider
        return None

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> AIResponse | None:
        """
        Generate AI response using available provider.

        Tries providers in order until one succeeds.

        Returns:
            AIResponse or None if no provider available
        """
        for provider in self.providers:
            try:
                if not await provider.is_available():
                    logger.debug(f"Provider {provider.name} not available, skipping")
                    continue

                logger.info(f"Using AI provider: {provider.name}")
                return await provider.generate(
                    prompt=prompt,
                    system=system,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except Exception as e:
                logger.warning(f"Provider {provider.name} failed: {e}")
                continue

        logger.error("No AI provider available")
        return None

    async def close(self):
        """Close all providers."""
        for provider in self.providers:
            if hasattr(provider, "close"):
                await provider.close()

    @property
    def is_configured(self) -> bool:
        """Check if any provider is configured."""
        return len(self.providers) > 0


def create_ai_service(
    ai_enabled: bool = False,
    ai_provider: str = "ollama",
    openai_api_key: str = "",
    ollama_host: str = "http://localhost:11434",
    ollama_model: str = "llama3.2",
    openai_model: str = "gpt-4o-mini",
) -> AIService:
    """
    Factory function to create AI service from config.

    Args:
        ai_enabled: Whether AI is enabled
        ai_provider: Primary provider ("ollama" or "openai")
        openai_api_key: OpenAI API key
        ollama_host: Ollama server URL
        ollama_model: Ollama model name
        openai_model: OpenAI model name

    Returns:
        Configured AIService
    """
    service = AIService()

    if not ai_enabled:
        return service

    # Add providers based on preference
    if ai_provider == "openai" and openai_api_key:
        service.add_provider(OpenAIProvider(api_key=openai_api_key, model=openai_model))
        # Add Ollama as fallback
        service.add_provider(OllamaProvider(host=ollama_host, model=ollama_model))
    else:
        # Ollama first (or default)
        service.add_provider(OllamaProvider(host=ollama_host, model=ollama_model))
        # Add OpenAI as fallback if configured
        if openai_api_key:
            service.add_provider(OpenAIProvider(api_key=openai_api_key, model=openai_model))

    return service
