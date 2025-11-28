# CLI Reference

Complete reference for all btx_fix_mcp CLI commands.

## Global Options

```bash
python -m btx_fix_mcp [OPTIONS] COMMAND
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--help` | No | - | Show help message |
| `--version` | No | - | Show version |

---

## Review Commands

All review commands support `--repo PATH` to specify the target repository.

### `review all`

Run all review analyses.

```bash
python -m btx_fix_mcp review [--repo PATH] all [--mode MODE] [--complexity N] [--severity LEVEL]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--repo PATH` | No | `.` (current directory) | Repository path to analyze |
| `--mode, -m MODE` | No | `git` | Scope mode: `git` (uncommitted changes) or `full` (all files) |
| `--complexity N` | No | `10` | Maximum cyclomatic complexity threshold |
| `--severity LEVEL` | No | `low` | Minimum security severity: `low`, `medium`, or `high` |

> **Note**: If `--mode git` is used but the directory is not a git repository, it automatically falls back to `full` mode with a warning.

**Example:**
```bash
# Review uncommitted git changes (default)
python -m btx_fix_mcp review all

# Review all files
python -m btx_fix_mcp review all --mode full

# Review at specific path
python -m btx_fix_mcp review --repo /path/to/project all

# Review with custom thresholds
python -m btx_fix_mcp review all --complexity 15 --severity high
```

---

### `review scope`

Discover files to analyze.

```bash
python -m btx_fix_mcp review scope [--mode MODE]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--mode, -m MODE` | No | `git` | `git` = uncommitted changes, `full` = all files |

> **Note**: If `--mode git` is used but the directory is not a git repository, it automatically falls back to `full` mode with a warning.

---

### `review quality`

Run code quality analysis.

```bash
python -m btx_fix_mcp review quality [--complexity N] [--maintainability N]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--complexity, -c N` | No | `10` | Maximum cyclomatic complexity threshold |
| `--maintainability, -m N` | No | `20` | Minimum maintainability index threshold |

**Analyzes:**
- Cyclomatic complexity (threshold: ≤10)
- Function length (threshold: ≤50 lines)
- Nesting depth (threshold: ≤3 levels)
- Maintainability index (threshold: ≥20)
- Code duplication
- Dead code
- Type coverage
- Import cycles
- God objects

---

### `review security`

Run security vulnerability scan.

```bash
python -m btx_fix_mcp review security [--severity LEVEL] [--confidence LEVEL]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--severity LEVEL` | No | `low` | Minimum severity: `low`, `medium`, `high` |
| `--confidence LEVEL` | No | `low` | Minimum confidence: `low`, `medium`, `high` |

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
python -m btx_fix_mcp review deps [--no-vulnerabilities] [--no-licenses] [--no-outdated]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--no-vulnerabilities` | No | `false` | Skip vulnerability scan |
| `--no-licenses` | No | `false` | Skip license check |
| `--no-outdated` | No | `false` | Skip outdated package check |

**Checks:**
- Known vulnerabilities (CVEs)
- Outdated packages
- License compliance

---

### `review docs`

Analyze documentation coverage.

```bash
python -m btx_fix_mcp review docs [--min-coverage N] [--style STYLE]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--min-coverage N` | No | `80` | Minimum docstring coverage percentage |
| `--style STYLE` | No | `google` | Docstring style: `google`, `numpy`, `sphinx` |

**Checks:**
- Docstring coverage (threshold: ≥80%)
- Missing parameter documentation
- Missing return documentation

---

### `review perf`

Run performance analysis.

```bash
python -m btx_fix_mcp review perf [--no-profiling] [--nested-loop-threshold N]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--no-profiling` | No | `false` | Skip profile data analysis |
| `--nested-loop-threshold N` | No | `2` | Max nested loop depth before flagging |

**Analyzes:**
- Function hotspots
- Performance anti-patterns
- Algorithm complexity

---

### `review cache`

Analyze cache optimization opportunities.

```bash
python -m btx_fix_mcp review cache [--cache-size N] [--hit-rate-threshold N] [--speedup-threshold N]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--cache-size N` | No | `128` | LRU cache maxsize for testing |
| `--hit-rate-threshold N` | No | `20.0` | Minimum cache hit rate % to recommend |
| `--speedup-threshold N` | No | `5.0` | Minimum speedup % to recommend |

**Identifies:**
- Pure functions suitable for caching
- Existing cache effectiveness
- Recommended `@lru_cache` decorators

> **Note**: For best results, run `review profile` first to generate profiling data.

---

### `review profile`

Profile a command for cache analysis.

```bash
python -m btx_fix_mcp review profile -- COMMAND [ARGS...]
```

| Argument | Required | Description |
|----------|----------|-------------|
| `COMMAND` | **Yes** | Command to profile (everything after `--`) |

**Examples:**
```bash
# Profile test suite
python -m btx_fix_mcp review profile -- pytest tests/

# Profile a script
python -m btx_fix_mcp review profile -- python my_script.py

# Profile a module
python -m btx_fix_mcp review profile -- python -m my_module
```

---

### `review report`

Generate consolidated report from existing analysis results.

```bash
python -m btx_fix_mcp review report
```

No options. Requires previous analysis runs (scope, quality, etc.) to have been executed.

---

### `review clean`

Clean analysis output files.

```bash
python -m btx_fix_mcp review clean [--subserver NAME] [--dry-run]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `-s, --subserver NAME` | No | `all` | Subserver to clean: `all`, `scope`, `quality`, `security`, `deps`, `docs`, `perf`, `cache`, `report`, `profile` |
| `--dry-run` | No | `false` | Show what would be deleted without deleting |

**Examples:**
```bash
# Clean all review data
python -m btx_fix_mcp review clean

# Clean only profile data
python -m btx_fix_mcp review clean -s profile

# Preview deletion
python -m btx_fix_mcp review clean --dry-run
```

---

## Output Structure

All commands write to `LLM-CONTEXT/btx_fix_mcp/review/`:

```
LLM-CONTEXT/btx_fix_mcp/review/
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

| Variable | Default | Description |
|----------|---------|-------------|
| `BTX_FIX_MCP_LOG_LEVEL` | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `BTX_FIX_MCP_OUTPUT_DIR` | `LLM-CONTEXT/btx_fix_mcp` | Override output directory |

---

## Configuration

See [Configuration Reference](../reference/CONFIGURATION.md) for customizing thresholds.

## Next Steps

- [CLI Quickstart](QUICKSTART.md) - Basic usage examples
- [Configuration](../reference/CONFIGURATION.md) - Customize analysis
- [Cache Profiling](../CACHE_SUBSERVER.md) - Cache optimization guide
