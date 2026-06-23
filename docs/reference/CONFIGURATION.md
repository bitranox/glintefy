# Configuration Reference

Complete reference for all glintefy configuration options.

## Configuration Priority

Settings are loaded from (lowest to highest priority):

1. `defaultconfig.toml` (bundled with package)
2. `~/.config/glintefy/config.toml` (user config)
3. Environment variables (`GLINTEFY_*`)
4. Constructor parameters (Python API)

## Configuration File

Create `~/.config/glintefy/config.toml`:

```toml
[review.quality]
complexity_threshold = 15
max_function_length = 60

[review.security]
severity_threshold = "medium"
```

## Environment Variables

Pattern: `GLINTEFY___{SECTION}__{KEY}` (triple underscore after prefix, double underscore between sections)

```bash
export GLINTEFY___REVIEW__QUALITY__COMPLEXITY_THRESHOLD=15
export GLINTEFY___REVIEW__SECURITY__SEVERITY_THRESHOLD=medium
export GLINTEFY___GENERAL__TIMEOUTS__TOOL_LONG=300
```

---

## General Settings

```toml
[general]
output_dir = "LLM-CONTEXT"           # Output directory
log_level = "INFO"                    # DEBUG, INFO, WARNING, ERROR
verbose = false                       # Verbose output
max_workers = 4                       # Parallel workers
```

---

## Review Settings

### Scope

```toml
[review.scope]
mode = "git"                          # "git" (default) or "full"
exclude_patterns = [
    # Virtual environments
    "**/.venv/**/*", "**/venv/**/*", "**/.virtualenv/**/*",
    # Dependency/cache directories
    "**/vendor/**/*", "**/node_modules/**/*", "**/__pycache__/**/*",
    "**/.tox/**/*", "**/.nox/**/*", "**/.pytest_cache/**/*",
    "**/.mypy_cache/**/*", "**/.ruff_cache/**/*",
    # Build artifacts
    "**/dist/**/*", "**/build/**/*", "**/*.egg-info/**/*",
    # Version control
    "**/.git/**/*",
    # IDE and editor configs
    "**/.claude/**/*", "**/.devcontainer/**/*",
    "**/.idea/**/*", "**/.vscode/**/*",
    # CI/CD and tooling
    "**/.github/**/*", "**/.qlty/**/*",
    # Project-specific
    "**/LLM-CONTEXT/**/*", "**/scripts/**/*",
    # Config files
    "*.example", "codecov.yml", ".snyk",
]
include_patterns = ["**/*"]
```

### Quality

```toml
[review.quality]
# Thresholds
complexity_threshold = 10             # Max cyclomatic complexity
maintainability_threshold = 20        # Min maintainability index
cognitive_complexity_threshold = 15   # Max cognitive complexity
max_function_length = 50              # Max lines per function
max_nesting_depth = 3                 # Max nesting levels
coupling_threshold = 15               # Max imports per module
god_object_methods_threshold = 20     # Max methods per class
god_object_lines_threshold = 500      # Max lines per class
churn_threshold = 20                  # Commits for high churn

# Feature Flags
enable_static_analysis = true         # Ruff linting
enable_duplication_detection = true   # Pylint duplication
min_duplicate_lines = 5               # Min duplicate lines
enable_type_coverage = true           # Mypy type checking
min_type_coverage = 80                # Min type coverage %
enable_dead_code_detection = true     # Vulture dead code
dead_code_confidence = 80             # Min confidence %
enable_docstring_coverage = true      # Interrogate
min_docstring_coverage = 80           # Min docstring coverage %
enable_import_cycle_detection = true  # Circular imports
enable_architecture_analysis = true   # God objects, coupling
detect_god_objects = true
detect_high_coupling = true
enable_code_churn = true              # Git history analysis
enable_test_analysis = true           # Test analysis
count_test_assertions = true
enable_cognitive_complexity = true
enable_halstead_metrics = true
enable_raw_metrics = true
enable_js_analysis = true             # ESLint for JS/TS
enable_beartype = true                # Runtime type checking
enable_runtime_check_detection = true
```

### Security

```toml
[review.security]
severity_threshold = "low"            # "low", "medium", "high"
confidence_threshold = "low"          # "low", "medium", "high"
bandit_config = ""                    # Optional bandit config path
skip_tests = []                       # Bandit test IDs to skip
exclude_paths = []                    # Additional paths to exclude
critical_threshold = 1                # High issues for CRITICAL status
warning_threshold = 5                 # Medium issues for WARNING status
```

### Dependencies

```toml
[review.deps]
scan_vulnerabilities = true
check_licenses = true
allowed_licenses = [
    "MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause",
    "ISC", "MPL-2.0", "LGPL-2.1", "LGPL-3.0",
]
disallowed_licenses = ["GPL-3.0", "AGPL-3.0"]
check_outdated = true
max_age_days = 365                    # Max dependency age (0 = no limit)
```

### Documentation

```toml
[review.docs]
check_docstrings = true
docstring_style = "google"            # "google", "numpy", "sphinx"
min_coverage = 80                     # Min docstring coverage %
require_readme = true
require_changelog = false
required_readme_sections = ["Installation", "Usage"]
```

### Performance

```toml
[review.perf]
estimate_runtime = true
estimate_memory = true
runtime_threshold_ms = 100            # Flag functions > this
memory_threshold_mb = 50              # Flag modules > this
detect_complexity = true              # O(n^2), O(n!) detection
nested_loop_threshold = 2             # Flag deep nested loops
```

### Cache

```toml
[review.cache]
cache_size = 128                      # LRU cache maxsize for testing
hit_rate_threshold = 20.0             # Min hit rate % to recommend
speedup_threshold = 5.0               # Min speedup % to recommend
min_calls = 100                       # Min calls for hotspot
min_cumtime = 0.1                     # Min cumulative time (seconds)
test_timeout = 300                    # Test timeout (seconds)
num_runs = 3                          # Timing runs for stability
max_profile_age_hours = 24.0          # Max profile age before warning
```

---

## Tool Settings

### Radon

```toml
[tools.radon]
show_all = true
show_average = true
sort_by = "score"                     # "score", "filename", "line"
```

### Pylint

```toml
[tools.pylint]
jobs = 0                              # 0 = auto
output_format = "json"
reports = false
max_line_length = 88
good_names = ["i", "j", "k", "ex", "_", "id", "pk"]
```

### Ruff

```toml
[tools.ruff]
line_length = 88
target_version = "py313"
select = ["E", "F", "W", "I", "N", "UP", "B", "C4", "SIM"]
ignore = ["E501"]
fix = true
unsafe_fixes = false
```

### MyPy

```toml
[tools.mypy]
python_version = "3.13"
strict = false
ignore_missing_imports = true
show_error_codes = true
pretty = true
```

### Bandit

```toml
[tools.bandit]
min_severity = 1                      # 1=LOW, 2=MEDIUM, 3=HIGH
min_confidence = 1                    # 1=LOW, 2=MEDIUM, 3=HIGH
format = "json"
recursive = true
processes = 4
```

### Pytest

```toml
[tools.pytest]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
cov_fail_under = 80
cov_report = ["term-missing", "html"]
```

---

## Display Limits

```toml
[output.display]
max_sample_files = 10                 # Files in scope report
max_high_security = 10                # High severity issues
max_medium_security = 10              # Medium severity issues
max_vulnerabilities = 10              # Vulnerability issues
max_outdated_packages = 10            # Outdated packages
max_license_issues = 5                # License violations
max_missing_docstrings = 15           # Missing docstring examples
max_hotspots = 10                     # Performance hotspots
max_pattern_issues = 10               # Performance anti-patterns
max_critical_display = 20             # Critical issues in summary
max_metrics_display = 5               # Metrics per sub-server
```

---

## Timeouts

```toml
[general.timeouts]
git_quick_op = 10                     # Quick git commands (is_git_repo, get_branch)
git_status = 20                       # Git status operations
git_commit = 60                       # Git commit (may run pre-commit hooks)
git_log = 20                          # Git log/history
git_diff = 60                         # Git diff operations
git_blame = 10                        # Git blame
tool_quick = 60                       # Fast tools (radon, etc.)
tool_analysis = 120                   # Standard tools (ruff, interrogate, bandit)
tool_long = 240                       # Slow tools (mypy, pylint, pytest)
profile_tests = 600                   # Test profiling (10 minutes)
beartype_check = 120                  # Beartype runtime type checking
vuln_scan = 240                       # Dependency vulnerability scanning
```

---

## Python API Configuration

```python
from glintefy.subservers.review.quality import QualitySubServer

# Override via constructor
quality = QualitySubServer(
    output_dir=output_dir,
    repo_path=repo_path,
    complexity_threshold=15,
    max_function_length=60,
    enable_beartype=False,
)
```

---

## Example Configurations

### Strict Quality

```toml
[review.quality]
complexity_threshold = 8
max_function_length = 40
max_nesting_depth = 2
min_type_coverage = 90
min_docstring_coverage = 95
```

### Security Focus

```toml
[review.security]
severity_threshold = "low"
confidence_threshold = "low"
critical_threshold = 0

[review.deps]
scan_vulnerabilities = true
max_age_days = 180
```

### Performance Focus

```toml
[review.perf]
runtime_threshold_ms = 50
nested_loop_threshold = 1

[review.cache]
hit_rate_threshold = 10.0
speedup_threshold = 3.0
```

---

## Next Steps

- [CLI Reference](../cli/REFERENCE.md) - CLI commands
- [MCP Tools](../mcp/TOOLS.md) - MCP server tools
- [Architecture](../architecture/OVERVIEW.md) - System design
