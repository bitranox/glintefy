# Architecture Overview

System design and architecture of glintefy.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface                          │
├─────────────────────────────┬───────────────────────────────┤
│          CLI                │          MCP Server           │
│   (python -m glintefy)   │   (glintefy.servers)       │
└─────────────────────────────┴───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Review Orchestrator                      │
│                   (servers/review.py)                       │
└─────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Scope     │      │   Quality   │      │  Security   │
│ SubServer   │      │  SubServer  │      │  SubServer  │
└─────────────┘      └─────────────┘      └─────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                    Analysis Tools                           │
│      (radon, ruff, mypy, vulture, bandit, ...)             │
│           Isolated in ~/.cache/glintefy/tools-venv/     │
└─────────────────────────────────────────────────────────────┘
```

## Package Structure

```
src/glintefy/
├── __init__.py                  # Package init
├── cli.py                       # CLI entry point
├── config.py                    # Configuration loading
├── defaultconfig.toml           # Default configuration
├── tools_venv.py                # Tool environment manager
│
├── servers/                     # MCP servers
│   ├── __init__.py
│   └── review.py                # Review MCP server
│
└── subservers/                  # Analysis subservers
    ├── base.py                  # BaseSubServer class
    ├── common/                  # Shared utilities
    │   ├── files.py             # File operations
    │   ├── git.py               # Git operations
    │   ├── logging.py           # Logging utilities
    │   └── protocol.py          # SubServerResult
    │
    └── review/                  # Review subservers
        ├── scope.py             # File discovery
        ├── quality/             # Quality analysis
        │   ├── __init__.py
        │   ├── complexity.py
        │   ├── duplication.py
        │   └── ...
        ├── security.py          # Security scanning
        ├── deps.py              # Dependency analysis
        ├── docs.py              # Documentation analysis
        ├── perf.py              # Performance analysis
        ├── cache_subserver.py   # Cache optimization
        └── cache/               # Cache analysis modules
            ├── pure_function_detector.py
            ├── hotspot_analyzer.py
            ├── batch_screener.py
            └── ...
```

## Core Components

### SubServerResult

Standard result format for all subservers:

```python
@dataclass
class SubServerResult:
    status: str          # SUCCESS, PARTIAL, FAILED
    summary: str         # Markdown summary
    artifacts: dict      # {name: Path} output files
    metrics: dict        # Numeric metrics
    errors: list         # Error messages
```

### BaseSubServer

Base class all subservers inherit from:

```python
class BaseSubServer(ABC):
    def __init__(self, name, input_dir, output_dir, **config):
        """Initialize with directories and config."""

    def validate_inputs(self) -> tuple[bool, list[str]]:
        """Validate required inputs exist."""

    @abstractmethod
    def execute(self) -> SubServerResult:
        """Execute analysis. Override in subclasses."""

    def run(self) -> SubServerResult:
        """Main entry: validate, execute, handle errors."""
```

### ReviewMCPServer

Orchestrates subservers for MCP protocol:

```python
class ReviewMCPServer:
    def run_scope(self, mode="git") -> dict
    def run_quality() -> dict
    def run_security() -> dict
    def run_deps() -> dict
    def run_docs() -> dict
    def run_perf() -> dict
    def run_cache() -> dict
    def run_all(mode="git") -> dict

    def get_tool_definitions() -> list
    def handle_tool_call(name, args) -> dict
```

## Data Flow

### Review Pipeline

```
1. Scope Analysis
   └─> files_to_review.txt

2. Parallel Analysis
   ├─> Quality  ─> quality_summary.md, issues.json
   ├─> Security ─> security_summary.md, bandit_report.json
   ├─> Deps     ─> deps_summary.md
   ├─> Docs     ─> docs_summary.md
   ├─> Perf     ─> perf_summary.md
   └─> Cache    ─> cache_summary.md, candidates.json

3. Report Generation
   └─> code_review_report.md, verdict.json, metrics.json
```

### Output Directory

```
LLM-CONTEXT/glintefy/review/
├── scope/
│   ├── files_to_review.txt
│   ├── status.txt
│   └── scope_summary.md
├── quality/
│   ├── quality_summary.md
│   ├── complexity.json
│   └── issues.json
├── security/
│   ├── security_summary.md
│   └── bandit_report.json
├── deps/
│   └── deps_summary.md
├── docs/
│   └── docs_summary.md
├── perf/
│   ├── perf_summary.md
│   └── test_profile.prof
├── cache/
│   ├── cache_summary.md
│   └── candidates.json
└── report/
    ├── code_review_report.md
    ├── verdict.json
    └── metrics.json
```

## Tools Virtual Environment

Analysis tools are installed in an isolated environment:

```
~/.cache/glintefy/tools-venv/
├── bin/
│   ├── python
│   ├── ruff
│   ├── mypy
│   ├── pylint
│   ├── vulture
│   ├── bandit
│   └── ...
└── lib/
```

**Benefits:**
- No conflicts with project dependencies
- Consistent tool versions
- Automatic installation on first use

## Configuration System

```
defaultconfig.toml (bundled)
         │
         ▼
~/.config/glintefy/config.toml (user)
         │
         ▼
Environment variables (GLINTEFY_*)
         │
         ▼
Constructor parameters (Python API)
```

## Cache Analysis Pipeline

```
1. AST Analysis (pure_function_detector.py)
   └─> Identify pure functions (deterministic, no side effects)

2. Profiling Cross-reference (hotspot_analyzer.py)
   └─> Match pure functions with runtime hotspots

3. Batch Screening (batch_screener.py)
   └─> Test candidates for cache hit rate

4. Individual Validation (individual_validator.py)
   └─> Measure precise performance impact
```

## Next Steps

- [CLI Reference](../cli/REFERENCE.md) - CLI usage
- [MCP Tools](../mcp/TOOLS.md) - MCP server usage
- [Configuration](../reference/CONFIGURATION.md) - All settings
- [Cache Subserver](../CACHE_SUBSERVER.md) - Cache optimization details
