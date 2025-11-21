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

**MCP servers for comprehensive code review and automated fixing.**

## Overview

btx_fix_mcp provides two MCP (Model Context Protocol) servers:

- **btx-review**: Analyzes code for quality, security, and documentation issues
- **btx-fix**: Automated code fixing with evidence-based verification (planned)

### Key Features

- **18+ Quality Analyses**: Complexity, maintainability, duplication, type coverage, dead code, and more
- **Security Scanning**: Bandit integration for vulnerability detection
- **Isolated Tool Environment**: Analysis tools run in a dedicated venv (`~/.cache/btx-fix-mcp/tools-venv/`)
- **Flexible Configuration**: TOML-based config with parameter overrides
- **Comprehensive Testing**: 219 tests with full coverage

## Installation

```bash
# Install via uv (recommended)
pip install --upgrade uv
uv venv && source .venv/bin/activate
uv pip install btx_fix_mcp

# Or install via pip
pip install btx_fix_mcp

# For development
git clone https://github.com/bitranox/btx_fix_mcp
cd btx_fix_mcp
make dev
```

## Quick Start

```python
from pathlib import Path
from btx_fix_mcp.subservers.review.scope import ScopeSubServer
from btx_fix_mcp.subservers.review.quality import QualitySubServer
from btx_fix_mcp.subservers.review.security import SecuritySubServer

# Run scope analysis (discovers files to review)
scope = ScopeSubServer(
    output_dir=Path("LLM-CONTEXT/review-anal/scope"),
    repo_path=Path.cwd(),
    mode="full",
)
scope.run()

# Run quality analysis
quality = QualitySubServer(
    input_dir=Path("LLM-CONTEXT/review-anal/scope"),
    output_dir=Path("LLM-CONTEXT/review-anal/quality"),
    repo_path=Path.cwd(),
)
result = quality.run()

print(f"Issues found: {result.metrics['issues_count']}")
print(f"High complexity: {result.metrics['high_complexity_count']}")
```

## Quality Analyses

The quality sub-server provides:

| Analysis | Tool | Description |
|----------|------|-------------|
| Cyclomatic Complexity | radon | Function complexity scoring |
| Cognitive Complexity | custom | Mental effort to understand code |
| Maintainability Index | radon | Overall maintainability score |
| Code Duplication | pylint | Duplicate code detection |
| Static Analysis | ruff | Linting and style issues |
| Type Coverage | mypy | Type annotation coverage |
| Dead Code | vulture | Unused code detection |
| Import Cycles | custom | Circular import detection |
| Docstring Coverage | interrogate | Documentation completeness |
| Architecture | custom | God objects, coupling analysis |
| Code Churn | git | Frequently modified files |
| Test Analysis | custom | Test coverage and assertions |

## Configuration

Configuration is loaded from (lowest to highest priority):
1. `defaultconfig.toml` (bundled)
2. `~/.config/btx-fix-mcp/config.toml`
3. Environment variables
4. Constructor parameters

Example:
```python
quality = QualitySubServer(
    complexity_threshold=15,      # Override default
    enable_dead_code_detection=False,
)
```

See [README_MCP.md](README_MCP.md) for full configuration reference.

## Development

```bash
# Run tests
make test

# Run without coverage (faster)
python -m pytest tests/ --no-cov

# Linting
ruff check src/ tests/

# Type checking
pyright src/
```

### Python 3.13+ Support

The project requires Python 3.13 or newer, tested on 3.13 and 3.14.

## Documentation

- [MCP Server Guide](README_MCP.md) - Detailed usage and configuration
- [Install Guide](INSTALL.md) - Installation options
- [Development Handbook](DEVELOPMENT.md) - Development setup
- [Contributor Guide](CONTRIBUTING.md) - How to contribute
- [Changelog](CHANGELOG.md) - Version history
- [Architecture](docs/ARCHITECTURE_SUMMARY.md) - System design

## License

[MIT License](LICENSE)
