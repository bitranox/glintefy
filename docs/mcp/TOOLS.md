# MCP Tools Reference

Complete reference for btx_fix_mcp MCP server tools.

## Server Overview

The btx-review MCP server provides code analysis tools via the Model Context Protocol.

```json
{
  "mcpServers": {
    "btx-review": {
      "command": "python",
      "args": ["-m", "btx_fix_mcp.servers.review"],
      "cwd": "/path/to/project"
    }
  }
}
```

## Tools

### `review_all`

Run all review analyses.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `mode` | string | `"git"` | `"git"` or `"full"` |

**Example:**
```
Use review_all with mode="full" to analyze the entire repository
```

**Returns:**
- Summary of all analyses
- Verdict (pass/fail)
- Metrics from each subserver

---

### `review_scope`

Discover files to analyze.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `mode` | string | `"git"` | `"git"` = changes only, `"full"` = all files |

**Returns:**
- List of files to review
- File count by type

---

### `review_quality`

Run code quality analysis.

**Parameters:** None

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

Run security vulnerability scan.

**Parameters:** None

**Returns:**
- High severity issues
- Medium severity issues
- Low severity issues
- Issue details (file, line, description)

---

### `review_deps`

Analyze dependencies.

**Parameters:** None

**Returns:**
- Vulnerability scan results
- Outdated packages
- License compliance

---

### `review_docs`

Analyze documentation coverage.

**Parameters:** None

**Returns:**
- Docstring coverage percentage
- Missing docstrings (files, functions, classes)
- Documentation quality issues

---

### `review_perf`

Run performance analysis.

**Parameters:** None

**Returns:**
- Function hotspots
- Performance anti-patterns
- Algorithm complexity issues

---

### `review_cache`

Analyze cache optimization opportunities.

**Parameters:** None

**Requires:** Profile data (optional but recommended)

**Returns:**
- Pure function candidates
- Existing cache analysis
- Cache recommendations with expected hit rate
- Performance impact estimates

---

## Resources

The server exposes these MCP resources:

### `review://status`

Current status of the review server.

### `review://config`

Current configuration values.

### `review://results/{subserver}`

Results from a specific subserver (scope, quality, security, etc.).

## Configuration via MCP

Configuration can be passed to tools:

```
Use review_quality with complexity_threshold=15
```

Or set via environment:
```bash
export BTX_FIX_MCP_REVIEW_QUALITY_COMPLEXITY_THRESHOLD=15
```

## Output Location

Results are saved to:
```
{cwd}/LLM-CONTEXT/btx_fix_mcp/review/
```

## Error Handling

Tools return structured errors:

```json
{
  "status": "FAILED",
  "errors": ["Error message"],
  "summary": "Analysis failed: reason"
}
```

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

## Next Steps

- [MCP Quickstart](QUICKSTART.md) - Initial setup
- [Configuration](../reference/CONFIGURATION.md) - Customize thresholds
- [Architecture](../architecture/OVERVIEW.md) - System design
