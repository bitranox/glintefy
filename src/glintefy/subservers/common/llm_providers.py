"""LLM Provider Abstraction Layer.

Supports multiple LLM providers:
- Anthropic (Claude)
- OpenAI (GPT)
- Local LLM servers (Ollama, LM Studio, vLLM, etc.)
- Any OpenAI-compatible API

This allows the MCP server to use whatever LLM backend you prefer,
without being locked into a single provider.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Literal

from glintefy.subservers.common.logging import get_mcp_logger

logger = get_mcp_logger("glintefy.llm_providers")

# Type aliases
SeverityLevel = Literal["low", "medium", "high", "critical"]


class LLMProvider(ABC):
    """Abstract base class for LLM providers.

    All providers must implement:
    - complete(): Send prompt and get text response
    - count_tokens(): Estimate token usage (optional)
    """

    def __init__(self, model: str, api_key: str | None = None):
        """Initialize provider.

        Args:
            model: Model identifier (provider-specific)
            api_key: API key (if required)
        """
        self.model = model
        self.api_key = api_key
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    @abstractmethod
    def complete(
        self,
        prompt: str,
        max_tokens: int = 100,
        temperature: float = 0.0,
        system_prompt: str | None = None,
    ) -> tuple[str, int, int]:
        """Complete a prompt.

        Args:
            prompt: User prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 = deterministic)
            system_prompt: Optional system prompt

        Returns:
            Tuple of (response_text, input_tokens, output_tokens)
        """

    def count_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation).

        Args:
            text: Text to count

        Returns:
            Estimated token count
        """
        # Rough approximation: 1 token ~ 4 characters
        return len(text) // 4

    def get_usage(self) -> dict[str, int]:
        """Get cumulative token usage.

        Returns:
            Dict with input_tokens, output_tokens, total_tokens
        """
        return {
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
        }


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider."""

    def __init__(self, model: str = "claude-3-5-sonnet-20241022", api_key: str | None = None):
        """Initialize Anthropic provider.

        Args:
            model: Claude model (sonnet, haiku, opus)
            api_key: Anthropic API key
        """
        super().__init__(model, api_key)
        self._client = None

    @property
    def client(self):
        """Lazy-load Anthropic client."""
        if self._client is None:
            try:
                from anthropic import Anthropic

                self._client = Anthropic(api_key=self.api_key)
            except ImportError as e:
                raise ImportError("anthropic package required. Install: pip install anthropic") from e

        return self._client

    def complete(
        self,
        prompt: str,
        max_tokens: int = 100,
        temperature: float = 0.0,
        system_prompt: str | None = None,
    ) -> tuple[str, int, int]:
        """Complete prompt using Anthropic API."""
        messages = [{"role": "user", "content": prompt}]

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        response = self.client.messages.create(**kwargs)

        # Track usage
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

        return response.content[0].text, input_tokens, output_tokens


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider."""

    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None):
        """Initialize OpenAI provider.

        Args:
            model: OpenAI model (gpt-4o, gpt-4o-mini, gpt-3.5-turbo, etc.)
            api_key: OpenAI API key
        """
        super().__init__(model, api_key)
        self._client = None

    @property
    def client(self):
        """Lazy-load OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI

                self._client = OpenAI(api_key=self.api_key)
            except ImportError as e:
                raise ImportError("openai package required. Install: pip install openai") from e

        return self._client

    def complete(
        self,
        prompt: str,
        max_tokens: int = 100,
        temperature: float = 0.0,
        system_prompt: str | None = None,
    ) -> tuple[str, int, int]:
        """Complete prompt using OpenAI API."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        # Track usage
        input_tokens = response.usage.prompt_tokens if response.usage else self.count_tokens(prompt)
        output_tokens = response.usage.completion_tokens if response.usage else self.count_tokens(response.choices[0].message.content or "")
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

        return response.choices[0].message.content or "", input_tokens, output_tokens


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider.

    Ollama runs models locally on your machine.
    Install: https://ollama.com/

    Example models:
    - llama3.2:3b (fast, small)
    - qwen2.5-coder:7b (code-focused)
    - deepseek-coder-v2:16b (larger, better)
    """

    def __init__(self, model: str = "llama3.2:3b", base_url: str = "http://localhost:11434"):
        """Initialize Ollama provider.

        Args:
            model: Ollama model name
            base_url: Ollama API base URL
        """
        super().__init__(model, api_key=None)
        self.base_url = base_url.rstrip("/")
        self._client = None

    @property
    def client(self):
        """Lazy-load Ollama client."""
        if self._client is None:
            try:
                import requests

                self._client = requests
            except ImportError as e:
                raise ImportError("requests package required. Install: pip install requests") from e

        return self._client

    def complete(
        self,
        prompt: str,
        max_tokens: int = 100,
        temperature: float = 0.0,
        system_prompt: str | None = None,
    ) -> tuple[str, int, int]:
        """Complete prompt using Ollama API."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }

        try:
            response = self.client.post(f"{self.base_url}/api/chat", json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()

            # Estimate tokens (Ollama doesn't always return usage)
            input_tokens = self.count_tokens(prompt)
            output_text = data.get("message", {}).get("content", "")
            output_tokens = self.count_tokens(output_text)

            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens

            return output_text, input_tokens, output_tokens

        except Exception as e:
            logger.warning(f"Ollama API error: {e}")
            raise


class OpenAICompatibleProvider(LLMProvider):
    """OpenAI-compatible API provider.

    Works with:
    - LM Studio (local)
    - vLLM (self-hosted)
    - LocalAI (local)
    - Together AI (cloud)
    - Any server implementing OpenAI's chat completions API
    """

    def __init__(
        self,
        model: str,
        base_url: str,
        api_key: str | None = None,
    ):
        """Initialize OpenAI-compatible provider.

        Args:
            model: Model identifier (server-specific)
            base_url: API base URL (e.g., http://localhost:1234/v1)
            api_key: API key (optional for local servers)
        """
        super().__init__(model, api_key)
        self.base_url = base_url.rstrip("/")
        self._client = None

    @property
    def client(self):
        """Lazy-load OpenAI client with custom base URL."""
        if self._client is None:
            try:
                from openai import OpenAI

                self._client = OpenAI(api_key=self.api_key or "not-needed", base_url=self.base_url)
            except ImportError as e:
                raise ImportError("openai package required. Install: pip install openai") from e

        return self._client

    def complete(
        self,
        prompt: str,
        max_tokens: int = 100,
        temperature: float = 0.0,
        system_prompt: str | None = None,
    ) -> tuple[str, int, int]:
        """Complete prompt using OpenAI-compatible API."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        # Track usage (fallback to estimation if not provided)
        input_tokens = response.usage.prompt_tokens if response.usage else self.count_tokens(prompt)
        output_tokens = response.usage.completion_tokens if response.usage else self.count_tokens(response.choices[0].message.content or "")
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

        return response.choices[0].message.content or "", input_tokens, output_tokens


def create_provider(config: dict[str, Any]) -> LLMProvider:
    """Factory function to create LLM provider from config.

    Args:
        config: Provider configuration dict with:
            - provider: "anthropic", "openai", "ollama", "openai-compatible"
            - model: Model identifier
            - api_key: API key (if needed)
            - base_url: Base URL (for local/compatible providers)

    Returns:
        Configured LLM provider instance

    Example:
        >>> config = {"provider": "ollama", "model": "llama3.2:3b"}
        >>> provider = create_provider(config)
    """
    provider_type = config.get("provider", "anthropic").lower()

    if provider_type == "anthropic":
        return AnthropicProvider(
            model=config.get("model", "claude-3-5-sonnet-20241022"),
            api_key=config.get("api_key"),
        )

    if provider_type == "openai":
        return OpenAIProvider(
            model=config.get("model", "gpt-4o-mini"),
            api_key=config.get("api_key"),
        )

    if provider_type == "ollama":
        return OllamaProvider(
            model=config.get("model", "llama3.2:3b"),
            base_url=config.get("base_url", "http://localhost:11434"),
        )

    if provider_type in ("openai-compatible", "compatible", "custom"):
        if "base_url" not in config:
            raise ValueError("base_url required for openai-compatible provider")

        return OpenAICompatibleProvider(
            model=config["model"],
            base_url=config["base_url"],
            api_key=config.get("api_key"),
        )

    raise ValueError(f"Unknown provider: {provider_type}. Supported: anthropic, openai, ollama, openai-compatible")


def get_provider_cost(provider: str, model: str) -> dict[str, float]:
    """Get cost per 1M tokens for provider/model.

    Args:
        provider: Provider name
        model: Model name

    Returns:
        Dict with input_cost and output_cost per 1M tokens (USD)
    """
    # Prices as of January 2025 (approximate)
    costs = {
        "anthropic": {
            "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
            "claude-3-5-haiku-20241022": {"input": 0.25, "output": 1.25},
            "claude-3-opus-20240229": {"input": 15.0, "output": 75.0},
        },
        "openai": {
            "gpt-4o": {"input": 2.5, "output": 10.0},
            "gpt-4o-mini": {"input": 0.15, "output": 0.6},
            "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
        },
        "ollama": {
            "default": {"input": 0.0, "output": 0.0},  # Local = free!
        },
        "openai-compatible": {
            "default": {"input": 0.0, "output": 0.0},  # Assume free (local)
        },
    }

    provider_costs = costs.get(provider, {})
    model_cost = provider_costs.get(model, provider_costs.get("default", {"input": 0.0, "output": 0.0}))

    return {"input_cost": model_cost["input"], "output_cost": model_cost["output"]}
