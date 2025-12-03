# CLI Reference

Complete reference for all glintefy CLI commands.

## Global Options

```bash
python -m glintefy [OPTIONS] COMMAND
```

| Option | Required | Default          | Permitted Values | Description |
|--------|----------|------------------|------------------|-------------|
| `--help`, `-h` | No | -                | - | Show help message |
| `--version` | No | -                | - | Show version |
| `--traceback/--no-traceback` | No | `--no-traceback` | - | Show full Python traceback on errors |

---

## Config Commands

Configuration management commands for deploying, viewing, and managing configuration files.

### `config-deploy`

Deploy default configuration to system or user directories.

```bash
python -m glintefy config-deploy [OPTIONS]
```

| Option | Required | Default | Permitted Values | Description |
|--------|----------|---------|------------------|-------------|
| `--target` | **Yes** | - | `app`, `host`, `user` | Target layer(s) to deploy to (repeatable) |
| `--force` | No | `false` | Flag (no value) | Overwrite existing configuration files |

**Target values:**
| Value | Description |
|-------|-------------|
| `app` | System-wide application config (recommended) |
| `host` | System-wide host config |
| `user` | User-specific config (~/.config on Linux) |

**Platform-specific paths:**
- **Linux (app)**: `/etc/xdg/glintefy/config.toml`
- **Linux (user)**: `~/.config/glintefy/config.toml`
- **macOS (app)**: `/Library/Application Support/bitranox/Glintefy/config.toml`
- **macOS (user)**: `~/Library/Application Support/bitranox/Glintefy/config.toml`
- **Windows (app)**: `C:\ProgramData\bitranox\Glintefy\config.toml`
- **Windows (user)**: `%APPDATA%\bitranox\Glintefy\config.toml`

**Examples:**
```bash
# Deploy to application directory (recommended)
python -m glintefy config-deploy --target app

# Deploy to user config directory
python -m glintefy config-deploy --target user

# Deploy to multiple targets
python -m glintefy config-deploy --target app --target user

# Force overwrite existing config
python -m glintefy config-deploy --target user --force
```

---

### `config-show`

Show current effective configuration (merged from all sources).

```bash
python -m glintefy config-show [OPTIONS]
```

| Option | Required | Default | Permitted Values | Description |
|--------|----------|---------|------------------|-------------|
| `--section`, `-s` | No | all | Dotted path (e.g., `review.quality`, `general.timeouts`) | Show only specific section |
| `--json` | No | `false` | Flag (no value) | Output as JSON instead of TOML-like format |

**Examples:**
```bash
# Show all configuration
python -m glintefy config-show

# Show quality settings only
python -m glintefy config-show -s review.quality

# Show security settings as JSON
python -m glintefy config-show -s review.security --json

# Show timeout settings
python -m glintefy config-show -s general.timeouts
```

---

### `config-path`

Show all configuration file locations and their status.

```bash
python -m glintefy config-path
```

No options. Displays:
- Package defaults location (always exists)
- User config location (platform-specific)
- Project config location
- Environment variable format

---

## Review Commands

All review commands support `--repo PATH` to specify the target repository.

| Option | Required | Default | Permitted Values | Description |
|--------|----------|---------|------------------|-------------|
| `--repo`, `-r` | No | `.` (current directory) | Any valid directory path | Repository path to analyze |

---

### `review all`

Run all review analyses.

```bash
python -m glintefy review [--repo PATH] all [OPTIONS]
```

| Option | Required | Default | Permitted Values | Description |
|--------|----------|---------|------------------|-------------|
| `--mode`, `-m` | No | `git` | `git`, `full` | Scope mode |
| `--complexity` | No | `10` | Any positive integer | Maximum cyclomatic complexity threshold |
| `--severity` | No | `low` | `low`, `medium`, `high` | Minimum security severity to report |

**Mode values:**
- `git` - Review only uncommitted changes (requires git repository, falls back to `full` if not available)
- `full` - Review all files in the repository

> **Note**: If `--mode git` is used but the directory is not a git repository, it automatically falls back to `full` mode with a warning.

**Example:**
```bash
# Review uncommitted git changes (default)
python -m glintefy review all

# Review all files
python -m glintefy review all --mode full

# Review at specific path
python -m glintefy review --repo /path/to/project all

# Review with custom thresholds
python -m glintefy review all --complexity 15 --severity high
```

---

### `review scope`

Discover files to analyze.

```bash
python -m glintefy review scope [OPTIONS]
```

| Option | Required | Default | Permitted Values | Description |
|--------|----------|---------|------------------|-------------|
| `--mode`, `-m` | No | `git` | `git`, `full` | Scope mode |

**Mode values:**
- `git` - Scan only uncommitted changes (requires git repository, falls back to `full` if not available)
- `full` - Scan all files in the repository

> **Note**: If `--mode git` is used but the directory is not a git repository, it automatically falls back to `full` mode with a warning.

---

### `review quality`

Run code quality analysis.

```bash
python -m glintefy review quality [OPTIONS]
```

| Option | Required | Default | Permitted Values | Description |
|--------|----------|---------|------------------|-------------|
| `--complexity`, `-c` | No | `10` | Any positive integer | Maximum cyclomatic complexity threshold |
| `--maintainability`, `-m` | No | `20` | Any positive integer (0-100) | Minimum maintainability index threshold |

**Threshold guidelines:**
- **Complexity**: Lower is better. Values >10 indicate complex functions that should be refactored.
- **Maintainability**: Higher is better. Values <20 indicate hard-to-maintain code.

**Analyzes:**
- Cyclomatic complexity (threshold: <=10)
- Function length (threshold: <=50 lines)
- Nesting depth (threshold: <=3 levels)
- Maintainability index (threshold: >=20)
- Code duplication
- Dead code
- Type coverage
- Import cycles
- God objects

---

### `review security`

Run security vulnerability scan.

```bash
python -m glintefy review security [OPTIONS]
```

| Option | Required | Default | Permitted Values | Description |
|--------|----------|---------|------------------|-------------|
| `--severity`, `-s` | No | `low` | `low`, `medium`, `high` | Minimum severity to report |
| `--confidence`, `-c` | No | `low` | `low`, `medium`, `high` | Minimum confidence to report |

**Severity levels:**
- `low` - Report all issues including minor ones
- `medium` - Report medium and high severity issues only
- `high` - Report only high severity (critical) issues

**Confidence levels:**
- `low` - Report all findings including uncertain ones
- `medium` - Report medium and high confidence findings only
- `high` - Report only high confidence (definite) findings

**Uses Bandit to detect:**
- Hardcoded passwords
- SQL injection
- Command injection
- Weak cryptography
- Other OWASP vulnerabilities

---

### `review deps`

Analyze dependencies.

```bash
python -m glintefy review deps [OPTIONS]
```

| Option | Required | Default | Permitted Values | Description |
|--------|----------|---------|------------------|-------------|
| `--no-vulnerabilities` | No | `false` (enabled) | Flag (no value) | Skip vulnerability scanning |
| `--no-licenses` | No | `false` (enabled) | Flag (no value) | Skip license compliance checking |
| `--no-outdated` | No | `false` (enabled) | Flag (no value) | Skip outdated package detection |

**Flag behavior:**
- Flags are boolean switches. Include the flag to disable the check.
- By default, all checks are enabled.

**Example:**
```bash
# Run all dependency checks (default)
python -m glintefy review deps

# Skip vulnerability scan
python -m glintefy review deps --no-vulnerabilities

# Only check for outdated packages
python -m glintefy review deps --no-vulnerabilities --no-licenses
```

**Checks:**
- Known vulnerabilities (CVEs)
- Outdated packages
- License compliance

---

### `review docs`

Analyze documentation coverage.

```bash
python -m glintefy review docs [OPTIONS]
```

| Option | Required | Default | Permitted Values | Description |
|--------|----------|---------|------------------|-------------|
| `--min-coverage`, `-c` | No | `80` | Integer 0-100 | Minimum docstring coverage percentage |

**Coverage guidelines:**
- `80`+ - Good documentation coverage
- `50-79` - Moderate coverage, consider improving
- `<50` - Poor coverage, needs attention

**Checks:**
- Docstring coverage (threshold: >=80%)
- Missing parameter documentation
- Missing return documentation

---

### `review perf`

Run performance analysis.

```bash
python -m glintefy review perf [OPTIONS]
```

| Option | Required | Default | Permitted Values | Description |
|--------|----------|---------|------------------|-------------|
| `--no-profiling` | No | `false` (enabled) | Flag (no value) | Skip profile data analysis |

**Flag behavior:**
- Include `--no-profiling` to skip analysis of existing profile data.
- By default, profiling analysis is enabled if profile data exists.

**Analyzes:**
- Function hotspots
- Performance anti-patterns
- Algorithm complexity

---

### `review cache`

Analyze cache optimization opportunities.

```bash
python -m glintefy review cache [OPTIONS]
```

| Option | Required | Default | Permitted Values | Description |
|--------|----------|---------|------------------|-------------|
| `--cache-size` | No | `128` | Any positive integer | LRU cache maxsize for testing |
| `--hit-rate` | No | `20.0` | Float 0.0-100.0 | Minimum cache hit rate % to recommend |
| `--speedup` | No | `5.0` | Float >= 0.0 | Minimum speedup % to recommend |

**Parameter guidelines:**
- **cache-size**: Common values are powers of 2 (64, 128, 256, 512). Larger values use more memory.
- **hit-rate**: Functions with hit rates below this threshold are not recommended for caching.
- **speedup**: Functions with speedup below this threshold are not recommended for caching.

**Identifies:**
- Pure functions suitable for caching
- Existing cache effectiveness
- Recommended `@lru_cache` decorators

> **Note**: For best results, run `review profile` first to generate profiling data.

---

### `review profile`

Profile a command for cache analysis.

```bash
python -m glintefy review profile -- COMMAND [ARGS...]
```

| Argument | Required | Default | Permitted Values | Description |
|----------|----------|---------|------------------|-------------|
| `COMMAND` | **Yes** | - | Any shell command | Command to profile (everything after `--`) |

**Command formats:**
- `python script.py` - Profile a Python script
- `pytest tests/` - Profile test execution
- `python -m module` - Profile a Python module

**Examples:**
```bash
# Profile test suite
python -m glintefy review profile -- pytest tests/

# Profile a script
python -m glintefy review profile -- python my_script.py

# Profile a module
python -m glintefy review profile -- python -m my_module

# Profile with arguments
python -m glintefy review profile -- pytest tests/ -v --tb=short
```

---

### `review report`

Generate consolidated report from existing analysis results.

```bash
python -m glintefy review report
```

No options. Requires previous analysis runs (scope, quality, etc.) to have been executed.

---

### `review clean`

Clean analysis output files.

```bash
python -m glintefy review clean [OPTIONS]
```

| Option | Required | Default | Permitted Values | Description |
|--------|----------|---------|------------------|-------------|
| `-s`, `--subserver` | No | `all` | `all`, `scope`, `quality`, `security`, `deps`, `docs`, `perf`, `cache`, `report`, `profile` | Subserver output to clean |
| `--dry-run` | No | `false` | Flag (no value) | Show what would be deleted without deleting |

**Subserver values:**
| Value | Description |
|-------|-------------|
| `all` | Clean all review data (entire `LLM-CONTEXT/glintefy/review/` directory) |
| `scope` | Clean scope analysis output (`review/scope/`) |
| `quality` | Clean quality analysis output (`review/quality/`) |
| `security` | Clean security scan output (`review/security/`) |
| `deps` | Clean dependency analysis output (`review/deps/`) |
| `docs` | Clean documentation analysis output (`review/docs/`) |
| `perf` | Clean performance analysis output (`review/perf/`) |
| `cache` | Clean cache analysis output (`review/cache/`) |
| `report` | Clean consolidated report output (`review/report/`) |
| `profile` | Clean only the profile data file (`review/perf/test_profile.prof`) |

**Examples:**
```bash
# Clean all review data
python -m glintefy review clean

# Clean only profile data
python -m glintefy review clean -s profile

# Clean only cache analysis
python -m glintefy review clean -s cache

# Preview deletion (dry run)
python -m glintefy review clean --dry-run

# Preview cleaning specific subserver
python -m glintefy review clean -s quality --dry-run
```

---

## Output Structure

All commands write to `LLM-CONTEXT/glintefy/review/`:

```
LLM-CONTEXT/glintefy/review/
├── scope/
│   ├── files_to_review.txt    # List of files
│   └── scope_summary.md       # Summary
├── quality/
│   ├── quality_summary.md     # Summary
│   ├── complexity.json        # Complexity data
│   └── issues.json            # Quality issues
├── security/
│   ├── security_summary.md    # Summary
│   └── bandit_report.json     # Bandit output
├── deps/
│   └── deps_summary.md        # Dependency analysis
├── docs/
│   └── docs_summary.md        # Documentation coverage
├── perf/
│   ├── perf_summary.md        # Performance summary
│   └── test_profile.prof      # Profile data
├── cache/
│   ├── cache_summary.md       # Cache recommendations
│   └── candidates.json        # Cache candidates
└── report/
    ├── code_review_report.md  # Final report
    ├── verdict.json           # Pass/fail verdict
    └── metrics.json           # All metrics
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Analysis found issues or error occurred |

---

## Environment Variables

Environment variables use the format: `GLINTEFY___<SECTION>__<KEY>=<VALUE>`

- Triple underscore (`___`) separates the prefix from the section
- Double underscore (`__`) separates section from key
- Nested sections use double underscore (e.g., `GENERAL__TIMEOUTS__GIT_STATUS`)

| Variable | Default | Permitted Values | Description |
|----------|---------|------------------|-------------|
| `GLINTEFY___GENERAL__LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | Log verbosity level |
| `GLINTEFY___GENERAL__VERBOSE` | `false` | `true`, `false` | Enable verbose output |
| `GLINTEFY___GENERAL__MAX_WORKERS` | `4` | Any positive integer | Maximum parallel workers |
| `GLINTEFY___REVIEW__OUTPUT_DIR` | `LLM-CONTEXT/glintefy/review` | Any valid directory path | Override review output directory |
| `GLINTEFY___REVIEW__QUALITY__COMPLEXITY_THRESHOLD` | `10` | Any positive integer | Default complexity threshold |
| `GLINTEFY___REVIEW__SECURITY__SEVERITY_THRESHOLD` | `low` | `low`, `medium`, `high` | Default security severity |

**Examples:**
```bash
# Set log level to DEBUG
export GLINTEFY___GENERAL__LOG_LEVEL=DEBUG

# Set custom complexity threshold
export GLINTEFY___REVIEW__QUALITY__COMPLEXITY_THRESHOLD=15

# Set security severity threshold
export GLINTEFY___REVIEW__SECURITY__SEVERITY_THRESHOLD=high
```

---

## Configuration

See [Configuration Reference](../reference/CONFIGURATION.md) for customizing thresholds.

## Next Steps

- [CLI Quickstart](QUICKSTART.md) - Basic usage examples
- [Configuration](../reference/CONFIGURATION.md) - Customize analysis
- [Cache Profiling](../CACHE_SUBSERVER.md) - Cache optimization guide
