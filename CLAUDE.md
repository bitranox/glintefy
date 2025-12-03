# Claude Code Guidelines for glintefy

## Session Initialization

When starting a new session, read and apply the following system prompt files from `/media/srv-main-softdev/projects/softwarestack/systemprompts`:

### Core Guidelines (Always Apply)
- `core_programming_solid.md`

### Bash-Specific Guidelines
When working with Bash scripts:
- `core_programming_solid.md`
- `bash_clean_architecture.md`
- `bash_clean_code.md`
- `bash_small_functions.md`

### Python-Specific Guidelines
When working with Python code:
- `core_programming_solid.md`
- `python_solid_architecture_enforcer.md`
- `python_clean_architecture.md`
- `python_clean_code.md`
- `python_small_functions_style.md`
- `python_libraries_to_use.md`
- `python_lib_structure_template.md`

### Additional Guidelines
- `self_documenting.md`
- `self_documenting_template.md`
- `python_jupyter_notebooks.md`
- `python_testing.md`

## Project Structure

```
glintefy/
├── .github/
│   └── workflows/              # GitHub Actions CI/CD workflows
├── .devcontainer/              # Dev container configuration
├── docs/                       # Project documentation
│   └── systemdesign/           # System design documents
├── notebooks/                  # Jupyter notebooks for experiments
├── scripts/                    # Build and automation scripts
│   ├── build.py               # Build wheel/sdist
│   ├── bump*.py               # Version bump scripts
│   ├── clean.py               # Clean build artifacts
│   ├── test.py                # Run tests with coverage
│   ├── push.py                # Git push with monitoring
│   ├── release.py             # Create releases
│   ├── menu.py                # Interactive TUI menu
│   └── _utils.py              # Shared utilities
├── src/
│   └── glintefy/  # Main Python package
│       ├── __init__.py        # Package initialization
│       ├── __init__conf__.py  # Configuration loader
│       ├── __main__.py        # CLI entry point
│       ├── cli.py             # CLI implementation
│       ├── behaviors.py       # Core behaviors/business logic
│       └── py.typed           # PEP 561 marker
├── tests/                     # Test suite
├── .env.example               # Example environment variables
├── CLAUDE.md                  # Claude Code guidelines (this file)
├── CHANGELOG.md               # Version history
├── CONTRIBUTING.md            # Contribution guidelines
├── DEVELOPMENT.md             # Development setup guide
├── INSTALL.md                 # Installation instructions
├── Makefile                   # Make targets for common tasks
├── pyproject.toml             # Project metadata & dependencies
├── codecov.yml                # Codecov configuration
└── README.md                  # Project overview
```

## Versioning & Releases

- **Single Source of Truth**: Package version is in `pyproject.toml` (`[project].version`)
- **Version Bumps**: update `pyproject.toml` , `CHANGELOG.md` and update the constants in `src/../__init__conf__.py` according to `pyproject.toml`  
    - Automation rewrites `src/glintefy/__init__conf__.py` from `pyproject.toml`, so runtime code imports generated constants instead of querying `importlib.metadata`.
    - After updating project metadata (version, summary, URLs, authors) run `make test` (or `python -m scripts.test`) to regenerate the metadata module before committing.
- **Release Tags**: Format is `vX.Y.Z` (push tags for CI to build and publish)

## Common Make Targets

| Target            | Description                                                                     |
|-------------------|---------------------------------------------------------------------------------|
| `build`           | Build wheel/sdist artifacts                                                     |
| `bump`            | Bump version (VERSION=X.Y.Z or PART=major\|minor\|patch) and update changelog  |
| `bump-major`      | Increment major version ((X+1).0.0)                                            |
| `bump-minor`      | Increment minor version (X.Y.Z → X.(Y+1).0)                                    |
| `bump-patch`      | Increment patch version (X.Y.Z → X.Y.(Z+1))                                    |
| `clean`           | Remove caches, coverage, and build artifacts (includes `dist/` and `build/`)   |
| `dev`             | Install package with dev extras                                                |
| `help`            | Show make targets                                                              |
| `install`         | Editable install                                                               |
| `menu`            | Interactive TUI menu                                                           |
| `push`            | Commit changes and push to GitHub (no CI monitoring)                           |
| `release`         | Tag vX.Y.Z, push, sync packaging, run gh release if available                  |
| `run`             | Run module entry (`python -m ... --help`)                                      |
| `test`            | Lint, format, type-check, run tests with coverage, upload to Codecov           |
| `version-current` | Print current version from `pyproject.toml`                                    |

## Coding Style & Naming Conventions

Follow the guidelines in `python_clean_code.md` for all Python code.

## Architecture Overview

Apply principles from `python_clean_architecture.md` when designing and implementing features.

## Security & Configuration

- `.env` files are for local tooling only (CodeCov tokens, etc.)
- **NEVER** commit secrets to version control
- Rich logging should sanitize payloads before rendering

## Documentation & Translations

### Web Documentation
- Update only English docs under `/website/docs`
- Other languages are translated automatically
- When in doubt, ask before modifying non-English documentation

### App UI Strings (i18n)
- Update only `sources/_locales/en` for string changes
- Other languages are translated automatically
- When in doubt, ask before modifying non-English locales

## Commit & Push Policy

### Pre-Push Requirements
- **Always run `make test` before pushing** to avoid lint/test breakage
- Ensure all tests pass and code is properly formatted

### Post-Push Monitoring
- Monitor GitHub Actions for errors after pushing
- Attempt to correct any CI/CD errors that appear

## Snapshot Before Major Changes

**ALWAYS create a snapshot before making significant code changes** to enable easy rollback if something goes wrong.

### When to Create Snapshots
- Before refactoring multiple files
- Before modernizing syntax across the codebase
- Before making breaking changes to APIs or interfaces
- Before any batch/automated code modifications

### How to Create Snapshots
```bash
# Option 1: Create a temporary commit (preferred)
git add -A && git commit -m "SNAPSHOT: Before [description of changes]"

# Option 2: Create a stash with description
git stash push -m "SNAPSHOT: Before [description of changes]"

# Option 3: Create a branch
git checkout -b snapshot/before-[description]
git checkout -  # Return to original branch
```

### How to Rollback
```bash
# If using temporary commit
git reset --soft HEAD~1  # Undo commit, keep changes staged
git reset --hard HEAD~1  # Undo commit AND discard changes

# If using stash
git stash pop

# If using branch
git checkout snapshot/before-[description]
```

### Important
- Always verify tests pass AFTER rolling back
- Delete temporary snapshot commits/branches after successful changes
- Document what the snapshot was for in the commit/stash message

## Configuration Testing Requirements

When adding or modifying configuration settings:

1. **Document in defaultconfig.toml**: All configuration keys used by sub-servers MUST be documented in `src/glintefy/defaultconfig.toml`, even if commented out
2. **Match key names**: Config keys in code must exactly match keys in defaultconfig.toml
3. **Test config loading**: Add tests in `tests/test_config.py` to verify:
   - New config keys are documented in defaultconfig.toml
   - Sub-servers correctly read the config values
   - Constructor parameters override config file values
   - Default values are sensible

### Config Key Naming Conventions
- Use `snake_case` for all keys (lowercase with underscores)
- Boolean feature flags: Use `enable_` prefix (e.g., `enable_type_coverage`)
- Thresholds: Use `_threshold` suffix or `min_`/`max_` prefix (e.g., `complexity_threshold`, `min_coverage`)
- No hyphens or spaces in key names

### Config Section Structure
```toml
[general]           # Global settings
[review]            # Review orchestrator settings
[review.scope]      # Scope sub-server
[review.quality]    # Quality sub-server
[review.security]   # Security sub-server
[fix]               # Fix orchestrator settings
[fix.scope]         # Fix scope settings
[tools.toolname]    # Tool-specific settings (bandit, ruff, mypy, etc.)
```

### Example: Adding a New Config Key
```python
# 1. Add to defaultconfig.toml under appropriate section:
# [review.quality]
# my_new_threshold = 10

# 2. Read in sub-server __init__:
self.my_new_threshold = config.get("my_new_threshold", 10)

# 3. Add test in tests/test_config.py:
def test_quality_reads_my_new_threshold(self):
    # Verify key is documented
    config_text = _DEFAULT_CONFIG_FILE.read_text()
    assert "my_new_threshold" in config_text
```

## MCP Server Logging Requirements

All MCP server components MUST implement detailed debug and error logging for troubleshooting. **No log files** - logs go to stderr only (MCP protocol uses stdout).

### Logging Utilities

Use the logging utilities from `src/glintefy/subservers/common/logging.py`:

```python
from glintefy.subservers.common.logging import (
    get_mcp_logger,        # Get logger that outputs to stderr only
    log_debug,             # Debug message with context dict
    log_error_detailed,    # Error with traceback and context
    log_function_call,     # Log function entry with args
    log_function_result,   # Log function exit with result
    debug_log,             # Decorator for auto function tracing
    log_config_loaded,     # Log config values (redacts secrets)
    log_subprocess_call,   # Log subprocess before execution
    log_subprocess_result, # Log subprocess after completion
    log_tool_execution,    # Log analysis tool summary
)
```

### Logging Requirements

1. **Use `get_mcp_logger()`** - Returns a logger that outputs to stderr only (no files)
2. **Log function entry/exit** - Use `@debug_log(logger)` decorator or manual `log_function_call`/`log_function_result`
3. **Log errors with context** - Use `log_error_detailed()` to include traceback and relevant context
4. **Redact secrets** - Use `log_config_loaded()` which auto-redacts keys containing: `password`, `secret`, `token`, `key`, `api_key`, `auth`
5. **Log subprocess calls** - Use `log_subprocess_call()` before and `log_subprocess_result()` after

### Sub-Server MCP Mode

All sub-servers support a `mcp_mode` parameter that switches logging:

```python
# Standalone mode (default): logs to stdout
server = ScopeSubServer(output_dir=output_dir, mcp_mode=False)

# MCP mode: logs to stderr only (MCP protocol uses stdout)
server = ScopeSubServer(output_dir=output_dir, mcp_mode=True)
```

### Example: Sub-Server with Logging

```python
from glintefy.subservers.common.logging import (
    get_mcp_logger, log_error_detailed, debug_log
)

class MySubServer(BaseSubServer):
    def __init__(self, ..., mcp_mode: bool = False):
        super().__init__(...)
        if mcp_mode:
            self._logger = get_mcp_logger(f"glintefy.{self.name}")
        else:
            self._logger = setup_logger(self.name, log_file=None, level=20)

    @debug_log(_logger)  # Auto-logs entry, exit, and errors
    def run(self) -> SubServerResult:
        try:
            # ... implementation ...
        except Exception as e:
            log_error_detailed(
                self._logger, e,
                context={"files": len(self.files)},
                include_traceback=True,
            )
            raise
```

### MCP Server Implementation

The `ReviewMCPServer` wraps sub-servers for MCP protocol:

```python
from glintefy.servers.review import ReviewMCPServer

# Create MCP server
server = ReviewMCPServer(repo_path=Path("."))

# Run individual tools
result = server.run_scope(mode="git")
result = server.run_quality()
result = server.run_security()

# Run all reviews
result = server.run_all(mode="git")

# Get MCP tool definitions
tools = server.get_tool_definitions()

# Handle MCP tool call
result = server.handle_tool_call("review_scope", {"mode": "full"})
```

### Testing Logging

When testing code that uses `get_mcp_logger()`, use `capsys` instead of `caplog` (logger has `propagate=False`):

```python
def test_my_function_logs_debug(self, capsys):
    logger = get_mcp_logger("test_logger")
    my_function(logger)
    captured = capsys.readouterr()
    assert "expected message" in captured.err
```

## Code Review Quality Analyses

When reviewing code in this project, **run these tools** to ensure quality:

### Required Analysis Tools

| Tool | Command | Purpose |
|------|---------|---------|
| **ruff** | `ruff check src/ tests/` | Linting, style, potential bugs |
| **mypy** | `mypy src/` | Type checking and coverage |
| **pylint** | `pylint src/` | Code duplication, code smells |
| **vulture** | `vulture src/` | Dead/unused code detection |
| **interrogate** | `interrogate src/` | Docstring coverage |
| **radon** | `radon cc src/ -a` | Cyclomatic complexity |
| **radon** | `radon mi src/` | Maintainability index |
| **bandit** | `bandit -r src/` | Security vulnerabilities |

### Quick Quality Check

```bash
# Run all quality checks at once
ruff check src/ tests/ && mypy src/ && radon cc src/ -a -nc
```

### Quality Thresholds

- Cyclomatic Complexity: **≤10** per function (A/B grade)
- Maintainability Index: **≥20** per file (A grade)
- Type Coverage: **≥80%**
- Docstring Coverage: **≥80%**
- No high/critical security issues from bandit

### Analysis Types Reference

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

## Claude Code Workflow

When working on this project:
1. Read relevant system prompts at session start
2. Apply appropriate coding guidelines based on file type
3. Run `make test` before commits
4. Follow versioning guidelines for releases
5. Monitor CI after pushing changes
6. **When adding config keys**: Follow Configuration Testing Requirements above
7. **When adding MCP components**: Follow MCP Server Logging Requirements above
- review everything what we have now
- always update the mindset for new mcp subservers or analyzers
- No more sqlite errors. When you need coverage, run explicitly:

  pytest --cov=src/glintefy --cov-report=term-missing
- on user command "full review" run python -m glintefy review all --mode full  , and analyze the code_review_report in LLM-CONTEXT/glintefy/review/report/all_issues.json after finishing the command
- ignore the slow tests - those are slow dependecy tests
- remove legacy code or backwards compatibility code in the whole codebase. we are in development, we dont care about backward compatibility
- only document current behaviour, no development fragments - dont document old, before etc ... only current state !
- consider dataclasses instead of dict-based
