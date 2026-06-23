# MCP Tools Reference

Complete reference for glintefy MCP server tools.

## Server Overview

The glintefy-review MCP server provides code analysis tools via the Model Context Protocol.

```json
{
  "mcpServers": {
    "glintefy-review": {
      "command": "python",
      "args": ["-m", "glintefy.servers.review"],
      "cwd": "/path/to/project"
    }
  }
}
```

## Tools

### `review_all`

Run all review analyses (scope + quality + security + deps + docs + perf + report).

**Parameters:**

| Name | Type | Required | Default | Permitted Values | Description |
|------|------|----------|---------|------------------|-------------|
| `mode` | string | No | `"git"` | `"git"`, `"full"` | Scope mode for file discovery |
| `complexity_threshold` | integer | No | `10` | Any positive integer | Maximum cyclomatic complexity |
| `severity_threshold` | string | No | `"low"` | `"low"`, `"medium"`, `"high"` | Minimum security severity |

**Mode values:**
- `"git"` - Review only uncommitted changes (falls back to `"full"` if not a git repository)
- `"full"` - Review all files in the repository

**Example:**
```
Use review_all with mode="full" to analyze the entire repository
Use review_all with mode="git", severity_threshold="high" to review changes with only critical security issues
```

**Returns:**
- Summary of all analyses
- Verdict (pass/fail)
- Metrics from each subserver

---

### `review_scope`

Discover files to analyze.

**Parameters:**

| Name | Type | Required | Default | Permitted Values | Description |
|------|------|----------|---------|------------------|-------------|
| `mode` | string | No | `"git"` | `"git"`, `"full"` | Scope mode for file discovery |

**Mode values:**
- `"git"` - Scan only uncommitted changes (falls back to `"full"` if not a git repository)
- `"full"` - Scan all files in the repository

**Returns:**
- List of files to review
- File count by type (CODE, TEST, DOCS, CONFIG, BUILD, OTHER)

---

### `review_quality`

Run code quality analysis.

**Parameters:**

| Name | Type | Required | Default | Permitted Values | Description |
|------|------|----------|---------|------------------|-------------|
| `complexity_threshold` | integer | No | `10` | Any positive integer | Maximum cyclomatic complexity before flagging |
| `maintainability_threshold` | integer | No | `20` | Integer 0-100 | Minimum maintainability index |

**Threshold guidelines:**
- **Complexity**: Lower is better. Values >10 indicate complex functions that should be refactored.
- **Maintainability**: Higher is better. Values <20 indicate hard-to-maintain code.

**Returns:**
- Complexity metrics (cyclomatic, cognitive)
- Function length violations
- Nesting depth violations
- Maintainability index
- Code duplication
- Dead code
- Type coverage
- Import cycles
- God objects

---

### `review_security`

Run security vulnerability scan using Bandit.

**Parameters:**

| Name | Type | Required | Default | Permitted Values | Description |
|------|------|----------|---------|------------------|-------------|
| `severity_threshold` | string | No | `"low"` | `"low"`, `"medium"`, `"high"` | Minimum severity to report |
| `confidence_threshold` | string | No | `"low"` | `"low"`, `"medium"`, `"high"` | Minimum confidence to report |
| `critical_threshold` | integer | No | `1` | Any positive integer | High severity issues to trigger PARTIAL status |
| `warning_threshold` | integer | No | `5` | Any positive integer | Medium severity issues to trigger PARTIAL status |

**Severity levels:**
- `"low"` - Report all issues including minor ones
- `"medium"` - Report medium and high severity issues only
- `"high"` - Report only high severity (critical) issues

**Confidence levels:**
- `"low"` - Report all findings including uncertain ones
- `"medium"` - Report medium and high confidence findings only
- `"high"` - Report only high confidence (definite) findings

**Returns:**
- High severity issues
- Medium severity issues
- Low severity issues
- Issue details (file, line, description)

---

### `review_deps`

Analyze dependencies for vulnerabilities and compliance.

**Parameters:**

| Name | Type | Required | Default | Permitted Values | Description |
|------|------|----------|---------|------------------|-------------|
| `scan_vulnerabilities` | boolean | No | `true` | `true`, `false` | Enable vulnerability scanning |
| `check_licenses` | boolean | No | `true` | `true`, `false` | Enable license compliance checking |
| `check_outdated` | boolean | No | `true` | `true`, `false` | Enable outdated package detection |

**Returns:**
- Vulnerability scan results (CVEs)
- Outdated packages
- License compliance issues

---

### `review_docs`

Analyze documentation coverage and quality.

**Parameters:**

| Name | Type | Required | Default | Permitted Values | Description |
|------|------|----------|---------|------------------|-------------|
| `min_coverage` | integer | No | `80` | Integer 0-100 | Minimum docstring coverage percentage |
| `docstring_style` | string | No | `"google"` | `"google"`, `"numpy"`, `"sphinx"` | Expected docstring style format |

**Docstring styles:**
- `"google"` - Google-style docstrings (Args:, Returns:, Raises:)
- `"numpy"` - NumPy-style docstrings (Parameters, Returns, Raises sections)
- `"sphinx"` - Sphinx-style docstrings (:param, :returns:, :raises:)

**Returns:**
- Docstring coverage percentage
- Missing docstrings (files, functions, classes)
- Documentation quality issues

---

### `review_perf`

Run performance analysis.

**Parameters:**

| Name | Type | Required | Default | Permitted Values | Description |
|------|------|----------|---------|------------------|-------------|
| `run_profiling` | boolean | No | `true` | `true`, `false` | Whether to analyze existing profile data |
| `nested_loop_threshold` | integer | No | `2` | Any positive integer | Nesting depth to trigger warning |

**Nested loop threshold values:**
- `2` - Flag O(n^2) complexity (nested loops)
- `3` - Flag O(n^3) complexity (triple-nested loops)

**Returns:**
- Function hotspots
- Performance anti-patterns
- Algorithm complexity issues

---

### `review_cache`

Analyze cache optimization opportunities using hybrid evidence-based approach.

**Prerequisite:** For best results, run profiling first using CLI: `python -m glintefy review profile -- pytest tests/`

**Parameters:**

| Name | Type | Required | Default | Permitted Values | Description |
|------|------|----------|---------|------------------|-------------|
| `cache_size` | integer | No | `128` | Any positive integer | LRU cache maxsize for testing |
| `hit_rate_threshold` | number | No | `20.0` | Float 0.0-100.0 | Minimum cache hit rate % for recommendations |
| `speedup_threshold` | number | No | `5.0` | Float >= 0.0 | Minimum speedup % for recommendations |

**Parameter guidelines:**
- **cache_size**: Common values are powers of 2 (64, 128, 256, 512). Larger values use more memory.
- **hit_rate_threshold**: Functions with hit rates below this are not recommended for caching.
- **speedup_threshold**: Functions with speedup below this are not recommended for caching.

**Returns:**
- Pure function candidates
- Existing cache analysis
- Cache recommendations with expected hit rate
- Performance impact estimates

---

### `review_report`

Generate consolidated report from all analysis results.

**Parameters:** None

**Prerequisite:** Requires previous analysis runs (scope, quality, security, etc.) to have been executed.

**Returns:**
- Consolidated summary
- Overall verdict (PASS/PARTIAL/FAIL)
- Combined metrics

---

## Resources

The server exposes these MCP resources:

### `review://status`

Current status of the review server.

### `review://config`

Current configuration values.

### `review://results/{subserver}`

Results from a specific subserver.

| Subserver | Description |
|-----------|-------------|
| `scope` | File discovery results |
| `quality` | Code quality analysis |
| `security` | Security scan results |
| `deps` | Dependency analysis |
| `docs` | Documentation coverage |
| `perf` | Performance analysis |
| `cache` | Cache recommendations |
| `report` | Consolidated report |

---

## Configuration via MCP

Configuration can be passed to tools:

```
Use review_quality with complexity_threshold=15
Use review_security with severity_threshold="high", confidence_threshold="medium"
Use review_cache with cache_size=256, hit_rate_threshold=30.0
```

Or set via environment (format: `GLINTEFY___<SECTION>__<KEY>=<VALUE>`):
```bash
# Triple underscore after prefix, double underscore between sections
export GLINTEFY___REVIEW__QUALITY__COMPLEXITY_THRESHOLD=15
export GLINTEFY___REVIEW__SECURITY__SEVERITY_THRESHOLD=high
export GLINTEFY___GENERAL__LOG_LEVEL=DEBUG
```

---

## Output Location

Results are saved to:
```
{cwd}/LLM-CONTEXT/glintefy/review/
├── scope/       # File discovery
├── quality/     # Quality metrics
├── security/    # Security issues
├── deps/        # Dependencies
├── docs/        # Documentation
├── perf/        # Performance
├── cache/       # Cache analysis
└── report/      # Final report
```

---

## Error Handling

Tools return structured errors:

```json
{
  "status": "FAILED",
  "errors": ["Error message"],
  "summary": "Analysis failed: reason"
}
```

---

## Integration with Claude

### Asking for Analysis

```
"Review the code quality"
→ Claude uses review_quality

"Check for security issues"
→ Claude uses review_security

"Find caching opportunities"
→ Claude uses review_cache

"Full code review"
→ Claude uses review_all
```

### Following Up

```
"Show me the high complexity functions"
→ Claude reads review://results/quality

"Fix the security issues"
→ Claude uses results to suggest fixes
```

---

## Next Steps

- [MCP Quickstart](QUICKSTART.md) - Initial setup
- [Configuration](../reference/CONFIGURATION.md) - Customize thresholds
- [Architecture](../architecture/OVERVIEW.md) - System design
