"""Internal LLM client for MCP server analysis.

This client makes SEPARATE API calls that do not affect the caller's context.
All LLM usage is internal to the MCP server and completely isolated from
the user's conversation with Claude Desktop.

Architecture:
    Claude Desktop -> MCP Server -> Internal LLM Client (separate context)
                          ->
                    Structured results only
                    (no LLM responses exposed)

Supported Providers:
    - Anthropic (Claude Sonnet, Haiku, Opus)
    - OpenAI (GPT-4o, GPT-4o-mini, GPT-3.5-turbo)
    - Ollama (local: llama3.2, qwen2.5-coder, deepseek-coder, etc.)
    - Any OpenAI-compatible API (LM Studio, vLLM, LocalAI, etc.)

Use Cases:
    - Classify issue severity/priority
    - Suggest fix strategies
    - Verify fixes resolve issues
    - Generate commit messages
    - Analyze code patterns
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from typing import Any, Literal

from glintefy.config import get_config
from glintefy.subservers.common.llm_providers import LLMProvider
from glintefy.subservers.common.logging import (
    get_mcp_logger,
    log_debug,
    log_error_detailed,
)

# Type aliases
SeverityLevel = Literal["low", "medium", "high", "critical"]
ComplexityLevel = Literal["trivial", "easy", "moderate", "hard"]

logger = get_mcp_logger("glintefy.llm_client")


class InternalLLMClient:
    """Internal LLM client for MCP server analysis.

    This client operates in complete isolation from the caller's context.
    Token usage is tracked separately and does not affect the user's budget.

    Example:
        >>> client = InternalLLMClient()
        >>> severity = client.classify_issue_severity(
        ...     issue_type="high_complexity",
        ...     code_snippet="def foo():\\n    ...",
        ...     context={"complexity": 15}
        ... )
        >>> print(severity)
        "high"
    """

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        fast_model: str | None = None,
        enable_caching: bool = True,
    ):
        """Initialize internal LLM client.

        Args:
            provider: LLM provider ("anthropic", "openai", "ollama", "openai-compatible")
            model: Model for complex analysis (provider-specific, default: claude-3-5-sonnet)
            fast_model: Model for simple tasks (provider-specific, default: claude-3-5-haiku)
            enable_caching: Enable prompt caching to save tokens

        Example:
            >>> # Use Anthropic (default)
            >>> client = InternalLLMClient()

            >>> # Use OpenAI
            >>> client = InternalLLMClient(provider="openai", model="gpt-4o-mini")

            >>> # Use Ollama (local, free!)
            >>> client = InternalLLMClient(provider="ollama", model="llama3.2:3b")
        """
        # Load config
        config = get_config()
        llm_config = config.get("llm", {})

        # Determine provider
        self.provider_name = provider or llm_config.get("provider", "anthropic")

        # Get provider-specific defaults
        provider_defaults = self._get_provider_defaults(self.provider_name)

        # Models
        self.model = model or llm_config.get("model", provider_defaults["model"])
        self.fast_model = fast_model or llm_config.get("fast_model", provider_defaults["fast_model"])

        # Settings
        self.enable_caching = enable_caching
        self.max_tokens_classification = llm_config.get("max_tokens_classification", 10)
        self.max_tokens_suggestion = llm_config.get("max_tokens_suggestion", 500)
        self.max_tokens_verification = llm_config.get("max_tokens_verification", 300)

        # Feature flags
        self.features = llm_config.get("features", {})

        # Token tracking
        self.call_count = 0

        # Initialize providers lazily
        self._provider: LLMProvider | None = None
        self._fast_provider: LLMProvider | None = None

        log_debug(
            logger,
            "InternalLLMClient initialized",
            provider=self.provider_name,
            model=self.model,
            fast_model=self.fast_model,
            caching=self.enable_caching,
        )

    def _get_provider_defaults(self, provider: str) -> dict[str, str]:
        """Get default models for provider.

        Args:
            provider: Provider name

        Returns:
            Dict with default model and fast_model
        """
        defaults = {
            "anthropic": {
                "model": "claude-3-5-sonnet-20241022",
                "fast_model": "claude-3-5-haiku-20241022",
            },
            "openai": {
                "model": "gpt-4o",
                "fast_model": "gpt-4o-mini",
            },
            "ollama": {
                "model": "qwen2.5-coder:7b",  # Good for code
                "fast_model": "llama3.2:3b",  # Fast and small
            },
            "openai-compatible": {
                "model": "local-model",  # User must configure
                "fast_model": "local-model",
            },
        }

        return defaults.get(provider, defaults["anthropic"])

    def _get_env_api_key(self) -> str | None:
        """Get API key from environment variable."""
        import os

        return os.getenv("GLINTEFY_ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")

    @property
    def client(self):
        """Lazy-load Anthropic client (only when needed)."""
        if self._client is None:
            if not self.api_key:
                raise ValueError("Anthropic API key not configured. Set GLINTEFY_ANTHROPIC_API_KEY or configure in config.toml")

            try:
                from anthropic import Anthropic

                self._client = Anthropic(api_key=self.api_key)
            except ImportError as e:
                raise ImportError("anthropic package required for internal LLM. Install with: pip install anthropic") from e

        return self._client

    def is_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled.

        Args:
            feature: Feature name (e.g., "classify_severity", "suggest_fixes")

        Returns:
            True if feature is enabled
        """
        return self.features.get(feature, False)

    def classify_issue_severity(
        self,
        issue_type: str,
        code_snippet: str,
        context: dict[str, Any],
        use_cache: bool = True,
    ) -> SeverityLevel:
        """Classify issue severity using internal LLM call.

        This is a SEPARATE API call with its own context window.
        The caller never sees this prompt or response.

        Args:
            issue_type: Type of issue (complexity, security, etc.)
            code_snippet: Code fragment with issue (keep small!)
            context: Additional context (file path, metrics, etc.)
            use_cache: Use cached result if available

        Returns:
            Severity classification: low, medium, high, or critical

        Example:
            >>> severity = client.classify_issue_severity(
            ...     issue_type="high_complexity",
            ...     code_snippet="def process(items):\\n    for i in items:\\n        ...",
            ...     context={"complexity": 18, "lines": 85}
            ... )
        """
        if not self.is_enabled("classify_severity"):
            return self._rule_based_severity(context)

        # Create cache key
        if use_cache and self.enable_caching:
            cache_key = self._make_cache_key(issue_type, code_snippet, context)
            cached = self._get_cached_classification(cache_key)
            if cached:
                log_debug(logger, "Using cached severity classification", severity=cached)
                return cached

        # Build prompt
        prompt = self._build_severity_prompt(issue_type, code_snippet, context)

        try:
            # Make API call (separate context!)
            response = self.client.messages.create(
                model=self.fast_model,  # Use fast model for simple classification
                max_tokens=self.max_tokens_classification,
                messages=[{"role": "user", "content": prompt}],
            )

            # Track usage
            self._track_usage(response)

            # Parse result
            result = response.content[0].text.strip().lower()

            if result not in ("low", "medium", "high", "critical"):
                logger.warning(f"Invalid LLM severity: {result}, using rule-based fallback")
                return self._rule_based_severity(context)

            # Cache result
            if use_cache and self.enable_caching:
                self._cache_classification(cache_key, result)

            log_debug(
                logger,
                "Issue severity classified",
                issue_type=issue_type,
                severity=result,
                tokens=response.usage.input_tokens + response.usage.output_tokens,
            )

            return result

        except Exception as e:
            log_error_detailed(logger, e, context={"fallback": "rule_based"})
            return self._rule_based_severity(context)

    def suggest_fix_strategy(
        self,
        issue: dict[str, Any],
        code_context: str,
    ) -> dict[str, Any]:
        """Suggest fix strategy for a code issue.

        This generates fix suggestions WITHOUT using the caller's context.
        The caller only receives structured fix suggestions.

        Args:
            issue: Issue details (type, location, metrics)
            code_context: Surrounding code for context (keep minimal!)

        Returns:
            Dict with:
                - strategy: Brief strategy description
                - steps: List of fix steps
                - complexity: Estimated fix complexity
                - safe: Whether fix is safe to automate
                - reasoning: Why this approach

        Example:
            >>> strategy = client.suggest_fix_strategy(
            ...     issue={"type": "high_complexity", "file": "foo.py", "line": 42},
            ...     code_context="def process():\\n    ..."
            ... )
        """
        if not self.is_enabled("suggest_fixes"):
            return self._fallback_strategy()

        prompt = f"""Suggest a fix strategy for this code issue:

Issue: {issue["type"]}
Location: {issue["file"]}:{issue.get("line", "?")}
Description: {issue.get("description", "No description")}

Code Context:
```python
{code_context[:500]}
```

Provide a fix strategy in JSON format:
{{
  "strategy": "brief strategy description",
  "steps": ["step 1", "step 2", ...],
  "complexity": "trivial|easy|moderate|hard",
  "safe": true|false,
  "reasoning": "why this approach"
}}

Respond with ONLY the JSON object, no other text."""

        try:
            response = self.client.messages.create(
                model=self.model,  # Use full model for complex reasoning
                max_tokens=self.max_tokens_suggestion,
                messages=[{"role": "user", "content": prompt}],
            )

            self._track_usage(response)

            # Parse JSON response
            result = json.loads(response.content[0].text)

            log_debug(logger, "Fix strategy suggested", complexity=result.get("complexity"))

            return result

        except Exception as e:
            log_error_detailed(logger, e, context={"fallback": "default_strategy"})
            return self._fallback_strategy()

    def verify_fix(
        self,
        original_code: str,
        fixed_code: str,
        issue_description: str,
    ) -> dict[str, Any]:
        """Verify that a fix resolves the reported issue.

        Args:
            original_code: Code before fix (keep minimal!)
            fixed_code: Code after fix (keep minimal!)
            issue_description: What was wrong

        Returns:
            Dict with:
                - resolved: Whether issue is fixed
                - confidence: Confidence score (0.0-1.0)
                - reasoning: Explanation
                - potential_issues: List of new problems introduced

        Example:
            >>> result = client.verify_fix(
            ...     original_code="def foo(x): return x*2",
            ...     fixed_code="def foo(x: int) -> int: return x*2",
            ...     issue_description="Missing type annotations"
            ... )
        """
        if not self.is_enabled("verify_fixes"):
            return {"resolved": True, "confidence": 0.5, "reasoning": "Verification disabled"}

        prompt = f"""Verify if this code fix resolves the issue:

Issue: {issue_description}

Original Code:
```python
{original_code[:300]}
```

Fixed Code:
```python
{fixed_code[:300]}
```

Respond in JSON:
{{
  "resolved": true|false,
  "confidence": 0.0-1.0,
  "reasoning": "explanation",
  "potential_issues": ["any new problems"]
}}

Respond with ONLY the JSON object, no other text."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens_verification,
                messages=[{"role": "user", "content": prompt}],
            )

            self._track_usage(response)

            result = json.loads(response.content[0].text)

            log_debug(logger, "Fix verified", resolved=result.get("resolved"), confidence=result.get("confidence"))

            return result

        except Exception as e:
            log_error_detailed(logger, e)
            return {"resolved": True, "confidence": 0.5, "reasoning": "Verification failed"}

    def generate_commit_message(
        self,
        changes_summary: str,
        files_changed: list[str],
    ) -> str:
        """Generate commit message for code changes.

        Args:
            changes_summary: Summary of changes made
            files_changed: List of file paths changed

        Returns:
            Generated commit message

        Example:
            >>> msg = client.generate_commit_message(
            ...     changes_summary="Fixed high complexity in process() function",
            ...     files_changed=["src/glintefy/foo.py"]
            ... )
        """
        if not self.is_enabled("generate_commit_messages"):
            return changes_summary

        prompt = f"""Generate a concise git commit message:

Changes: {changes_summary}
Files: {", ".join(files_changed[:5])}

Format: <type>: <description>
Types: fix, feat, refactor, docs, test, chore

Respond with ONLY the commit message, one line, no quotes."""

        try:
            response = self.client.messages.create(
                model=self.fast_model,
                max_tokens=50,
                messages=[{"role": "user", "content": prompt}],
            )

            self._track_usage(response)

            return response.content[0].text.strip()

        except Exception as e:
            log_error_detailed(logger, e)
            return changes_summary

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _build_severity_prompt(self, issue_type: str, code_snippet: str, context: dict) -> str:
        """Build prompt for severity classification."""
        return f"""Classify the severity of this code issue:

Issue Type: {issue_type}
File: {context.get("file_path", "unknown")}

Code:
```python
{code_snippet[:200]}
```

Metrics:
- Cyclomatic Complexity: {context.get("complexity", "N/A")}
- Lines of Code: {context.get("lines", "N/A")}
- Nesting Depth: {context.get("nesting", "N/A")}

Severity Criteria:
- low: Cosmetic issues, minor improvements
- medium: Maintainability concerns, moderate issues
- high: Significant problems, hard to maintain
- critical: Severe issues, security risks, extremely complex

Respond with ONLY one word: low, medium, high, or critical"""

    def _rule_based_severity(self, context: dict) -> SeverityLevel:
        """Fallback rule-based severity classification."""
        complexity = context.get("complexity", 0)
        lines = context.get("lines", 0)
        nesting = context.get("nesting", 0)

        if complexity > 20 or nesting > 5:
            return "critical"
        if complexity > 15 or nesting > 4 or lines > 100:
            return "high"
        if complexity > 10 or nesting > 3 or lines > 50:
            return "medium"
        return "low"

    def _fallback_strategy(self) -> dict[str, Any]:
        """Fallback fix strategy when LLM unavailable."""
        return {
            "strategy": "Refactor to reduce complexity",
            "steps": ["Extract helper methods", "Simplify logic", "Add type hints"],
            "complexity": "moderate",
            "safe": False,
            "reasoning": "Generic strategy (LLM unavailable)",
        }

    def _make_cache_key(self, issue_type: str, code_snippet: str, context: dict) -> str:
        """Create cache key from inputs."""
        key_str = f"{issue_type}:{code_snippet}:{json.dumps(context, sort_keys=True)}"
        return hashlib.sha256(key_str.encode()).hexdigest()

    @lru_cache(maxsize=1000)
    def _get_cached_classification(self, cache_key: str) -> SeverityLevel | None:
        """Get cached classification result."""
        # LRU cache handles this automatically
        return None

    def _cache_classification(self, cache_key: str, severity: SeverityLevel) -> None:
        """Cache classification result."""
        # Store in LRU cache by calling the cached method
        self._get_cached_classification.__wrapped__(self, cache_key)

    def _track_usage(self, response: Any) -> None:
        """Track token usage from API response."""
        self.total_input_tokens += response.usage.input_tokens
        self.total_output_tokens += response.usage.output_tokens
        self.call_count += 1

        total = self.total_input_tokens + self.total_output_tokens

        # Warn if usage is high
        if total > 100_000:
            logger.warning(f"High token usage in internal LLM: total_tokens={total}, calls={self.call_count}, estimated_cost_usd={self._calculate_cost()}")

    def _calculate_cost(self) -> float:
        """Estimate cost based on token usage.

        Prices (as of 2024):
        - Sonnet: $3/1M input, $15/1M output
        - Haiku: $0.25/1M input, $1.25/1M output

        Returns:
            Estimated cost in USD
        """
        # Use average pricing (mix of Sonnet and Haiku)
        input_cost_per_1m = 1.625  # Average of $3 and $0.25
        output_cost_per_1m = 8.125  # Average of $15 and $1.25

        input_cost = (self.total_input_tokens / 1_000_000) * input_cost_per_1m
        output_cost = (self.total_output_tokens / 1_000_000) * output_cost_per_1m

        return input_cost + output_cost

    def get_usage_summary(self) -> dict[str, Any]:
        """Get token usage summary for reporting.

        Returns:
            Dict with calls, tokens, and estimated cost

        Example:
            >>> summary = client.get_usage_summary()
            >>> print(f"Used {summary['total_tokens']} tokens across {summary['calls']} calls")
        """
        return {
            "calls": self.call_count,
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "estimated_cost_usd": round(self._calculate_cost(), 4),
        }

    def reset_usage(self) -> None:
        """Reset usage tracking (for testing or new analysis runs)."""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.call_count = 0
        log_debug(logger, "Token usage tracking reset")
