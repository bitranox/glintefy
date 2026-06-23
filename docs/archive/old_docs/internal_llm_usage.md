# Internal LLM Usage in MCP Servers

## Overview

MCP servers can use LLMs internally for classification, analysis, and result verification **without affecting the caller's context window**. The MCP protocol ensures complete context isolation.

## Architecture: Context Isolation

```
┌─────────────────────────────────────────────────────────────┐
│ Claude Desktop / MCP Client                                 │
│                                                              │
│  User's Conversation Context:                               │
│  ├─ User messages                                           │
│  ├─ Assistant responses                                     │
│  └─ Tool results from MCP server (structured data only)    │
│                                                              │
└─────────────────┬───────────────────────────────────────────┘
                  │ MCP Protocol (stdio/SSE)
                  │ Tool calls: review_quality({...})
                  │ Tool results: {"status": "SUCCESS", ...}
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ glintefy-review MCP Server                                       │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ ReviewMCPServer                                        │ │
│  │  ├─ handle_tool_call()                                │ │
│  │  └─ run_quality() → QualitySubServer                  │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Internal LLM Client (ISOLATED)                         │ │
│  │                                                         │ │
│  │  Separate Anthropic API Client:                        │ │
│  │  ├─ Own API key                                        │ │
│  │  ├─ Own context window                                 │ │
│  │  ├─ Own conversation state                             │ │
│  │  └─ No connection to caller's context                  │ │
│  │                                                         │ │
│  │  Use Cases:                                             │ │
│  │  ├─ Classify issue severity                            │ │
│  │  ├─ Suggest fix strategies                             │ │
│  │  ├─ Verify fix correctness                             │ │
│  │  ├─ Generate commit messages                           │ │
│  │  └─ Analyze code patterns                              │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Key Principles

### 1. Complete Context Isolation
- **Caller's context**: User conversation with Claude Desktop
- **Server's context**: Separate API calls for internal analysis
- **No sharing**: MCP protocol only passes structured data (JSON)

### 2. Token Efficiency
- Server LLM calls use **separate token budget**
- Caller only sees **summarized results** (not full LLM responses)
- No context window pollution

### 3. Privacy
- Server has no access to caller's conversation history
- Caller has no access to server's internal LLM prompts/responses
- Only structured tool results cross the boundary

## Implementation Patterns

### Pattern 1: Issue Classification

**Use Case**: Classify code issues by severity, category, or fixability

```python
# src/glintefy/subservers/common/llm_client.py

from anthropic import Anthropic
from typing import Literal

class InternalLLMClient:
    """Internal LLM client for MCP server analysis.

    This client makes SEPARATE API calls that do not affect
    the caller's context window. All LLM usage is internal
    to the MCP server.
    """

    def __init__(self, api_key: str | None = None, model: str = "claude-3-5-sonnet-20241022"):
        """Initialize internal LLM client.

        Args:
            api_key: Anthropic API key (reads from env if None)
            model: Model to use for internal analysis
        """
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.logger = get_mcp_logger("glintefy.llm_client")

    def classify_issue_severity(
        self,
        issue_type: str,
        code_snippet: str,
        context: dict,
    ) -> Literal["low", "medium", "high", "critical"]:
        """Classify issue severity using internal LLM call.

        This is a SEPARATE API call with its own context.
        The caller never sees this prompt or response.

        Args:
            issue_type: Type of issue (complexity, security, etc.)
            code_snippet: Code fragment with issue
            context: Additional context (file path, metrics, etc.)

        Returns:
            Severity classification
        """
        prompt = f"""Classify the severity of this code issue:

Issue Type: {issue_type}
File: {context.get('file_path', 'unknown')}

Code:
```python
{code_snippet}
```

Context:
- Cyclomatic Complexity: {context.get('complexity', 'N/A')}
- Lines of Code: {context.get('lines', 'N/A')}
- Nesting Depth: {context.get('nesting', 'N/A')}

Respond with ONLY one word: low, medium, high, or critical"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}],
        )

        result = response.content[0].text.strip().lower()

        # Log for debugging (stderr only in MCP mode)
        log_debug(
            self.logger,
            "Issue severity classified",
            issue_type=issue_type,
            severity=result,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens,
        )

        if result not in ("low", "medium", "high", "critical"):
            return "medium"  # Default fallback

        return result
```

### Pattern 2: Fix Strategy Suggestion

**Use Case**: Suggest how to fix a code issue

```python
def suggest_fix_strategy(
    self,
    issue: dict,
    code_context: str,
) -> dict:
    """Suggest fix strategy for a code issue.

    This generates fix suggestions WITHOUT using the caller's context.
    The caller only receives structured fix suggestions.

    Args:
        issue: Issue details (type, location, metrics)
        code_context: Surrounding code for context

    Returns:
        Dict with fix strategy, steps, and estimated complexity
    """
    prompt = f"""Suggest a fix strategy for this code issue:

Issue: {issue['type']}
Location: {issue['file']}:{issue['line']}
Description: {issue['description']}

Code Context:
```python
{code_context}
```

Provide a fix strategy in JSON format:
{{
  "strategy": "brief strategy description",
  "steps": ["step 1", "step 2", ...],
  "complexity": "trivial|easy|moderate|hard",
  "safe": true|false,
  "reasoning": "why this approach"
}}"""

    response = self.client.messages.create(
        model=self.model,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )

    import json
    return json.loads(response.content[0].text)
```

### Pattern 3: Result Verification

**Use Case**: Verify that a fix actually resolves the issue

```python
def verify_fix(
    self,
    original_code: str,
    fixed_code: str,
    issue_description: str,
) -> dict:
    """Verify that a fix resolves the reported issue.

    Args:
        original_code: Code before fix
        fixed_code: Code after fix
        issue_description: What was wrong

    Returns:
        Verification result with confidence score
    """
    prompt = f"""Verify if this code fix resolves the issue:

Issue: {issue_description}

Original Code:
```python
{original_code}
```

Fixed Code:
```python
{fixed_code}
```

Respond in JSON:
{{
  "resolved": true|false,
  "confidence": 0.0-1.0,
  "reasoning": "explanation",
  "potential_issues": ["any new problems"]
}}"""

    response = self.client.messages.create(
        model=self.model,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )

    import json
    return json.loads(response.content[0].text)
```

## Configuration

Add to `defaultconfig.toml`:

```toml
# =============================================================================
# INTERNAL LLM CONFIGURATION
# =============================================================================

[llm]
# Enable internal LLM usage for analysis enhancement
enable_internal_llm = false

# Anthropic API key (or set GLINTEFY_ANTHROPIC_API_KEY env var)
# Leave empty to read from environment
anthropic_api_key = ""

# Model to use for internal analysis
model = "claude-3-5-sonnet-20241022"

# Use faster model for simple classification tasks
fast_model = "claude-3-5-haiku-20241022"

# Maximum tokens for internal LLM calls
max_tokens_classification = 10
max_tokens_suggestion = 500
max_tokens_verification = 300

# Rate limiting (calls per minute)
rate_limit = 60

# Cache prompts for repeated analysis (saves tokens)
enable_prompt_caching = true

# Use cases to enable
[llm.features]
classify_severity = true        # Classify issue severity with LLM
suggest_fixes = false           # Suggest fix strategies (more expensive)
verify_fixes = false            # Verify fixes resolve issues (future)
generate_commit_messages = true # Generate commit messages
analyze_patterns = false        # Pattern analysis (experimental)
```

## Integration Example

### QualitySubServer with LLM Enhancement

```python
# src/glintefy/subservers/review/quality/__init__.py

from glintefy.subservers.common.llm_client import InternalLLMClient

class QualitySubServer(BaseSubServer):
    def __init__(self, ..., enable_llm: bool | None = None):
        super().__init__(...)

        # Load config
        config = get_config()
        llm_enabled = enable_llm if enable_llm is not None else config.get("llm", {}).get("enable_internal_llm", False)

        # Initialize internal LLM client if enabled
        self.llm_client = None
        if llm_enabled:
            api_key = config.get("llm", {}).get("anthropic_api_key") or None
            self.llm_client = InternalLLMClient(api_key=api_key)
            log_debug(self.logger, "Internal LLM client enabled")

    def _analyze_complexity_issues(self, issues: list[dict]) -> list[dict]:
        """Analyze complexity issues, optionally with LLM enhancement."""

        if self.llm_client and self.llm_client.is_enabled("classify_severity"):
            # Enhance issues with LLM classification
            for issue in issues:
                # Read code snippet
                code_snippet = self._read_code_snippet(
                    issue["file"],
                    issue["line"],
                    context_lines=5
                )

                # Classify with internal LLM (separate context!)
                llm_severity = self.llm_client.classify_issue_severity(
                    issue_type=issue["type"],
                    code_snippet=code_snippet,
                    context={
                        "file_path": issue["file"],
                        "complexity": issue.get("complexity"),
                        "lines": issue.get("lines"),
                        "nesting": issue.get("nesting"),
                    }
                )

                # Add LLM classification (doesn't replace tool-based severity)
                issue["llm_severity"] = llm_severity
                issue["enhanced_by_llm"] = True

        return issues
```

## Cost Management

### Token Usage Tracking

```python
class InternalLLMClient:
    def __init__(self, ...):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.call_count = 0

    def classify_issue_severity(self, ...) -> str:
        response = self.client.messages.create(...)

        # Track usage
        self.total_input_tokens += response.usage.input_tokens
        self.total_output_tokens += response.usage.output_tokens
        self.call_count += 1

        # Log if excessive
        if self.total_input_tokens + self.total_output_tokens > 100000:
            log_warning(
                self.logger,
                "High token usage in internal LLM",
                total_tokens=self.total_input_tokens + self.total_output_tokens,
                calls=self.call_count,
            )

        return result

    def get_usage_summary(self) -> dict:
        """Get token usage summary for reporting."""
        return {
            "calls": self.call_count,
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "estimated_cost_usd": self._calculate_cost(),
        }
```

### Caching Strategy

```python
from functools import lru_cache
import hashlib

class InternalLLMClient:
    @lru_cache(maxsize=1000)
    def _cached_classify(self, prompt_hash: str, prompt: str) -> str:
        """Cached classification to avoid redundant API calls."""
        response = self.client.messages.create(...)
        return response.content[0].text

    def classify_issue_severity(self, ...) -> str:
        # Create cache key from inputs
        cache_key = hashlib.sha256(
            f"{issue_type}:{code_snippet}:{context}".encode()
        ).hexdigest()

        # Use cached result if available
        return self._cached_classify(cache_key, prompt)
```

## Best Practices

### 1. Use LLM Sparingly
- **Static analysis first**: Use traditional tools (ruff, mypy, radon)
- **LLM for ambiguity**: Only when rule-based analysis isn't enough
- **Classify, don't analyze**: Use LLM for high-level decisions, not detailed analysis

### 2. Batch Requests
```python
def classify_multiple_issues(self, issues: list[dict]) -> list[str]:
    """Classify multiple issues in one API call to save tokens."""

    # Batch up to 10 issues per call
    prompt = "Classify severity for these issues:\n\n"
    for i, issue in enumerate(issues[:10]):
        prompt += f"{i+1}. {issue['type']} in {issue['file']}\n"
    prompt += "\nRespond with comma-separated: low,medium,high,..."

    # Single API call for multiple classifications
    response = self.client.messages.create(...)
```

### 3. Fallback Gracefully
```python
def classify_issue_severity(self, ...) -> str:
    try:
        return self._llm_classify(...)
    except Exception as e:
        log_error_detailed(self.logger, e, context={"fallback": True})
        # Fall back to rule-based classification
        return self._rule_based_classify(...)
```

### 4. Report LLM Usage
```python
class SubServerResult:
    llm_usage: dict | None = None  # Token usage if LLM was used

# In quality sub-server
result = SubServerResult(
    status="SUCCESS",
    summary=summary,
    artifacts=artifacts,
    metrics=metrics,
    llm_usage=self.llm_client.get_usage_summary() if self.llm_client else None,
)
```

## Security Considerations

### API Key Management
```toml
# ~/.config/glintefy/config.toml
[llm]
# NEVER commit API keys to git!
anthropic_api_key = "sk-ant-..."
```

Or use environment variable:
```bash
export GLINTEFY_ANTHROPIC_API_KEY="sk-ant-..."
```

### Code Privacy
- **Be careful what you send**: Code snippets may contain sensitive data
- **Minimize context**: Only send essential code fragments
- **User opt-in**: Make LLM usage optional and configurable
- **Log what's sent**: Log code snippets being analyzed (stderr in MCP mode)

## Testing

### Mock LLM Client for Tests
```python
# tests/conftest.py

class MockLLMClient:
    """Mock LLM client for testing without API calls."""

    def classify_issue_severity(self, issue_type, code_snippet, context):
        # Rule-based mock classification
        if context.get("complexity", 0) > 20:
            return "critical"
        elif context.get("complexity", 0) > 10:
            return "high"
        else:
            return "medium"

    def get_usage_summary(self):
        return {"calls": 0, "total_tokens": 0}

@pytest.fixture
def mock_llm_client(monkeypatch):
    monkeypatch.setattr(
        "glintefy.subservers.common.llm_client.InternalLLMClient",
        MockLLMClient,
    )
```

## Summary

### What You Get
✅ **Enhanced analysis** - LLM helps classify and prioritize issues
✅ **Context isolation** - Caller's context is never affected
✅ **Token efficiency** - Only structured results returned to caller
✅ **Cost control** - Configurable, cacheable, with fallbacks
✅ **Privacy** - Separate API client with no connection to caller

### What to Avoid
❌ **Don't send full files** - Extract relevant snippets only
❌ **Don't make it required** - Always have rule-based fallbacks
❌ **Don't ignore costs** - Track and limit token usage
❌ **Don't expose prompts** - Keep internal LLM usage implementation detail

### When to Use Internal LLM
- **Classification**: "Is this issue high priority?"
- **Disambiguation**: "Is this a security issue or just a warning?"
- **Suggestion**: "What's the best fix strategy?"
- **Verification**: "Did this fix work?"
- **Generation**: "Generate a commit message for these changes"

### When NOT to Use Internal LLM
- **Static analysis** - Use ruff, mypy, pylint instead
- **Metrics calculation** - Use radon, traditional tools
- **File operations** - Don't need LLM for git/file operations
- **Simple rules** - If a rule can decide, don't use LLM
