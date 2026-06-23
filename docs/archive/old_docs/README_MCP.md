# glintefy & glintefy-review: MCP Servers for Code Quality

> **Status**: Phase 1 Complete - Core Infrastructure & Review Sub-servers
> **Version**: 0.1.0
> **Last Updated**: 2025-11-21

## What is This?

Two MCP (Model Context Protocol) servers that provide comprehensive code review and automated fixing capabilities:

1. **glintefy-review** - Analyzes code for quality, security, performance, and documentation issues
2. **glintefy** - Actually fixes issues with evidence-based verification (planned)

## Current Implementation Status

### Completed

| Component | Status | Description |
|-----------|--------|-------------|
| **Core Infrastructure** | :white_check_mark: Complete | Base classes, protocols, logging |
| **Configuration System** | :white_check_mark: Complete | lib_layered_config + defaultconfig.toml |
| **Tools Venv Manager** | :white_check_mark: Complete | Isolated venv for analysis tools |
| **Scope Sub-server** | :white_check_mark: Complete | File discovery, git integration |
| **Quality Sub-server** | :white_check_mark: Complete | 18+ analysis types (see below) |
| **Security Sub-server** | :white_check_mark: Complete | Bandit integration |
| **Common Utilities** | :white_check_mark: Complete | Git, files, logging, protocol |
| **Test Suite** | :white_check_mark: Complete | 219 tests, 100% passing |

### Quality Sub-server Features

The quality sub-server provides comprehensive code analysis:

- **Complexity Analysis**: Cyclomatic complexity (radon), cognitive complexity
- **Maintainability**: Maintainability index, function length, nesting depth
- **Code Duplication**: Duplicate code detection (pylint)
- **Static Analysis**: Ruff linting with JSON output
- **Type Coverage**: mypy type checking
- **Dead Code**: Vulture dead code detection
- **Import Cycles**: Circular import detection
- **Docstring Coverage**: Interrogate integration
- **Test Analysis**: Test counting, assertion counting, OS-specific decorator detection
- **Architecture**: God object detection, coupling analysis
- **Runtime Checks**: Platform-specific code optimization opportunities
- **Code Churn**: Git history analysis for frequently modified files
- **Halstead Metrics**: Code complexity metrics
- **Raw Metrics**: LOC, SLOC, comment counts
- **JS/TS Support**: ESLint integration
- **Beartype**: Runtime type checking verification

### Cache Sub-server Features

The cache sub-server identifies `@lru_cache` optimization opportunities using a 4-stage pipeline:

1. **AST Analysis**: Detect pure functions (deterministic, no side effects)
2. **Profiling Cross-reference**: Match pure functions with runtime hotspots
3. **Batch Screening**: Test candidates for cache hit rate
4. **Individual Validation**: Measure precise performance impact

Key capabilities:
- **Pure Function Detection**: Identifies functions safe to cache
- **Existing Cache Evaluation**: Analyzes current `@lru_cache` decorators
- **Runtime Profiling Integration**: Uses cProfile data for accurate analysis
- **Static Fallback**: Works without profiling data using call-site analysis

See [Cache Subserver Documentation](docs/CACHE_SUBSERVER.md) for details.

### Additional Sub-servers

| Component | Status | Description |
|-----------|--------|-------------|
| **Performance Sub-server** | :white_check_mark: Complete | Runtime profiling analysis |
| **Docs Sub-server** | :white_check_mark: Complete | Documentation coverage |
| **Deps Sub-server** | :white_check_mark: Complete | Dependency analysis |
| **Cache Sub-server** | :white_check_mark: Complete | LRU cache optimization |
| **Review Orchestrator** | :white_check_mark: Complete | Coordinates all review sub-servers |
| **Fix Sub-servers** | :construction: Planned | Automated code fixing |

## Quick Start

### Installation

```bash
# Clone repository
git clone <repo-url>
cd glintefy

# Install with dev dependencies
make dev

# Run tests
make test
```

### Using Sub-servers Directly

```python
from pathlib import Path
from glintefy.subservers.review.scope import ScopeSubServer
from glintefy.subservers.review.quality import QualitySubServer
from glintefy.subservers.review.security import SecuritySubServer

# Step 1: Run scope analysis
scope = ScopeSubServer(
    output_dir=Path("LLM-CONTEXT/review-anal/scope"),
    repo_path=Path.cwd(),
    mode="full",  # or "git" for uncommitted changes only
)
scope_result = scope.run()

# Step 2: Run quality analysis (uses scope output)
quality = QualitySubServer(
    input_dir=Path("LLM-CONTEXT/review-anal/scope"),
    output_dir=Path("LLM-CONTEXT/review-anal/quality"),
    repo_path=Path.cwd(),
)
quality_result = quality.run()

# Step 3: Run security analysis
security = SecuritySubServer(
    input_dir=Path("LLM-CONTEXT/review-anal/scope"),
    output_dir=Path("LLM-CONTEXT/review-anal/security"),
    repo_path=Path.cwd(),
)
security_result = security.run()

# Access results
print(f"Quality issues: {quality_result.metrics['issues_count']}")
print(f"Security issues: {security_result.metrics['issues_found']}")
```

### Configuration

Configuration is loaded from multiple sources (lowest to highest priority):

1. `defaultconfig.toml` (bundled with package)
2. `~/.config/glintefy/config.toml` (user config)
3. Environment variables (`GLINTEFY_*`)
4. Constructor parameters

Example configuration override:

```python
# Override specific settings via constructor
quality = QualitySubServer(
    output_dir=output_dir,
    repo_path=repo_path,
    complexity_threshold=15,  # Override default of 10
    enable_beartype=False,    # Disable beartype checks
)
```

See `src/glintefy/defaultconfig.toml` for all available options.

## Tools Virtual Environment

Analysis tools (ruff, mypy, pylint, vulture, etc.) are installed in an isolated virtual environment:

- **Location**: `~/.cache/glintefy/tools-venv/`
- **Initialization**: Automatic on first use (idempotent)
- **Package Manager**: Uses `uv` for fast installation
- **Thread-safe**: Safe for concurrent access

```python
from glintefy.tools_venv import ensure_tools_venv, get_tool_path

# Ensure venv is ready (called automatically by sub-servers)
ensure_tools_venv()

# Get path to a specific tool
ruff_path = get_tool_path("ruff")
```

## Architecture

```
glintefy/
├── src/glintefy/
│   ├── __init__.py              # Package init
│   ├── config.py                # Configuration loader
│   ├── defaultconfig.toml       # Default configuration
│   ├── tools_venv.py            # Tools venv manager
│   │
│   ├── subservers/
│   │   ├── base.py              # BaseSubServer class
│   │   ├── common/              # Shared utilities
│   │   │   ├── files.py         # File operations
│   │   │   ├── git.py           # Git operations
│   │   │   ├── logging.py       # Logging utilities
│   │   │   └── protocol.py      # SubServerResult dataclass
│   │   │
│   │   └── review/              # Review sub-servers
│   │       ├── scope.py         # File discovery
│   │       ├── quality.py       # Code quality analysis
│   │       └── security.py      # Security scanning
│   │
│   └── servers/                 # MCP servers (planned)
│       └── __init__.py
│
├── tests/                       # Test suite (219 tests)
└── pyproject.toml              # Project metadata
```

## Sub-server Protocol

All sub-servers follow a consistent protocol:

```python
class BaseSubServer:
    def __init__(self, name, input_dir, output_dir, **config):
        """Initialize with input/output directories and config."""

    def validate_inputs(self) -> tuple[bool, list[str]]:
        """Validate required inputs exist."""

    def execute(self) -> SubServerResult:
        """Execute the analysis. Override in subclasses."""

    def run(self) -> SubServerResult:
        """Main entry point: validate, execute, handle errors."""

@dataclass
class SubServerResult:
    status: str          # SUCCESS, PARTIAL, FAILED
    summary: str         # Markdown summary
    artifacts: dict      # Output files {name: Path}
    metrics: dict        # Numeric metrics
    errors: list         # Error messages (if any)
```

## Development

### Prerequisites
- Python 3.9+ (tested on 3.13/3.14)
- Git
- Make (optional, for convenience commands)

### Setup
```bash
# Install in development mode
make dev

# Or manually
pip install -e ".[dev]"
```

### Testing
```bash
# Run all tests
make test

# Run without coverage (faster)
python -m pytest tests/ --no-cov

# Run specific test file
python -m pytest tests/subservers/review/test_quality.py -v
```

### Code Quality
```bash
# Linting
ruff check src/ tests/

# Type checking
pyright src/

# Formatting
black src/ tests/
```

## Configuration Reference

Key configuration options in `defaultconfig.toml`:

### Quality Analysis
```toml
[review.quality]
complexity_threshold = 10        # Max cyclomatic complexity
maintainability_threshold = 20   # Min maintainability index
max_function_length = 50         # Max lines per function
max_nesting_depth = 3            # Max nesting depth
cognitive_complexity_threshold = 15

# Feature flags
enable_type_coverage = true
enable_dead_code_detection = true
enable_import_cycle_detection = true
enable_docstring_coverage = true
enable_code_churn = true
enable_beartype = true
enable_static_analysis = true
enable_test_analysis = true
enable_architecture_analysis = true

# Thresholds
coupling_threshold = 15          # Max imports per module
god_object_methods_threshold = 20
god_object_lines_threshold = 500
churn_threshold = 20             # Commits to flag high churn
```

### Security Analysis
```toml
[review.security]
severity_threshold = "low"       # low, medium, high
confidence_threshold = "low"     # low, medium, high
```

### Scope Analysis
```toml
[review.scope]
mode = "git"                     # git (default) or full
exclude_patterns = [
    "vendor/",
    "node_modules/",
    ".venv/",
    "__pycache__/",
]
```

## Roadmap

### v0.1.0 (Current)
- :white_check_mark: Core infrastructure
- :white_check_mark: Scope, Quality, Security sub-servers
- :white_check_mark: Tools venv management
- :white_check_mark: Configuration system
- :white_check_mark: 219 tests passing

### v0.2.0 (Next)
- :construction: Review orchestrator server
- :construction: Performance sub-server
- :construction: Documentation sub-server
- :construction: Dependencies sub-server

### v0.3.0 (Future)
- :construction: Fix orchestrator server
- :construction: Evidence-based fixing protocol
- :construction: Git auto-commit/revert

### v1.0.0 (Target)
- Full MCP protocol integration
- All review sub-servers
- All fix sub-servers
- Complete documentation

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT License](LICENSE)

## Support

- **Issues**: [GitHub Issues](https://github.com/bitranox/glintefy/issues)
- **Documentation**: [docs/](docs/)
