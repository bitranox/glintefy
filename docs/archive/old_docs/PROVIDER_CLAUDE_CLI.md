# Using Claude CLI as a Provider

## Overview

Yes! You can use `claude-cli` (or any CLI tool) as an LLM provider by running it in a subprocess. This is a great option for:

✅ **Reusing existing CLI tools** - No need to install Python SDKs
✅ **Flexibility** - Works with any command-line LLM tool
✅ **Simplicity** - Just shell out to existing tools
✅ **Context isolation** - Subprocess has separate context

## Architecture

```
MCP Server (glintefy-review)
    ↓
InternalLLMClient
    ↓
SubprocessProvider
    ↓
$ claude-cli --prompt "Classify severity..."
    ↓
Response captured and parsed
```

## Implementation

Add this to `llm_providers.py`:

```python
class SubprocessProvider(LLMProvider):
    """Run LLM via subprocess (claude-cli, llm, etc.)."""

    def __init__(
        self,
        command: str | list[str],
        model: str | None = None,
        timeout: int = 60,
    ):
        """Initialize subprocess provider.

        Args:
            command: Base command to run (e.g., "claude-cli" or ["llm", "-m", "gpt-4"])
            model: Model name (passed as argument if provided)
            timeout: Subprocess timeout in seconds
        """
        super().__init__(model or "subprocess", api_key=None)
        self.command = command if isinstance(command, list) else [command]
        self.timeout = timeout

    def complete(
        self,
        prompt: str,
        max_tokens: int = 100,
        temperature: float = 0.0,
        system_prompt: str | None = None,
    ) -> tuple[str, int, int]:
        """Complete prompt via subprocess."""
        import subprocess

        # Build command
        cmd = self.command.copy()

        # Add model if specified
        if self.model and self.model != "subprocess":
            cmd.extend(["--model", self.model])

        # Add system prompt if provided
        if system_prompt:
            cmd.extend(["--system", system_prompt])

        # Add main prompt
        cmd.extend(["--prompt", prompt])

        # Add settings
        cmd.extend([
            "--max-tokens", str(max_tokens),
            "--temperature", str(temperature),
        ])

        # Run subprocess
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=True,
            )

            output = result.stdout.strip()

            # Estimate tokens
            input_tokens = self.count_tokens(prompt)
            output_tokens = self.count_tokens(output)

            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens

            return output, input_tokens, output_tokens

        except subprocess.TimeoutExpired as e:
            raise TimeoutError(f"Subprocess timed out after {self.timeout}s") from e

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Subprocess failed: {e.stderr}") from e
```

## Configuration Examples

### Example 1: claude-cli (Anthropic's Official CLI)

Install:
```bash
# Install claude-cli
npm install -g @anthropic-ai/claude-cli

# Or pip version (if available)
pip install claude-cli

# Set API key
export ANTHROPIC_API_KEY="sk-ant-YOUR-KEY"

# Test it
claude-cli --prompt "Hello" --model claude-3-5-haiku-20241022
```

Config:
```toml
# ~/.config/glintefy/config.toml
[llm]
enable_internal_llm = true
provider = "subprocess"

# Command to run
subprocess_command = ["claude-cli"]

# Model to use
model = "claude-3-5-sonnet-20241022"
fast_model = "claude-3-5-haiku-20241022"

[llm.features]
classify_severity = true
```

### Example 2: Simon Willison's `llm` Tool

Install:
```bash
# Install llm (supports many providers)
pip install llm

# Install OpenAI plugin
llm install llm-gpt4all

# Or Anthropic plugin
llm install llm-claude-3

# Set API key
llm keys set openai
# Enter your OpenAI API key

# Test it
llm "Classify severity: high complexity"
```

Config:
```toml
[llm]
enable_internal_llm = true
provider = "subprocess"

# Use llm command
subprocess_command = ["llm", "-m", "gpt-4o-mini"]

# Model specified in command above
model = "gpt-4o-mini"
fast_model = "gpt-4o-mini"
```

### Example 3: aider CLI

```bash
# Install aider (AI coding assistant)
pip install aider-chat

# Configure
export ANTHROPIC_API_KEY="sk-ant-YOUR-KEY"

# Test
aider --message "Classify this code complexity"
```

Config:
```toml
[llm]
provider = "subprocess"
subprocess_command = ["aider", "--yes", "--message"]
model = "claude-3-5-sonnet"
```

### Example 4: Custom Shell Script

Create a wrapper script:

```bash
#!/bin/bash
# ~/bin/my-llm-wrapper.sh

PROMPT="$1"

# Call your preferred LLM tool
curl -s https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "content-type: application/json" \
  -d "{
    \"model\": \"claude-3-5-haiku-20241022\",
    \"max_tokens\": 100,
    \"messages\": [{\"role\": \"user\", \"content\": \"$PROMPT\"}]
  }" | jq -r '.content[0].text'
```

Config:
```toml
[llm]
provider = "subprocess"
subprocess_command = ["~/bin/my-llm-wrapper.sh"]
```

## Advantages

### 1. Reuse Existing Tools
- No need to install Python SDKs
- Use tools you already have configured
- Leverage existing authentication/config

### 2. Isolation
- Subprocess has separate environment
- Can't affect MCP server's memory/state
- Easy to timeout/kill if stuck

### 3. Flexibility
- Works with ANY command-line tool
- Easy to add custom wrappers
- Can pipe through additional processing

### 4. Debugging
- Easy to test commands manually
- Can see exact command being run
- stderr captured for error messages

## Disadvantages

### 1. Slower
- Process startup overhead (~50-200ms)
- No connection pooling
- No response streaming

### 2. Less Control
- Depends on CLI tool's flags
- Harder to parse structured responses
- May need wrapper scripts

### 3. Token Counting
- No accurate token counts (estimated only)
- Can't use prompt caching
- Cost tracking less precise

## When to Use Subprocess Provider

✅ **Good for:**
- Quick prototyping
- Reusing existing CLI tools
- One-off experiments
- When you can't install Python SDKs

❌ **Not recommended for:**
- High-throughput scenarios (slow startup)
- Production (less reliable than direct API)
- When you need streaming responses
- When accurate token counting matters

## Comparison: Direct API vs CLI

| Feature | Direct API | CLI Subprocess |
|---------|-----------|----------------|
| **Speed** | Fast (50-500ms) | Slower (200-800ms) |
| **Overhead** | Low | High (process spawn) |
| **Token Counting** | Accurate | Estimated |
| **Streaming** | Yes | No |
| **Caching** | Yes (prompt cache) | No |
| **Setup** | Install SDK | Install CLI tool |
| **Debugging** | Harder | Easy (test in shell) |
| **Reliability** | High | Medium |

## Recommendation

**For Development:**
```toml
# Use claude-cli for quick iteration
[llm]
provider = "subprocess"
subprocess_command = ["claude-cli"]
```

**For Production:**
```toml
# Use direct API for better performance
[llm]
provider = "anthropic"  # Direct API call
```

**For Local/Free:**
```toml
# Use Ollama (direct API, but local)
[llm]
provider = "ollama"
```

## Complete Example

```python
# Test subprocess provider
from glintefy.subservers.common.llm_providers import SubprocessProvider

# Create provider
provider = SubprocessProvider(
    command=["claude-cli"],
    model="claude-3-5-haiku-20241022",
    timeout=30,
)

# Use it
response, input_tokens, output_tokens = provider.complete(
    prompt="Classify severity of: complexity=18",
    max_tokens=10,
)

print(f"Response: {response}")
print(f"Tokens: {input_tokens} in, {output_tokens} out")
print(f"Cost: ${(input_tokens * 0.25 + output_tokens * 1.25) / 1_000_000:.6f}")
```

## Other CLI Tools You Can Use

| Tool | Install | Use Case |
|------|---------|----------|
| `claude-cli` | npm/pip | Official Anthropic CLI |
| `llm` | pip | Multi-provider (OpenAI, Claude, local) |
| `aider` | pip | AI coding assistant |
| `gpt` | npm | OpenAI CLI |
| `ollama` | Binary | Local models CLI |
| `chatgpt-cli` | npm | ChatGPT CLI |
| Custom script | Any | Wrap any API |

## Summary

**Yes, you can use claude-cli or any CLI tool!**

Just configure:
```toml
[llm]
provider = "subprocess"
subprocess_command = ["claude-cli"]
model = "claude-3-5-haiku-20241022"
```

**Pros**:
- Reuse existing tools
- Easy to debug
- Flexible

**Cons**:
- Slower (process overhead)
- Less efficient
- Estimated token counts

**Recommendation**: Use for development/prototyping, but switch to direct API (anthropic/openai/ollama providers) for production for better performance.
