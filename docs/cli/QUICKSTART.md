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

### Review Git Changes (Default)

```bash
# Go to your project
cd /path/to/your/project

# Review uncommitted changes
python -m btx_fix_mcp review all
```

Output is saved to `LLM-CONTEXT/btx_fix_mcp/review/`.

### Review Entire Repository

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

| Command | Description |
|---------|-------------|
| `review all` | Run all analyses |
| `review all --mode full` | Analyze entire repo |
| `review all --mode git` | Analyze git changes only |
| `review scope` | Discover files to review |
| `review quality` | Code quality analysis |
| `review security` | Security vulnerability scan |
| `review deps` | Dependency analysis |
| `review docs` | Documentation coverage |
| `review perf` | Performance analysis |
| `review cache` | Cache optimization |
| `review profile -- CMD` | Profile a command |
| `review clean` | Clean analysis data |

## Next Steps

- [CLI Reference](REFERENCE.md) - All commands and options
- [Configuration](../reference/CONFIGURATION.md) - Customize thresholds
- [Cache Profiling](../CACHE_SUBSERVER.md) - LRU cache optimization guide
