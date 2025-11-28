# btx_fix_mcp

<!-- Badges -->
[![CI](https://github.com/bitranox/btx_fix_mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/bitranox/btx_fix_mcp/actions/workflows/ci.yml)
[![CodeQL](https://github.com/bitranox/btx_fix_mcp/actions/workflows/codeql.yml/badge.svg)](https://github.com/bitranox/btx_fix_mcp/actions/workflows/codeql.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Open in Codespaces](https://img.shields.io/badge/Codespaces-Open-blue?logo=github&logoColor=white&style=flat-square)](https://codespaces.new/bitranox/btx_fix_mcp?quickstart=1)
[![PyPI](https://img.shields.io/pypi/v/btx_fix_mcp.svg)](https://pypi.org/project/btx_fix_mcp/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/btx_fix_mcp.svg)](https://pypi.org/project/btx_fix_mcp/)
[![Code Style: Ruff](https://img.shields.io/badge/Code%20Style-Ruff-46A3FF?logo=ruff&labelColor=000)](https://docs.astral.sh/ruff/)
[![codecov](https://codecov.io/gh/bitranox/btx_fix_mcp/graph/badge.svg?token=UFBaUDIgRk)](https://codecov.io/gh/bitranox/btx_fix_mcp)
[![Maintainability](https://qlty.sh/badges/041ba2c1-37d6-40bb-85a0-ec5a8a0aca0c/maintainability.svg)](https://qlty.sh/gh/bitranox/projects/btx_fix_mcp)
[![Known Vulnerabilities](https://snyk.io/test/github/bitranox/btx_fix_mcp/badge.svg)](https://snyk.io/test/github/bitranox/btx_fix_mcp)
[![security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)

**Code review and automated fixing tools - available as CLI and MCP server.**

## What is btx_fix_mcp?

btx_fix_mcp provides comprehensive code analysis:

- **18+ Quality Analyses**: Complexity, maintainability, duplication, type coverage, dead code
- **Security Scanning**: Bandit integration for vulnerability detection
- **Cache Optimization**: Evidence-based `@lru_cache` recommendations
- **Documentation Coverage**: Docstring completeness analysis

**Two ways to use it:**

| Mode | Best For |
|------|----------|
| **CLI** | Direct command-line usage, CI/CD pipelines, scripts |
| **MCP Server** | Integration with Claude Desktop, AI-assisted workflows |

---

## Quick Start

### Installation

```bash
# Recommended: uv
pip install uv
uv pip install btx_fix_mcp

# Alternative: pip
pip install btx_fix_mcp

# Development
git clone https://github.com/bitranox/btx_fix_mcp
cd btx_fix_mcp && make dev
```

### CLI Usage (Simple)

```bash
# Review uncommitted git changes (default)
btx_fix_mcp review all

# Review all files
btx_fix_mcp review all --mode full

# Run specific analysis
btx_fix_mcp review quality
btx_fix_mcp review security

# Cache optimization with profiling (recommended)
btx_fix_mcp review profile -- python -m your_app    # Profile your app
btx_fix_mcp review profile -- pytest tests/         # Or profile tests
btx_fix_mcp review cache                            # Then analyze

# Clean up analysis data
btx_fix_mcp review clean                            # Delete all
btx_fix_mcp review clean -s profile                 # Delete profile only
btx_fix_mcp review clean --dry-run                  # Preview deletion
```

### MCP Server Usage (Simple)

Add to Claude Desktop config (`~/.config/claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "btx-review": {
      "command": "python",
      "args": ["-m", "btx_fix_mcp.servers.review"]
    }
  }
}
```

Then in Claude Desktop:
> "Review the code quality of this project"

---

## Documentation

### Getting Started

| Document | Description |
|----------|-------------|
| [CLI Quickstart](docs/cli/QUICKSTART.md) | Start using CLI in 5 minutes |
| [MCP Quickstart](docs/mcp/QUICKSTART.md) | Set up MCP server for Claude Desktop |
| [Installation Guide](INSTALL.md) | All installation methods |

### User Guides

| Document | Description |
|----------|-------------|
| [CLI Reference](docs/cli/REFERENCE.md) | All CLI commands and options |
| [MCP Tools Reference](docs/mcp/TOOLS.md) | MCP tools and resources |
| [Configuration](docs/reference/CONFIGURATION.md) | All configuration options |
| [Cache Profiling](docs/CACHE_SUBSERVER.md) | LRU cache optimization guide |

### Development

| Document | Description |
|----------|-------------|
| [Development Guide](DEVELOPMENT.md) | Setup, testing, make targets |
| [Architecture](docs/architecture/OVERVIEW.md) | System design overview |
| [Contributing](CONTRIBUTING.md) | How to contribute |

---

## Features Overview

### Analyses Available

| Analysis | Description | CLI Command |
|----------|-------------|-------------|
| **Scope** | File discovery, git changes | `review scope` |
| **Quality** | Complexity, maintainability, duplication | `review quality` |
| **Security** | Vulnerability scanning (Bandit) | `review security` |
| **Dependencies** | Outdated packages, vulnerabilities | `review deps` |
| **Documentation** | Docstring coverage | `review docs` |
| **Performance** | Hotspot detection, profiling | `review perf` |
| **Cache** | LRU cache optimization | `review cache` |

### Quality Metrics

| Metric | Tool | Threshold |
|--------|------|-----------|
| Cyclomatic Complexity | radon | ≤10 |
| Function Length | custom | ≤50 lines |
| Nesting Depth | custom | ≤3 levels |
| Maintainability Index | radon | ≥20 |
| Type Coverage | mypy | ≥80% |
| Docstring Coverage | interrogate | ≥80% |

---

## Requirements

- Python 3.13+
- Git (optional)

### Git Integration

Git is **optional** but enables additional features:

| Feature | Without Git | With Git |
|---------|-------------|----------|
| **Scope Mode** | `--mode full` scans all files | `--mode git` scans only uncommitted changes (default) |
| **Code Churn** | Skipped | Analyzes frequently modified files |
| **Branch Info** | Shows "N/A" | Displays current branch |

When git is not available:
- `--mode git` automatically falls back to `--mode full` with a warning
- Code churn analysis is skipped silently
- Cache analysis works without git (uses in-memory file backup)
- All other analyses work normally

---

## License

[MIT License](LICENSE)

---

## Links

- [PyPI](https://pypi.org/project/btx_fix_mcp/)
- [GitHub](https://github.com/bitranox/btx_fix_mcp)
- [Issues](https://github.com/bitranox/btx_fix_mcp/issues)
- [Changelog](CHANGELOG.md)
