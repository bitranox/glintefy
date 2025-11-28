# CLI Quickstart

Get started with btx_fix_mcp command-line interface in 5 minutes.

## Installation

```bash
# Quick install
pip install btx_fix_mcp

# Or with uv (faster)
uv pip install btx_fix_mcp
```

## Basic Usage

### Review Uncommitted Git Changes (Default)

```bash
# Go to your project
cd /path/to/your/project

# Review uncommitted changes
python -m btx_fix_mcp review all
```

Output is saved to `LLM-CONTEXT/btx_fix_mcp/review/`.

> **Note**: If your project is not a git repository, `--mode git` automatically falls back to `--mode full` with a warning.

### Review All Files

```bash
python -m btx_fix_mcp review all --mode full
```

### Run Specific Analyses

```bash
# Quality analysis only
python -m btx_fix_mcp review quality

# Security scan only
python -m btx_fix_mcp review security

# Cache optimization analysis
python -m btx_fix_mcp review cache
```

## Output Location

All results are saved to:

```
your-project/
└── LLM-CONTEXT/
    └── btx_fix_mcp/
        └── review/
            ├── scope/          # Files analyzed
            ├── quality/        # Quality metrics
            ├── security/       # Security issues
            ├── deps/           # Dependency analysis
            ├── docs/           # Documentation coverage
            ├── perf/           # Performance analysis
            ├── cache/          # Cache recommendations
            └── report/         # Final summary
```

## Common Workflows

### CI/CD Integration

```bash
# In your CI pipeline
python -m btx_fix_mcp review all --mode full

# Check exit code for failures
if [ $? -ne 0 ]; then
    echo "Code review found issues"
    exit 1
fi
```

### Pre-commit Hook

```bash
# Review only staged changes
python -m btx_fix_mcp review all --mode git
```

### Cache Optimization

```bash
# Profile your tests first
python -m btx_fix_mcp review profile -- pytest tests/

# Then analyze cache opportunities
python -m btx_fix_mcp review cache
```

### Clean Up Old Results

```bash
# Delete all review data
python -m btx_fix_mcp review clean

# Delete specific analysis
python -m btx_fix_mcp review clean -s quality
python -m btx_fix_mcp review clean -s profile

# Preview what would be deleted
python -m btx_fix_mcp review clean --dry-run
```

## Quick Reference

| Command | Option | Default | Permitted Values |
|---------|--------|---------|------------------|
| `review all` | `--mode` | `git` | `git`, `full` |
| | `--complexity` | `10` | Any positive integer |
| | `--severity` | `low` | `low`, `medium`, `high` |
| `review scope` | `--mode` | `git` | `git`, `full` |
| `review quality` | `--complexity` | `10` | Any positive integer |
| | `--maintainability` | `20` | Integer 0-100 |
| `review security` | `--severity` | `low` | `low`, `medium`, `high` |
| | `--confidence` | `low` | `low`, `medium`, `high` |
| `review deps` | `--no-vulnerabilities` | disabled | Flag (include to skip) |
| | `--no-licenses` | disabled | Flag (include to skip) |
| | `--no-outdated` | disabled | Flag (include to skip) |
| `review docs` | `--min-coverage` | `80` | Integer 0-100 |
| `review perf` | `--no-profiling` | disabled | Flag (include to skip) |
| `review cache` | `--cache-size` | `128` | Any positive integer |
| | `--hit-rate` | `20.0` | Float 0.0-100.0 |
| | `--speedup` | `5.0` | Float >= 0.0 |
| `review profile` | `COMMAND` | **required** | Any shell command after `--` |
| `review clean` | `--subserver` | `all` | `all`, `scope`, `quality`, `security`, `deps`, `docs`, `perf`, `cache`, `report`, `profile` |
| | `--dry-run` | disabled | Flag (include to preview) |
| `review report` | - | - | No options |

> **All options are optional** unless marked as required. See [CLI Reference](REFERENCE.md) for detailed documentation.

## Next Steps

- [CLI Reference](REFERENCE.md) - All commands and options
- [Configuration](../reference/CONFIGURATION.md) - Customize thresholds
- [Cache Profiling](../CACHE_SUBSERVER.md) - LRU cache optimization guide
