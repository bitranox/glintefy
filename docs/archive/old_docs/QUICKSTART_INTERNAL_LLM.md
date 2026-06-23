# Quick Start: Internal LLM Setup (5 Minutes)

## The Short Answer

**Q: Do I need to set everything up again?**

**A: Yes, but it's simple:**

1. Get a **separate** API key (different from your Claude Desktop key)
2. Put it in environment variable: `GLINTEFY_ANTHROPIC_API_KEY`
3. Enable features in config
4. Done!

**The caller's settings (Claude Desktop) don't apply to the server at all.**

## 5-Minute Setup

### Step 1: Get Server API Key (2 minutes)

1. Go to https://console.anthropic.com/settings/keys
2. Create a new API key
3. Name it "glintefy-review-server" (to distinguish from your personal key)
4. Copy the key: `sk-ant-api-03-...`

**Important:** Use a **different** key than your Claude Desktop key!

### Step 2: Set Environment Variable (1 minute)

```bash
# Add to ~/.bashrc or ~/.zshrc
echo 'export GLINTEFY_ANTHROPIC_API_KEY="sk-ant-api-03-YOUR-SERVER-KEY"' >> ~/.bashrc

# Reload
source ~/.bashrc

# Verify
echo $GLINTEFY_ANTHROPIC_API_KEY
# Should print: sk-ant-api-03-YOUR-SERVER-KEY
```

### Step 3: Enable Features (1 minute)

```bash
# Create config directory
mkdir -p ~/.config/glintefy

# Create config
cat > ~/.config/glintefy/config.toml << 'EOF'
[llm]
enable_internal_llm = true

[llm.features]
classify_severity = true
generate_commit_messages = true
EOF
```

### Step 4: Test (1 minute)

```bash
# Test internal LLM works
python << 'EOF'
from glintefy.subservers.common.llm_client import InternalLLMClient

client = InternalLLMClient()

# Quick test (uses ~10 tokens)
severity = client.classify_issue_severity(
    issue_type="high_complexity",
    code_snippet="def foo():\n    for i in range(100):\n        for j in range(100): pass",
    context={"complexity": 15}
)

print(f"✅ It works! Severity: {severity}")
print(f"   Tokens used: {client.get_usage_summary()['total_tokens']}")
EOF
```

Expected output:
```
✅ It works! Severity: high
   Tokens used: 150
```

## What You've Set Up

```
┌─────────────────────────────────────────┐
│ Your Claude Desktop                     │
│ API Key: sk-ant-api-03-YOUR-PERSONAL-KEY│
│ (unchanged - still your personal key)   │
└─────────────────────────────────────────┘
              ↕ MCP Protocol
┌─────────────────────────────────────────┐
│ glintefy-review MCP Server                   │
│ API Key: GLINTEFY_ANTHROPIC_API_KEY  │
│ API Key: sk-ant-api-03-YOUR-SERVER-KEY  │
│ (new separate key you just created)    │
└─────────────────────────────────────────┘
```

## Settings Summary

| Setting | Source | Value |
|---------|--------|-------|
| **Server API Key** | Environment: `GLINTEFY_ANTHROPIC_API_KEY` | `sk-ant-api-03-...` |
| **Enable LLM** | Config: `~/.config/glintefy/config.toml` | `enable_internal_llm = true` |
| **Features** | Config: `[llm.features]` | `classify_severity = true` |

**Your Claude Desktop settings:** Unchanged (uses different key)

## Cost Estimate

With these conservative settings:

- **classify_severity**: ~10 tokens per issue with Haiku (~$0.0001 per call)
- **generate_commit_messages**: ~50 tokens with Haiku (~$0.0005 per call)

**Example**: Reviewing 100 files with 200 issues = $0.02 + $0.05 = **$0.07 total**

Very cheap! The static analysis (ruff, mypy, radon) is still free.

## Disable Anytime

```bash
# Disable internal LLM (fall back to rule-based)
cat > ~/.config/glintefy/config.toml << 'EOF'
[llm]
enable_internal_llm = false
EOF
```

Or just unset the environment variable:
```bash
unset GLINTEFY_ANTHROPIC_API_KEY
```

The server will still work - just without LLM enhancements (uses rule-based fallbacks).

## Advanced: Per-Project Settings

Want different settings for different projects?

```bash
# In your project directory
cat > .glintefy.toml << 'EOF'
[llm.features]
classify_severity = true
suggest_fixes = true  # Enable expensive feature for this project
EOF

# API key still comes from environment
# (don't put API keys in project files!)
```

## Troubleshooting

### "API key not configured"

```bash
# Check environment variable
echo $GLINTEFY_ANTHROPIC_API_KEY

# If empty, set it:
export GLINTEFY_ANTHROPIC_API_KEY="sk-ant-api-03-YOUR-KEY"
```

### Features not enabled

```bash
# Check config
cat ~/.config/glintefy/config.toml

# Should show:
# [llm]
# enable_internal_llm = true
#
# [llm.features]
# classify_severity = true
```

### Works locally but not in MCP server

Add to Claude Desktop config:

```json
{
  "mcpServers": {
    "glintefy-review": {
      "command": "python",
      "args": ["-m", "glintefy", "serve"],
      "env": {
        "GLINTEFY_ANTHROPIC_API_KEY": "sk-ant-api-03-YOUR-KEY"
      }
    }
  }
}
```

## Key Takeaways

✅ **Separate API key** - Use different key for server than Claude Desktop

✅ **Environment variable** - `GLINTEFY_ANTHROPIC_API_KEY`

✅ **Enable in config** - `enable_internal_llm = true`

✅ **Very cheap** - ~$0.0001 per classification with Haiku

✅ **Optional** - Disable anytime, falls back to rule-based

✅ **Independent** - Your Claude Desktop settings don't apply

## Next Steps

- See [llm_configuration_guide.md](llm_configuration_guide.md) for detailed setup options
- See [internal_llm_usage.md](internal_llm_usage.md) for implementation details
- See [llm_independence_demo.md](examples/llm_independence_demo.md) for architecture explanation
