# Architecture Summary: glintefy and glintefy-review MCP Servers

## Quick Overview

Transform the existing bash-based Claude command system into two MCP servers with specialized sub-servers.

## Server Structure

### **glintefy-review** (Orchestrator)
Coordinates comprehensive code review through specialized sub-servers.

**Tools**:
- `review_codebase` - Full codebase review
- `review_changes` - Review specific changes (uncommitted, time-based, etc.)
- `review_files` - Review specific files/patterns

**Sub-servers** (11):
1. `scope` - Determine what to review
2. `deps` - Update dependencies
3. `quality` - Code quality analysis (complexity, duplication, style)
4. `security` - Security vulnerabilities (SQL injection, XSS, etc.)
5. `performance` - Performance analysis and profiling
6. `cache` - Identify caching opportunities
7. `docs` - Documentation completeness
8. `cicd` - CI/CD pipeline analysis
9. `refactor-tests` - Test suite quality
10. `report` - Compile final report
11. `log-analyzer` - Analyze logs for errors

### **glintefy** (Orchestrator)
Actually fixes code issues with evidence-based verification.

**Tools**:
- `fix_issues` - Fix all issues from review
- `fix_critical` - Fix only critical issues (security, tests)
- `fix_quality` - Fix quality issues (refactoring)
- `fix_docs` - Fix documentation

**Sub-servers** (9):
1. `plan` - Create actionable fix plan with strategies
2. `critical` - Fix security vulnerabilities and test failures
3. `quality` - Fix code quality issues
4. `refactor-tests` - Refactor test suite
5. `cache` - Apply cache optimizations
6. `docs` - Fix documentation
7. `verify` - Run comprehensive verification (tests 3x)
8. `report` - Generate fix report with evidence
9. `log-analyzer` - Analyze logs for errors

## Evidence-Based Fixing Protocol

The fix system's core principle: **"Don't trust, verify"**

```
FOR EACH FIX:
1. MEASURE BEFORE
   - Run tests 3x (detect flaky tests)
   - Security scan
   - Capture metrics

2. APPLY FIX
   - Modify code using AST/regex
   - Create backup

3. MEASURE AFTER
   - Run tests 3x
   - Re-scan security
   - Compare metrics

4. DECIDE
   ✓ Evidence shows improvement → git commit
   ✗ Evidence shows regression → git revert

5. DOCUMENT
   - Save all evidence files
   - Log decision and reasoning
```

## Key Features

### Evidence-Based
- All fixes verified with tests run 3x
- Before/after metrics comparison
- Complete audit trail
- Automatic revert on failures

### Parallel Execution
- Review sub-servers run in parallel
- Faster analysis for large codebases

### Actionable Plans
- Each issue has specific fix strategy
- Evidence requirements defined
- Success criteria quantified
- Rollback triggers clear

### Safety
- Git commit successful fixes
- Git revert failed fixes
- Backup files before modification
- Flaky test detection (3x runs)

## File Structure

```
LLM-CONTEXT/
├── review-anal/          # Review workspace
│   ├── scope/            # What files to review
│   ├── quality/          # Quality issues found
│   ├── security/         # Security issues found
│   ├── report/           # Final review report
│   └── logs/             # All logs
│
└── fix-anal/             # Fix workspace
    ├── plan/             # Fix plan with strategies
    ├── metrics/          # Baseline metrics (BEFORE)
    ├── critical/         # Critical fixes applied
    ├── quality/          # Quality fixes applied
    ├── verification/     # After-fix verification
    ├── evidence/         # Evidence files
    │   ├── before/       # Evidence before fixes
    │   └── after/        # Evidence after fixes
    └── report/           # Final fix report
```

## Example Workflow

### 1. Review Code
```python
# MCP Client (Claude Code)
result = call_tool("glintefy-review", "review_codebase", {
    "priority": "all",
    "parallel": True
})

# Returns:
{
    "files_reviewed": 347,
    "findings": {
        "critical": 2,    # Security, test failures
        "high": 8,        # Quality issues
        "medium": 23,     # Documentation
        "low": 45         # Style issues
    },
    "approval_status": "APPROVED_WITH_COMMENTS"
}
```

### 2. Fix Issues
```python
# MCP Client (Claude Code)
result = call_tool("glintefy", "fix_critical", {
    "verify": True,        # Run 3x test verification
    "auto_commit": True    # Auto-commit successful fixes
})

# Returns:
{
    "issues_fixed": 7,      # Actually fixed and committed
    "issues_reverted": 3,   # Reverted (tests failed)
    "git_commits": 7,       # Git commits created
    "tests_passing": True,  # All tests pass 3x
    "evidence": "fix://evidence/after"
}
```

## Integration Protocol

Every sub-server MUST:
1. Create `status.txt` → "SUCCESS" or "FAILED"
2. Create `{subagent}_summary.md` → Human-readable results
3. Save artifacts to designated directory
4. Return structured MCP response
5. Exit with proper code (0=success)

## Implementation Phases

1. **Core Infrastructure** (Week 1-2)
   - MCP server framework
   - Base orchestrator/sub-server classes
   - Directory utilities

2. **Review Server** (Week 3-4)
   - glintefy-review orchestrator
   - Core sub-servers (scope, quality, security)
   - Parallel execution

3. **Fix Server** (Week 5-6)
   - glintefy orchestrator
   - Critical fix sub-server (evidence-based)
   - Quality fix sub-server
   - Git commit/revert logic

4. **Remaining Sub-servers** (Week 7-8)
   - Performance, cache, docs, cicd, tests
   - Report generation
   - Log analysis

5. **Testing & Docs** (Week 9-10)
   - Integration tests
   - Documentation
   - Deployment guides

## Tech Stack

- **Python 3.13+** - Main language
- **MCP SDK** - Anthropic's MCP Python SDK
- **Analysis Tools**:
  - `bandit` - Security scanning
  - `radon` - Complexity metrics
  - `pytest` - Testing
  - Python AST - Code parsing/modification
- **Git** - Version control operations

## Benefits vs. Old System

| Feature | Old (Bash) | New (MCP) |
|---------|-----------|-----------|
| Protocol | None | Standardized MCP |
| Language | Bash | Python 3.13+ |
| Versioning | Hard | Easy (pip package) |
| Testing | Manual | Automated |
| Error Handling | Basic | Rich |
| Maintainability | Low | High |
| Extensibility | Hard | Easy |
| Multi-client | No | Yes (any MCP client) |

## Why MCP?

1. **Standard Protocol** - Works with any MCP client
2. **Better UX** - Structured tools and resources
3. **Versioning** - Deploy as pip package
4. **Testing** - Proper test infrastructure
5. **Maintenance** - Python easier than bash
6. **Future-Proof** - Can add new features easily

## Configuration

```json
{
  "mcpServers": {
    "glintefy-review": {
      "command": "python",
      "args": ["-m", "glintefy.servers.review"]
    },
    "glintefy": {
      "command": "python",
      "args": ["-m", "glintefy.servers.fix"]
    }
  }
}
```

## Compatibility

- Same directory structure (`LLM-CONTEXT/`)
- Same file formats and conventions
- Same evidence-based protocol
- Gradual migration from bash to Python

## Success Metrics

- ✅ All review analyses complete successfully
- ✅ Security vulnerabilities actually fixed
- ✅ Tests pass 3/3 runs after fixes
- ✅ Failed fixes automatically reverted
- ✅ Complete evidence trail for audit
- ✅ Git commits for all successful fixes

---

**For full details, see:** `docs/MCP_ARCHITECTURE.md`
