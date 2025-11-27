# Internal LLM Configuration Guide

## Overview: Complete Independence

**Key Principle**: The MCP server has its **own separate configuration** completely independent from Claude Desktop or any MCP client.

```
User's Claude Desktop          MCP Server (btx-review)
├─ User's API key              ├─ Server's API key (DIFFERENT!)
├─ User's settings             ├─ Server's settings
└─ User's conversation         └─ Server's internal LLM calls

      ↕ MCP Protocol (Tool calls only, no settings shared)
```

## API Key Sources (Priority Order)

The internal LLM client looks for API keys in this order (first found wins):

1. **Constructor parameter** (programmatic override)
   ```python
   client = InternalLLMClient(api_key="sk-ant-...")
   ```

2. **Config file** (`~/.config/btx-fix-mcp/config.toml`)
   ```toml
   [llm]
   anthropic_api_key = "sk-ant-api-03-server-key-xxx"
   ```

3. **Environment variable** (preferred for security)
   ```bash
   export BTX_FIX_MCP_ANTHROPIC_API_KEY="sk-ant-api-03-server-key-xxx"
   ```

4. **Fallback environment variable**
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-api-03-server-key-xxx"
   ```

If none found → Error on first LLM call (falls back to rule-based analysis)

## Setup Options

### Option 1: Environment Variable (Recommended)

**Most secure** - No API key in files

```bash
# Add to ~/.bashrc or ~/.zshrc
export BTX_FIX_MCP_ANTHROPIC_API_KEY="sk-ant-api-03-YourServerKey"

# Or for session only
export BTX_FIX_MCP_ANTHROPIC_API_KEY="sk-ant-api-03-YourServerKey"
python -m btx_fix_mcp review all --mode full
```

**Pros**:
- ✅ No API key in files (can't accidentally commit)
- ✅ Easy to rotate keys
- ✅ Can use different keys per shell session

**Cons**:
- ❌ Must set in every terminal session (unless in shell config)
- ❌ Not available to GUI-launched processes

### Option 2: Config File (Persistent)

**Convenient** - Set once and forget

```bash
# Create config directory
mkdir -p ~/.config/btx-fix-mcp

# Create config file
cat > ~/.config/btx-fix-mcp/config.toml << 'EOF'
[llm]
# Enable internal LLM features
enable_internal_llm = true

# Server's API key (DIFFERENT from user's Claude Desktop key!)
anthropic_api_key = "sk-ant-api-03-YourServerKey"

# Models to use
model = "claude-3-5-sonnet-20241022"
fast_model = "claude-3-5-haiku-20241022"

[llm.features]
classify_severity = true
generate_commit_messages = true
EOF

# Protect config file (contains API key!)
chmod 600 ~/.config/btx-fix-mcp/config.toml
```

**Pros**:
- ✅ Persistent across sessions
- ✅ Works with GUI-launched MCP servers
- ✅ All settings in one place

**Cons**:
- ❌ API key in plaintext file
- ❌ Risk of committing to git if config in project dir
- ❌ Need to remember to secure permissions

### Option 3: Project-Specific Config (Not Recommended for API Keys)

**Only for non-secret settings** - Do NOT put API keys here!

```bash
# In your project directory
cat > .btx-fix-mcp.toml << 'EOF'
[llm]
# Enable features but don't put API key here!
enable_internal_llm = true

[llm.features]
classify_severity = true

# API key will come from env or ~/.config/btx-fix-mcp/config.toml
EOF

# Add to .gitignore to be safe
echo ".btx-fix-mcp.toml" >> .gitignore
```

**Pros**:
- ✅ Project-specific LLM feature settings
- ✅ Can commit safe settings to git

**Cons**:
- ❌ **NEVER put API keys here** (risk of git commit)
- ❌ Overrides user config (may surprise users)

## Complete Setup Examples

### Example 1: Development Machine (Environment Variable)

```bash
# 1. Get API key from Anthropic Console (separate from your Claude Desktop key)
#    https://console.anthropic.com/settings/keys

# 2. Add to shell config
cat >> ~/.bashrc << 'EOF'
# MCP Server API key (separate from Claude Desktop)
export BTX_FIX_MCP_ANTHROPIC_API_KEY="sk-ant-api-03-dev-machine-key"
EOF

# 3. Reload shell or source config
source ~/.bashrc

# 4. Enable features in config (optional)
mkdir -p ~/.config/btx-fix-mcp
cat > ~/.config/btx-fix-mcp/config.toml << 'EOF'
[llm]
enable_internal_llm = true

[llm.features]
classify_severity = true
generate_commit_messages = true
EOF

# 5. Test it works
python -m btx_fix_mcp review quality --complexity 10
```

### Example 2: Production Server (Config File)

```bash
# 1. Create secure config directory
mkdir -p ~/.config/btx-fix-mcp
chmod 700 ~/.config/btx-fix-mcp

# 2. Create config with restricted permissions
cat > ~/.config/btx-fix-mcp/config.toml << 'EOF'
[llm]
enable_internal_llm = true
anthropic_api_key = "sk-ant-api-03-production-server-key"

# Use faster model for classification (cheaper)
fast_model = "claude-3-5-haiku-20241022"

# Conservative token limits
max_tokens_classification = 10
max_tokens_suggestion = 300

[llm.features]
classify_severity = true
suggest_fixes = false  # More expensive, disable for now
generate_commit_messages = true
EOF

# 3. Secure the file
chmod 600 ~/.config/btx-fix-mcp/config.toml

# 4. Verify permissions
ls -la ~/.config/btx-fix-mcp/
# Should show: -rw------- (only owner can read/write)
```

### Example 3: CI/CD Pipeline (Environment Variable)

```yaml
# .github/workflows/review.yml
name: Code Review

on: [push, pull_request]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install btx-fix-mcp
        run: pip install btx-fix-mcp

      - name: Run code review
        env:
          # GitHub Secret: BTX_FIX_MCP_API_KEY
          BTX_FIX_MCP_ANTHROPIC_API_KEY: ${{ secrets.BTX_FIX_MCP_API_KEY }}
        run: |
          python -m btx_fix_mcp review all --mode git
```

## MCP Server Integration

When running as MCP server (connected to Claude Desktop):

### Claude Desktop Configuration

```json
// ~/.config/claude-desktop/config.json (macOS/Linux)
// %APPDATA%/Claude/config.json (Windows)
{
  "mcpServers": {
    "btx-review": {
      "command": "python",
      "args": ["-m", "btx_fix_mcp", "serve"],
      "env": {
        // Option 1: Pass API key via environment
        "BTX_FIX_MCP_ANTHROPIC_API_KEY": "sk-ant-api-03-server-key"
      }
    }
  }
}
```

**Or** rely on system environment or config file:

```json
{
  "mcpServers": {
    "btx-review": {
      "command": "python",
      "args": ["-m", "btx_fix_mcp", "serve"]
      // No env - uses BTX_FIX_MCP_ANTHROPIC_API_KEY from environment
      // or anthropic_api_key from ~/.config/btx-fix-mcp/config.toml
    }
  }
}
```

## Verification

### Check Configuration Loading

```bash
# Test API key is found (doesn't make any calls)
python << 'EOF'
from btx_fix_mcp.subservers.common.llm_client import InternalLLMClient

client = InternalLLMClient()
if client.api_key:
    print(f"✅ API key found: {client.api_key[:20]}...")
    print(f"   Model: {client.model}")
    print(f"   Fast model: {client.fast_model}")
else:
    print("❌ No API key configured")
EOF
```

### Test LLM Classification

```bash
# Make actual API call (uses tokens!)
python << 'EOF'
from btx_fix_mcp.subservers.common.llm_client import InternalLLMClient
from btx_fix_mcp.config import get_config

# Check if enabled
config = get_config()
if not config.get("llm", {}).get("enable_internal_llm"):
    print("⚠️  Internal LLM disabled in config")
    exit(1)

client = InternalLLMClient()

# Test classification
severity = client.classify_issue_severity(
    issue_type="high_complexity",
    code_snippet="def process(items):\n    for i in items:\n        for j in items:\n            pass",
    context={"complexity": 18, "lines": 50}
)

print(f"✅ Classification works: {severity}")
print(f"   Token usage: {client.get_usage_summary()}")
EOF
```

## Security Best Practices

### 1. Never Commit API Keys

```bash
# Add to .gitignore
cat >> .gitignore << 'EOF'
# MCP Server config (may contain API keys)
.btx-fix-mcp.toml
.btx-fix-mcp.yaml
config.toml
EOF
```

### 2. Use Separate API Keys

**DO NOT reuse your personal Claude Desktop API key for the MCP server!**

Reasons:
- Different usage patterns (server makes many small calls)
- Different rate limits (server may hit limits)
- Easier billing tracking (see server costs separately)
- Security isolation (revoke server key without affecting personal use)

### 3. Rotate Keys Regularly

```bash
# 1. Generate new key in Anthropic Console
# 2. Update environment variable
export BTX_FIX_MCP_ANTHROPIC_API_KEY="sk-ant-api-03-new-key"

# 3. Or update config file
sed -i 's/anthropic_api_key = "sk-ant-api-03-old-key"/anthropic_api_key = "sk-ant-api-03-new-key"/' \
  ~/.config/btx-fix-mcp/config.toml

# 4. Restart MCP server (if running)
```

### 4. Restrict Permissions

```bash
# Config directory: only owner can access
chmod 700 ~/.config/btx-fix-mcp

# Config file: only owner can read/write
chmod 600 ~/.config/btx-fix-mcp/config.toml

# Verify
ls -la ~/.config/btx-fix-mcp/
# Should show: drwx------ (dir) and -rw------- (file)
```

## Troubleshooting

### Error: "Anthropic API key not configured"

**Cause**: No API key found in any source

**Fix**:
```bash
# Check environment variable
echo $BTX_FIX_MCP_ANTHROPIC_API_KEY

# Check config file
cat ~/.config/btx-fix-mcp/config.toml | grep anthropic_api_key

# Set via environment
export BTX_FIX_MCP_ANTHROPIC_API_KEY="sk-ant-api-03-your-key"

# Or add to config
mkdir -p ~/.config/btx-fix-mcp
echo 'anthropic_api_key = "sk-ant-api-03-your-key"' >> ~/.config/btx-fix-mcp/config.toml
```

### Error: "anthropic package required"

**Cause**: Anthropic Python SDK not installed

**Fix**:
```bash
pip install anthropic

# Or install with btx-fix-mcp extras
pip install btx-fix-mcp[llm]  # If we add this extra
```

### LLM Features Not Working

**Cause**: Features disabled in config

**Fix**:
```bash
# Check feature flags
python << 'EOF'
from btx_fix_mcp.config import get_config
config = get_config()
print("LLM enabled:", config.get("llm", {}).get("enable_internal_llm"))
print("Features:", config.get("llm", {}).get("features", {}))
EOF

# Enable in config
cat >> ~/.config/btx-fix-mcp/config.toml << 'EOF'
[llm]
enable_internal_llm = true

[llm.features]
classify_severity = true
EOF
```

### API Key Works Locally but Not in MCP Server

**Cause**: Environment variables not passed to MCP server process

**Fix**: Add to Claude Desktop config:

```json
{
  "mcpServers": {
    "btx-review": {
      "command": "python",
      "args": ["-m", "btx_fix_mcp", "serve"],
      "env": {
        "BTX_FIX_MCP_ANTHROPIC_API_KEY": "sk-ant-api-03-your-key"
      }
    }
  }
}
```

## Cost Monitoring

### Track Usage

```python
from btx_fix_mcp.subservers.common.llm_client import InternalLLMClient

client = InternalLLMClient()

# After analysis
summary = client.get_usage_summary()
print(f"API calls: {summary['calls']}")
print(f"Total tokens: {summary['total_tokens']}")
print(f"Estimated cost: ${summary['estimated_cost_usd']:.4f}")
```

### Set Budget Limits

```toml
# ~/.config/btx-fix-mcp/config.toml
[llm]
# Limit max tokens per operation type
max_tokens_classification = 10   # Very cheap (~$0.0001 per call)
max_tokens_suggestion = 200      # Reduced from 500 to save costs
max_tokens_verification = 100    # Reduced from 300 to save costs

# Disable expensive features
[llm.features]
classify_severity = true         # Cheap (10 tokens with Haiku)
suggest_fixes = false            # Expensive (500 tokens with Sonnet) - DISABLED
verify_fixes = false             # Expensive (300 tokens with Sonnet) - DISABLED
generate_commit_messages = true  # Cheap (50 tokens with Haiku)
```

## Summary: No Settings Shared

| Setting | Claude Desktop (Caller) | MCP Server (btx-review) |
|---------|------------------------|-------------------------|
| **API Key** | User's personal key | **Separate server key** ❗ |
| **Model** | User's choice | Server's config (sonnet/haiku) |
| **Token Budget** | User's account | Server's account |
| **Settings** | Claude Desktop config | `~/.config/btx-fix-mcp/` |
| **Conversation** | User's chat history | No access to chat |
| **Context** | User's context window | Separate API calls |

**Key Takeaway**: Set everything up independently. The MCP server is a separate process with separate credentials and separate configuration.
