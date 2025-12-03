# Multi-Provider LLM Setup Guide

## Overview

The internal LLM client supports **multiple providers**, so you're **not locked into Anthropic**:

| Provider | Type | Cost | Setup Complexity |
|----------|------|------|------------------|
| **Anthropic** | Cloud | Paid | ⭐ Easy |
| **OpenAI** | Cloud | Paid | ⭐ Easy |
| **Ollama** | Local | **FREE** | ⭐⭐ Medium |
| **LM Studio** | Local | **FREE** | ⭐⭐ Medium |
| **vLLM** | Self-hosted | **FREE** | ⭐⭐⭐ Advanced |

**Key Point**: The MCP server's internal LLM is **completely independent** from Claude Desktop, so you can use **any provider you want**.

## Provider #1: Anthropic (Default)

**Best for**: Production, reliability, quality

###Configuration

```toml
# ~/.config/glintefy/config.toml
[llm]
enable_internal_llm = true
provider = "anthropic"  # This is the default

# Anthropic models
model = "claude-3-5-sonnet-20241022"  # Complex reasoning
fast_model = "claude-3-5-haiku-20241022"  # Quick classification

# API key (or use GLINTEFY_ANTHROPIC_API_KEY env var)
anthropic_api_key = "sk-ant-api-03-YOUR-KEY"

[llm.features]
classify_severity = true
generate_commit_messages = true
```

### Cost
- Haiku: $0.25/1M input, $1.25/1M output (very cheap for classification)
- Sonnet: $3/1M input, $15/1M output (reasonable for suggestions)

### Setup
```bash
# Get API key from: https://console.anthropic.com/settings/keys
export GLINTEFY_ANTHROPIC_API_KEY="sk-ant-api-03-YOUR-KEY"
```

## Provider #2: OpenAI

**Best for**: Existing OpenAI customers, GPT-4o quality

### Configuration

```toml
# ~/.config/glintefy/config.toml
[llm]
enable_internal_llm = true
provider = "openai"

# OpenAI models
model = "gpt-4o"  # High quality
fast_model = "gpt-4o-mini"  # Fast and cheap

# API key (or use GLINTEFY_OPENAI_API_KEY env var)
openai_api_key = "sk-proj-YOUR-KEY"

[llm.features]
classify_severity = true
generate_commit_messages = true
```

### Cost
- gpt-4o-mini: $0.15/1M input, $0.6/1M output (cheapest!)
- gpt-4o: $2.5/1M input, $10/1M output

### Setup
```bash
# Get API key from: https://platform.openai.com/api-keys
export GLINTEFY_OPENAI_API_KEY="sk-proj-YOUR-KEY"

# Or use standard OpenAI env var
export OPENAI_API_KEY="sk-proj-YOUR-KEY"
```

## Provider #3: Ollama (Local - FREE!)

**Best for**: Privacy, offline use, zero cost, development

### Why Ollama?
✅ **Completely free** - No API costs
✅ **Private** - Code never leaves your machine
✅ **Offline** - Works without internet
✅ **Fast** - No network latency
✅ **Easy setup** - One command to install

### Installation

```bash
# macOS/Linux
curl -fsSL https://ollama.com/install.sh | sh

# Or download from: https://ollama.com/download

# Verify installation
ollama --version
```

### Pull Models

```bash
# Fast, small model (3B params, ~2GB)
ollama pull llama3.2:3b

# Code-focused model (7B params, ~4.7GB)
ollama pull qwen2.5-coder:7b

# Larger, better quality (16B params, ~9.5GB)
ollama pull deepseek-coder-v2:16b

# List installed models
ollama list
```

### Configuration

```toml
# ~/.config/glintefy/config.toml
[llm]
enable_internal_llm = true
provider = "ollama"

# Ollama models (must be pulled first!)
model = "qwen2.5-coder:7b"  # Good balance
fast_model = "llama3.2:3b"  # Very fast

# Ollama API endpoint (default: http://localhost:11434)
ollama_base_url = "http://localhost:11434"

# No API key needed!

[llm.features]
classify_severity = true
suggest_fixes = true  # FREE, so enable everything!
generate_commit_messages = true
analyze_patterns = true
```

### Recommended Models

| Model | Size | RAM | Speed | Quality | Use Case |
|-------|------|-----|-------|---------|----------|
| `llama3.2:3b` | 2GB | 4GB | ⚡⚡⚡ | ⭐⭐ | Fast classification |
| `qwen2.5-coder:7b` | 4.7GB | 8GB | ⚡⚡ | ⭐⭐⭐ | Code analysis |
| `deepseek-coder-v2:16b` | 9.5GB | 16GB | ⚡ | ⭐⭐⭐⭐ | Best quality |
| `codellama:13b` | 7.4GB | 12GB | ⚡ | ⭐⭐⭐ | Alternative |

### Test Ollama

```bash
# Start Ollama server (if not auto-started)
ollama serve

# Test a model
ollama run llama3.2:3b "Classify severity: high complexity"

# Test from Python
python << 'EOF'
from glintefy.subservers.common.llm_client import InternalLLMClient

client = InternalLLMClient(provider="ollama", fast_model="llama3.2:3b")

severity = client.classify_issue_severity(
    issue_type="high_complexity",
    code_snippet="def foo():\n    for i in range(100):\n        for j in range(100): pass",
    context={"complexity": 15}
)

print(f"✅ Ollama works! Severity: {severity}")
print(f"   Cost: $0.00 (local)")
EOF
```

## Provider #4: LM Studio (Local GUI - FREE!)

**Best for**: Non-technical users, local models with GUI

### Why LM Studio?
✅ **Completely free**
✅ **Beautiful GUI** - Easy model management
✅ **OpenAI-compatible** - Works with existing code
✅ **Model discovery** - Browse and download models easily

### Installation

1. Download from: https://lmstudio.ai/
2. Install and launch LM Studio
3. Go to "Search" tab
4. Download a model (e.g., "Qwen2.5-Coder-7B-Instruct")
5. Go to "Local Server" tab
6. Click "Start Server" (runs on `http://localhost:1234`)

### Configuration

```toml
# ~/.config/glintefy/config.toml
[llm]
enable_internal_llm = true
provider = "openai-compatible"

# LM Studio uses OpenAI-compatible API
base_url = "http://localhost:1234/v1"

# Model name from LM Studio
model = "qwen2.5-coder-7b-instruct"
fast_model = "qwen2.5-coder-7b-instruct"

# No API key needed for local!
# (or set to anything if required)
api_key = "not-needed"

[llm.features]
classify_severity = true
suggest_fixes = true
generate_commit_messages = true
```

## Provider #5: vLLM (Self-Hosted - Advanced)

**Best for**: Teams, production self-hosting, GPU clusters

### Why vLLM?
✅ **High throughput** - Optimized for batch processing
✅ **Production-ready** - Battle-tested
✅ **Multi-GPU** - Scale horizontally
✅ **OpenAI-compatible** - Drop-in replacement

### Installation (Docker)

```bash
# Pull vLLM image
docker pull vllm/vllm-openai:latest

# Run with model
docker run --gpus all \
  -p 8000:8000 \
  vllm/vllm-openai:latest \
  --model Qwen/Qwen2.5-Coder-7B-Instruct

# Or use docker-compose
cat > docker-compose.yml << 'EOF'
version: '3'
services:
  vllm:
    image: vllm/vllm-openai:latest
    ports:
      - "8000:8000"
    command: --model Qwen/Qwen2.5-Coder-7B-Instruct
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
EOF

docker-compose up -d
```

### Configuration

```toml
# ~/.config/glintefy/config.toml
[llm]
enable_internal_llm = true
provider = "openai-compatible"

# vLLM OpenAI-compatible endpoint
base_url = "http://localhost:8000/v1"

# Model name from vLLM
model = "Qwen/Qwen2.5-Coder-7B-Instruct"
fast_model = "Qwen/Qwen2.5-Coder-7B-Instruct"

# No API key for local, or set team key if adding auth
api_key = "team-api-key"

[llm.features]
classify_severity = true
suggest_fixes = true
generate_commit_messages = true
```

## Comparison Matrix

| Feature | Anthropic | OpenAI | Ollama | LM Studio | vLLM |
|---------|-----------|--------|--------|-----------|------|
| **Cost** | Paid | Paid | Free | Free | Free |
| **Quality** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Speed** | Fast | Fast | Fast | Medium | Very Fast |
| **Privacy** | Cloud | Cloud | Local | Local | Local |
| **Offline** | ❌ No | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes |
| **Setup** | Easy | Easy | Easy | Easy | Advanced |
| **Maintenance** | None | None | Low | Low | Medium |
| **Best For** | Production | Existing users | Dev/testing | Non-technical | Teams/scale |

## Switching Providers

### Quick Switch

```bash
# Switch to Ollama (local, free)
cat > ~/.config/glintefy/config.toml << 'EOF'
[llm]
enable_internal_llm = true
provider = "ollama"
fast_model = "llama3.2:3b"
EOF

# Switch to OpenAI
export GLINTEFY_OPENAI_API_KEY="sk-proj-YOUR-KEY"
cat > ~/.config/glintefy/config.toml << 'EOF'
[llm]
enable_internal_llm = true
provider = "openai"
fast_model = "gpt-4o-mini"
EOF
```

### Per-Project Override

```bash
# Use Ollama for this project (free for experiments)
cat > .glintefy.toml << 'EOF'
[llm]
provider = "ollama"
model = "qwen2.5-coder:7b"
EOF

# Or use Anthropic for production project
cat > .glintefy.toml << 'EOF'
[llm]
provider = "anthropic"
model = "claude-3-5-sonnet-20241022"
EOF
```

## Cost Comparison (1000 Issue Classifications)

| Provider | Model | Input Tokens | Output Tokens | Total Cost |
|----------|-------|--------------|---------------|------------|
| **Anthropic** | Haiku | 1.5M | 10K | **$0.39** |
| **OpenAI** | GPT-4o-mini | 1.5M | 10K | **$0.23** |
| **Ollama** | llama3.2:3b | N/A | N/A | **$0.00** |
| **LM Studio** | Qwen2.5-Coder | N/A | N/A | **$0.00** |
| **vLLM** | Qwen2.5-Coder | N/A | N/A | **$0.00** |

**Winner for cost**: Local models (Ollama, LM Studio, vLLM) are **100% free**

## Recommendations

### Personal Development
👉 **Use Ollama** - Free, fast, private
```bash
ollama pull llama3.2:3b
# Set provider = "ollama" in config
```

### Small Team
👉 **Use LM Studio** - Easy GUI, shared models
```bash
# One person runs LM Studio server
# Everyone points to http://team-server:1234
```

### Production (Small)
👉 **Use OpenAI** - Cheapest cloud option
```bash
# gpt-4o-mini is only $0.15/1M input tokens
export GLINTEFY_OPENAI_API_KEY="..."
```

### Production (Large)
👉 **Use vLLM** - Self-hosted at scale
```bash
# High throughput, full control, no API costs
docker-compose up vllm
```

### Maximum Quality
👉 **Use Anthropic Claude** - Best reasoning
```bash
# Claude Sonnet 3.5 for complex analysis
export GLINTEFY_ANTHROPIC_API_KEY="..."
```

## Environment Variables

| Provider | Primary Env Var | Fallback Env Var |
|----------|----------------|------------------|
| Anthropic | `GLINTEFY_ANTHROPIC_API_KEY` | `ANTHROPIC_API_KEY` |
| OpenAI | `GLINTEFY_OPENAI_API_KEY` | `OPENAI_API_KEY` |
| Ollama | (none - uses base_url) | - |
| OpenAI-compatible | `GLINTEFY_API_KEY` | - |

## Troubleshooting

### Ollama: "connection refused"

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not, start it
ollama serve

# Or check if using different port
ollama_base_url = "http://localhost:11434"  # in config
```

### LM Studio: "model not found"

1. Open LM Studio
2. Go to "Local Server" tab
3. Check "Loaded Model" name
4. Update config with exact model name

### vLLM: "CUDA out of memory"

```bash
# Use smaller model
docker run --gpus all \
  -p 8000:8000 \
  vllm/vllm-openai:latest \
  --model Qwen/Qwen2.5-Coder-3B-Instruct  # Smaller!

# Or limit GPU memory
--gpu-memory-utilization 0.8
```

## Summary

**You are NOT locked into Anthropic!**

✅ **4+ providers supported** - Anthropic, OpenAI, Ollama, LM Studio, vLLM, etc.

✅ **Local options available** - Ollama and LM Studio are completely free

✅ **Easy switching** - Just change config file

✅ **No caller impact** - MCP server's LLM choice doesn't affect Claude Desktop

✅ **Cost control** - Use free local models for development, paid for production

**Recommended starting point**: Try Ollama first (free, easy, private), then upgrade to cloud if needed.
