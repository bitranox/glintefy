# CLI Reference

Complete reference for all btx_fix_mcp CLI commands.

## Global Options

```bash
python -m btx_fix_mcp [OPTIONS] COMMAND
```

| Option | Description |
|--------|-------------|
| `--help` | Show help message |
| `--version` | Show version |

## Review Commands

### `review all`

Run all review analyses.

```bash
python -m btx_fix_mcp review [--repo PATH] all [--mode MODE]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--repo PATH` | `.` | Repository path |
| `--mode MODE` | `git` | Scope mode: `git` (changes only) or `full` (entire repo) |

**Example:**
```bash
# Review git changes in current directory
python -m btx_fix_mcp review all

# Review entire repo at specific path
python -m btx_fix_mcp review --repo /path/to/project all --mode full
```

### `review scope`

Discover files to analyze.

```bash
python -m btx_fix_mcp review scope [--mode MODE]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--mode MODE` | `git` | `git` = uncommitted changes, `full` = all files |

### `review quality`

Run code quality analysis.

```bash
python -m btx_fix_mcp review quality
```

Analyzes:
- Cyclomatic complexity (threshold: ≤10)
- Function length (threshold: ≤50 lines)
- Nesting depth (threshold: ≤3 levels)
- Maintainability index (threshold: ≥20)
- Code duplication
- Dead code
- Type coverage
- Import cycles
- God objects

### `review security`

Run security vulnerability scan.

```bash
python -m btx_fix_mcp review security
```

Uses Bandit to detect:
- Hardcoded passwords
- SQL injection
- Command injection
- Weak cryptography
- Other OWASP vulnerabilities

### `review deps`

Analyze dependencies.

```bash
python -m btx_fix_mcp review deps
```

Checks:
- Known vulnerabilities (CVEs)
- Outdated packages
- License compliance

### `review docs`

Analyze documentation coverage.

```bash
python -m btx_fix_mcp review docs
```

Checks:
- Docstring coverage (threshold: ≥80%)
- Missing parameter documentation
- Missing return documentation

### `review perf`

Run performance analysis.

```bash
python -m btx_fix_mcp review perf
```

Analyzes:
- Function hotspots
- Performance anti-patterns
- Algorithm complexity

### `review cache`

Analyze cache optimization opportunities.

```bash
python -m btx_fix_mcp review cache
```

Identifies:
- Pure functions suitable for caching
- Existing cache effectiveness
- Recommended `@lru_cache` decorators

### `review profile`

Profile a command for cache analysis.

```bash
python -m btx_fix_mcp review profile -- COMMAND
```

**Examples:**
```bash
# Profile test suite
python -m btx_fix_mcp review profile -- pytest tests/

# Profile a script
python -m btx_fix_mcp review profile -- python my_script.py

# Profile a module
python -m btx_fix_mcp review profile -- python -m my_module
```

### `review clean`

Clean analysis output files.

```bash
python -m btx_fix_mcp review clean [--subserver NAME] [--dry-run]
```

| Option | Default | Description |
|--------|---------|-------------|
| `-s, --subserver NAME` | `all` | Clean specific subserver or `all` |
| `--dry-run` | false | Show what would be deleted |

**Subserver options:** `all`, `scope`, `quality`, `security`, `deps`, `docs`, `perf`, `cache`, `report`, `profile`

**Examples:**
```bash
# Clean all review data
python -m btx_fix_mcp review clean

# Clean only profile data
python -m btx_fix_mcp review clean -s profile

# Preview deletion
python -m btx_fix_mcp review clean --dry-run
```

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

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Analysis found issues or error occurred |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `BTX_FIX_MCP_LOG_LEVEL` | Log level: DEBUG, INFO, WARNING, ERROR |
| `BTX_FIX_MCP_OUTPUT_DIR` | Override output directory |

## Configuration

See [Configuration Reference](../reference/CONFIGURATION.md) for customizing thresholds.

## Next Steps

- [CLI Quickstart](QUICKSTART.md) - Basic usage examples
- [Configuration](../reference/CONFIGURATION.md) - Customize analysis
- [Cache Profiling](../CACHE_SUBSERVER.md) - Cache optimization guide
