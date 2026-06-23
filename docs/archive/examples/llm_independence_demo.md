# LLM Independence Demo

## Visual Example: Complete Separation

This demonstrates that the MCP server's internal LLM is completely independent from the caller.

```
┌──────────────────────────────────────────────────────────────────┐
│ Alice's Laptop (Claude Desktop)                                  │
│                                                                   │
│  ~/.config/claude-desktop/anthropic-key.txt:                    │
│    sk-ant-api-03-alice-personal-key-xxx                         │
│                                                                   │
│  Alice's conversation with Claude:                               │
│    Alice: "Review my code quality"                              │
│    Claude: "I'll use the glintefy-review MCP server..."             │
│    [Calls MCP server tool: review_quality]                      │
│                                                                   │
└──────────────────────┬───────────────────────────────────────────┘
                       │ MCP Protocol
                       │ {"tool": "review_quality", "args": {...}}
                       │ (NO API key, NO settings passed)
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ glintefy-review MCP Server (Running on Alice's machine)              │
│                                                                   │
│  ~/.config/glintefy/config.toml:                             │
│    [llm]                                                         │
│    anthropic_api_key = "sk-ant-api-03-server-key-yyy"          │
│                                                                   │
│  Server makes SEPARATE API call to Anthropic:                   │
│    POST https://api.anthropic.com/v1/messages                   │
│    Authorization: sk-ant-api-03-server-key-yyy  ← DIFFERENT!   │
│    {                                                             │
│      "model": "claude-3-5-haiku-20241022",                      │
│      "messages": [{                                              │
│        "role": "user",                                           │
│        "content": "Classify severity: complexity=18..."         │
│      }]                                                          │
│    }                                                             │
│                                                                   │
│  Anthropic API returns:                                          │
│    {"content": [{"text": "high"}], ...}                         │
│                                                                   │
│  Server processes and returns to Claude Desktop:                │
│    {                                                             │
│      "status": "SUCCESS",                                        │
│      "issues": [{"severity": "high", ...}]                      │
│    }                                                             │
│                                                                   │
└──────────────────────┬───────────────────────────────────────────┘
                       │ MCP Protocol
                       │ {structured JSON results only}
                       │ (NO LLM prompts, NO LLM responses)
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ Alice's Laptop (Claude Desktop)                                  │
│                                                                   │
│  Alice's conversation continues:                                 │
│    Claude: "I found 5 high-severity issues:                     │
│             1. High complexity in process() function            │
│             2. ..."                                              │
│                                                                   │
│  Alice's API key usage:                                          │
│    - Her questions to Claude Desktop                             │
│    - Claude Desktop's responses                                  │
│    - Tool results displayed (just JSON, no tokens)              │
│                                                                   │
│  Server's API key usage (separate billing!):                    │
│    - Internal severity classifications                           │
│    - Internal fix suggestions                                    │
│    - Alice NEVER sees these calls                               │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

## Real-World Scenario

### Scenario 1: Different Users, Same Server

```
User Bob:
  - API Key: sk-ant-api-03-bob-personal-key
  - Calls glintefy-review MCP server

User Carol:
  - API Key: sk-ant-api-03-carol-personal-key
  - Calls SAME glintefy-review MCP server

MCP Server:
  - API Key: sk-ant-api-03-company-server-key
  - Both Bob and Carol's requests use THIS key for internal LLM
  - Company pays for internal LLM usage
  - Bob and Carol only pay for their Claude Desktop usage
```

### Scenario 2: Cost Tracking

```python
# Alice's monthly bill from Anthropic:
# - Conversations with Claude Desktop: $50
# - MCP server internal LLM: $0 (uses separate key)

# Company's monthly bill from Anthropic:
# - Server API key (sk-ant-api-03-company-server-key): $120
#   - Alice's code reviews: $40
#   - Bob's code reviews: $50
#   - Carol's code reviews: $30
```

## Configuration Example: Team Setup

### Company Server

```bash
# /opt/glintefy-review-server/.config/glintefy/config.toml
[llm]
enable_internal_llm = true
anthropic_api_key = "sk-ant-api-03-company-production-key"

# Use cheaper model for classification
fast_model = "claude-3-5-haiku-20241022"

# Enable basic features only
[llm.features]
classify_severity = true
generate_commit_messages = true
suggest_fixes = false  # Too expensive for all requests
```

### Developer Alice

```json
// Alice's ~/.config/claude-desktop/config.json
{
  "mcpServers": {
    "glintefy-review": {
      "command": "ssh",
      "args": [
        "company-server.local",
        "python", "-m", "glintefy", "serve"
      ]
    }
  }
}

// Alice's personal Anthropic key (for Claude Desktop): sk-ant-api-03-alice-personal-key
// Company server key (for internal LLM): sk-ant-api-03-company-production-key
// These are COMPLETELY SEPARATE
```

## Code Example: Independence

```python
# This is what happens inside the MCP server

from glintefy.subservers.common.llm_client import InternalLLMClient

# Server's LLM client (uses server's API key)
internal_llm = InternalLLMClient()
# Reads: GLINTEFY_ANTHROPIC_API_KEY=sk-ant-api-03-server-key

# When Alice calls review_quality:
def handle_review_quality(arguments):
    # 1. Run static analysis (no API calls)
    issues = run_radon_complexity()  # Local analysis

    # 2. Enhance with internal LLM (separate API call)
    if internal_llm.is_enabled("classify_severity"):
        for issue in issues:
            # THIS uses server's API key, NOT Alice's!
            severity = internal_llm.classify_issue_severity(
                issue_type=issue['type'],
                code_snippet=issue['code'],
                context=issue['metrics']
            )
            issue['llm_severity'] = severity

    # 3. Return structured results to Alice (no LLM details)
    return {
        "status": "SUCCESS",
        "issues": issues,  # Just the classifications, not LLM responses
        "metrics": {...}
    }

# Alice's Claude Desktop receives:
# {
#   "status": "SUCCESS",
#   "issues": [
#     {"severity": "high", "type": "complexity", ...},
#     ...
#   ]
# }
#
# Alice does NOT see:
# - The internal LLM prompt
# - The internal LLM response
# - The server's API key
# - Token usage details
```

## Billing Example

### Alice's Anthropic Bill (Personal Key)

```
Statement Period: January 2025
API Key: sk-ant-api-03-alice-personal-key

Usage:
- Claude Desktop conversations: 2.5M input tokens, 800K output tokens
- Cost: $12.50 (input) + $12.00 (output) = $24.50

MCP Tool Calls:
- glintefy-review tool calls: 0 tokens (just JSON results, no LLM usage)
- Cost: $0.00

Total: $24.50
```

### Company's Anthropic Bill (Server Key)

```
Statement Period: January 2025
API Key: sk-ant-api-03-company-server-key

Usage by glintefy-review MCP server:
- Internal severity classifications: 500K input, 5K output
  - Model: claude-3-5-haiku-20241022
  - Cost: $0.13 (input) + $0.01 (output) = $0.14

- Internal commit messages: 100K input, 10K output
  - Model: claude-3-5-haiku-20241022
  - Cost: $0.03 (input) + $0.01 (output) = $0.04

Total: $0.18 (very cheap!)

Users: Alice, Bob, Carol (3 developers)
Cost per user: $0.06/month
```

## FAQ

### Q: Does the MCP server see my Claude Desktop conversations?

**A: No.** The MCP protocol only passes:
- Tool calls: `{"tool": "review_quality", "args": {...}}`
- Tool results: `{"status": "SUCCESS", "issues": [...]}`

The server has **zero access** to your conversation history.

### Q: Does my API key get used by the MCP server?

**A: No.** The MCP server uses its own separate API key. Your personal key is only used for your Claude Desktop conversations.

### Q: Can I use the same API key for both?

**A: Technically yes, but DON'T.**

Reasons:
- Different billing/tracking
- Different rate limits
- Security isolation
- If server key leaks, your personal account isn't compromised

### Q: Who pays for the internal LLM calls?

**A: Whoever owns the server's API key.**

- Personal use: You pay (use your own server key)
- Company use: Company pays (use company server key)
- Shared server: Whoever runs the server pays

### Q: Can I disable internal LLM to save costs?

**A: Yes!** Just set in config:

```toml
[llm]
enable_internal_llm = false
```

The server will fall back to rule-based analysis (free, but less sophisticated).

### Q: How do I know if the server is using internal LLM?

**A: Check the tool results:**

```json
{
  "status": "SUCCESS",
  "metrics": {
    "issues_count": 10,
    "llm_enhanced": true,  ← LLM was used
    "llm_usage": {         ← Token usage details
      "calls": 10,
      "total_tokens": 150,
      "estimated_cost_usd": 0.0002
    }
  }
}
```

## Summary: Complete Independence

| Aspect | Your Setting | Server's Setting | Shared? |
|--------|--------------|------------------|---------|
| API Key | Your personal key | Server's key | ❌ No |
| Token Budget | Your account | Server's account | ❌ No |
| Billing | Your bill | Server owner's bill | ❌ No |
| Conversation | Your chat history | No access | ❌ No |
| Context Window | Your context | Separate API calls | ❌ No |
| Rate Limits | Your limits | Server's limits | ❌ No |
| Model Choice | You pick in Desktop | Server config | ❌ No |
| Feature Flags | N/A | Server config | ❌ No |

**Everything is separate. You need to configure the server independently.**
