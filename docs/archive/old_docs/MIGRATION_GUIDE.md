# Migration Guide: Bash Commands → MCP Servers

## Overview

This guide explains how to migrate from the old bash-based Claude command system (`old_commands/`) to the new MCP server architecture.

---

## Key Differences

### Old System (Bash Commands)

```
User → Claude Code → /bx_review_anal! → Bash Script
                         ↓
                   Sub-scripts run
                         ↓
                   Files in LLM-CONTEXT/
```

**Characteristics**:
- Bash scripts embedded in .md files
- Invoked via slash commands in Claude Code
- Direct script execution
- No standardized interface
- Hard to test and version

### New System (MCP Servers)

```
User → Claude Code → MCP Tool Call → Python Server
                         ↓
                   Sub-servers run (parallel)
                         ↓
                   Files in LLM-CONTEXT/
                         ↓
                   MCP Response (structured)
```

**Characteristics**:
- Python-based MCP servers
- Invoked via MCP protocol (standardized)
- Structured tool/resource interface
- Easy to test and version
- Supports multiple MCP clients

---

## Mapping: Old Commands → New MCP Tools

### Review Commands

| Old Command | New MCP Tool | Server |
|-------------|-------------|--------|
| `/bx_review_anal!` | `review_codebase` | glintefy-review |
| Manual: "review changes in last 8 hours" | `review_changes` with `scope: "8h"` | glintefy-review |
| Manual: "review src/auth.py" | `review_files` with `files: ["src/auth.py"]` | glintefy-review |

### Fix Commands

| Old Command | New MCP Tool | Server |
|-------------|-------------|--------|
| `/bx_fix_anal!` | `fix_issues` with `scope: "all"` | glintefy |
| Manual: "fix only critical issues" | `fix_critical` | glintefy |
| Manual: "fix quality issues" | `fix_quality` | glintefy |
| Manual: "fix documentation" | `fix_docs` | glintefy |

### Sub-Agent Commands

Sub-agents are now invoked automatically by orchestrators, not manually by users.

| Old Command | New Sub-server | Orchestrator |
|-------------|----------------|--------------|
| `/bx_review_anal_sub_scope` | `scope` | glintefy-review |
| `/bx_review_anal_sub_deps` | `deps` | glintefy-review |
| `/bx_review_anal_sub_quality` | `quality` | glintefy-review |
| `/bx_review_anal_sub_security` | `security` | glintefy-review |
| `/bx_fix_anal_sub_plan` | `plan` | glintefy |
| `/bx_fix_anal_sub_critical` | `critical` | glintefy |

---

## Usage Examples

### Example 1: Full Codebase Review

#### Old Way (Bash)
```
User: /bx_review_anal!

Claude: [Runs bash script]
- Determines scope
- Runs multiple bash sub-scripts sequentially
- Generates report in LLM-CONTEXT/
- Returns text summary
```

#### New Way (MCP)
```python
# Claude Code calls MCP tool
tool: "review_codebase"
arguments: {
    "priority": "all",
    "parallel": true
}

# Server response (structured)
{
    "status": "success",
    "data": {
        "files_reviewed": 347,
        "findings": {
            "critical": 2,
            "high": 8,
            "medium": 23,
            "low": 45
        },
        "approval_status": "APPROVED_WITH_COMMENTS",
        "report": "review://report"  # MCP resource
    }
}

# User can access report via MCP resource
resource: "review://report"
```

**Benefits**:
- ✅ Structured response (JSON)
- ✅ Parallel execution
- ✅ MCP resources for artifacts
- ✅ Type-safe parameters

### Example 2: Fix Critical Issues

#### Old Way (Bash)
```
User: /bx_fix_anal_sub_critical

Claude: [Runs bash script]
- Reads issues from LLM-CONTEXT/
- Attempts fixes
- Runs tests
- Commits or reverts
- Returns text summary
```

#### New Way (MCP)
```python
# Claude Code calls MCP tool
tool: "fix_critical"
arguments: {
    "verify": true,         # Run 3x test verification
    "auto_commit": true     # Auto-commit successes
}

# Server response (structured)
{
    "status": "success",
    "data": {
        "issues_fixed": 7,
        "issues_reverted": 3,
        "git_commits": 7,
        "tests_passing": true,
        "evidence": "fix://evidence/after",
        "report": "fix://report"
    }
}

# Access evidence files via MCP resources
resource: "fix://evidence/after"
```

**Benefits**:
- ✅ Evidence-based verification
- ✅ Automatic git operations
- ✅ Detailed metrics
- ✅ Access to all artifacts

---

## File Structure Compatibility

The MCP servers maintain the same file structure as the bash system:

```
LLM-CONTEXT/
├── review-anal/          # Same as before
│   ├── scope/
│   ├── quality/
│   ├── security/
│   └── ...
└── fix-anal/             # Same as before
    ├── plan/
    ├── critical/
    └── ...
```

**Why?** This ensures:
1. Backward compatibility
2. Familiar structure for debugging
3. Easy migration path
4. Can run bash and MCP side-by-side during transition

---

## Migration Strategy

### Phase 1: Parallel Operation (Weeks 1-4)

Run both systems side-by-side:

```
/bx_review_anal!          → Bash script (old)
review_codebase tool      → MCP server (new)
```

**Compare results** to ensure parity.

### Phase 2: Gradual Transition (Weeks 5-8)

Migrate high-priority workflows first:

1. **Week 5**: Use MCP for critical fixes only
2. **Week 6**: Use MCP for security reviews
3. **Week 7**: Use MCP for quality analysis
4. **Week 8**: Use MCP for all reviews

Keep bash commands as backup.

### Phase 3: Full Migration (Weeks 9-10)

1. Archive bash commands to `old_commands/`
2. Update documentation
3. Remove slash commands from Claude Code config
4. MCP servers become primary

### Phase 4: Cleanup (Week 11+)

1. Remove bash scripts (keep one archived copy)
2. Remove old documentation
3. Celebrate! 🎉

---

## Side-by-Side Comparison

### Review Workflow

#### Bash Version
```bash
# File: old_commands/bx_review_anal!.md
#!/bin/bash
set -e

# Step 1: Initialize
mkdir -p LLM-CONTEXT/review-anal
echo "IN_PROGRESS" > status.txt

# Step 2: Run scope analysis
bash bx_review_anal_sub_scope.md

# Step 3: Run quality analysis
bash bx_review_anal_sub_quality.md

# Step 4: Run security analysis
bash bx_review_anal_sub_security.md

# Step 5: Generate report
bash bx_review_anal_sub_report.md

echo "SUCCESS" > status.txt
```

**Issues**:
- ❌ Sequential execution (slow)
- ❌ No type safety
- ❌ Hard to test
- ❌ Error handling complex
- ❌ No structured output

#### MCP Version
```python
# File: src/glintefy/servers/review.py
@self.server.call_tool()
async def review_codebase(priority: str, parallel: bool):
    """Review entire codebase."""

    # Step 1: Initialize
    workspace = Path("LLM-CONTEXT/review-anal")
    workspace.mkdir(parents=True, exist_ok=True)

    # Step 2-4: Run sub-servers (parallel if requested)
    if parallel:
        results = await asyncio.gather(
            run_subserver("scope", workspace),
            run_subserver("quality", workspace),
            run_subserver("security", workspace)
        )
    else:
        results = [
            await run_subserver("scope", workspace),
            await run_subserver("quality", workspace),
            await run_subserver("security", workspace)
        ]

    # Step 5: Generate report
    report = await run_subserver("report", workspace)

    # Return structured response
    return {
        "status": "success",
        "data": compile_results(results, report)
    }
```

**Benefits**:
- ✅ Parallel execution option
- ✅ Type-safe parameters
- ✅ Easy to test (async functions)
- ✅ Clean error handling
- ✅ Structured output (JSON)

---

## Porting Guide: Bash → Python

### Example: Port a Sub-Server

#### Original Bash (scope sub-server)

```bash
# File: old_commands/bx_review_anal_sub_scope.md

#!/bin/bash
set -e

# Check git status
git rev-parse --is-inside-work-tree && echo "Git: YES" || echo "Git: NO"

# Generate file list
if git rev-parse --is-inside-work-tree 2>/dev/null; then
    git ls-files | grep -v '\.lock$' > files_to_review.txt
else
    find . -type f -not -path '*/node_modules/*' > files_to_review.txt
fi

# Count files
file_count=$(wc -l < files_to_review.txt)
echo "Files to review: $file_count"

# Save summary
cat > scope/scope_summary.txt << EOF
=== REVIEW SCOPE ===
Files: $file_count
EOF

echo "SUCCESS" > scope/status.txt
```

#### Ported Python (scope sub-server)

```python
# File: src/glintefy/subservers/review/scope.py

from pathlib import Path
from ..base import BaseSubServer, SubServerResult
import subprocess


class ScopeSubServer(BaseSubServer):
    """Determine review scope."""

    def validate_inputs(self) -> tuple[bool, list[str]]:
        """No required inputs for scope analysis."""
        return True, []

    def execute(self) -> SubServerResult:
        """Execute scope analysis."""

        # Check git status
        is_git_repo = self._is_git_repo()
        status_msg = "Git: YES" if is_git_repo else "Git: NO"
        print(status_msg)

        # Generate file list
        if is_git_repo:
            files = self._get_git_files()
        else:
            files = self._get_all_files()

        # Save file list
        files_file = self.output_dir / "files_to_review.txt"
        files_file.write_text("\n".join(str(f) for f in files))

        # Generate summary
        summary = f"""# Scope Analysis

**Files to review:** {len(files)}
**Repository:** {'Git' if is_git_repo else 'Non-git directory'}

## Files
```
{chr(10).join(str(f) for f in files[:20])}
{'...' if len(files) > 20 else ''}
```
"""

        return SubServerResult(
            status="SUCCESS",
            summary=summary,
            artifacts={
                "files_to_review": files_file,
                "scope_summary": self.output_dir / "scope_summary.md"
            },
            metrics={"file_count": len(files)}
        )

    def _is_git_repo(self) -> bool:
        """Check if in git repository."""
        try:
            subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                check=True,
                capture_output=True
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def _get_git_files(self) -> list[Path]:
        """Get tracked git files."""
        result = subprocess.run(
            ["git", "ls-files"],
            capture_output=True,
            text=True
        )
        files = [Path(f) for f in result.stdout.strip().split('\n') if f]
        # Filter out .lock files
        return [f for f in files if not f.name.endswith('.lock')]

    def _get_all_files(self) -> list[Path]:
        """Get all files (non-git)."""
        from ..common.files import find_files
        return find_files(
            root=Path.cwd(),
            pattern="*",
            exclude_patterns=[
                "*/node_modules/*",
                "*/.venv/*",
                "*/__pycache__/*"
            ]
        )
```

**Improvements**:
1. ✅ Type hints for all functions
2. ✅ Structured result (SubServerResult)
3. ✅ Error handling (try/except)
4. ✅ Testable (no global state)
5. ✅ Documented (docstrings)
6. ✅ Reusable utilities

---

## Testing Strategy

### Old System (Bash)
- Manual testing only
- Run script and check output
- No automated tests
- Hard to debug failures

### New System (MCP)
- Comprehensive unit tests
- Integration tests
- Mocked external dependencies
- 90%+ code coverage target

**Example Test**:

```python
# File: tests/subservers/review/test_scope.py

import pytest
from pathlib import Path
from glintefy.subservers.review.scope import ScopeSubServer


def test_scope_non_git_repo(tmp_path):
    """Test scope analysis in non-git directory."""

    # Create test files
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')")
    (tmp_path / "README.md").write_text("# Test")

    # Run scope analysis
    output_dir = tmp_path / "output"
    scope = ScopeSubServer("scope", tmp_path, output_dir)
    result = scope.run()

    # Assertions
    assert result.status == "SUCCESS"
    assert result.metrics["file_count"] == 2
    assert (output_dir / "files_to_review.txt").exists()


@pytest.mark.asyncio
async def test_review_orchestrator(tmp_path, mock_subservers):
    """Test full review workflow."""

    # Mock sub-servers
    mock_subservers.scope.return_value = SubServerResult(...)
    mock_subservers.quality.return_value = SubServerResult(...)

    # Run review
    orchestrator = ReviewOrchestrator(workspace=tmp_path)
    result = await orchestrator.review_codebase(priority="all")

    # Assertions
    assert result["status"] == "success"
    assert "findings" in result["data"]
```

---

## Rollback Plan

If issues occur during migration, you can easily rollback:

### Option 1: Keep Both Systems
```json
{
  "mcpServers": {
    "glintefy-review": { /* MCP server */ },
    "glintefy": { /* MCP server */ }
  },
  "commands": {
    "/bx_review_anal!": { /* Bash command */ },
    "/bx_fix_anal!": { /* Bash command */ }
  }
}
```

Use MCP for new work, bash for critical operations.

### Option 2: Disable MCP Servers
```json
{
  "mcpServers": {
    // "glintefy-review": { /* Disabled */ },
    // "glintefy": { /* Disabled */ }
  }
}
```

Revert to bash commands only.

### Option 3: Version Pinning
```toml
# Pin to working version
dependencies = [
    "glintefy==1.0.0",  # Known good version
]
```

---

## FAQ

### Q: Can I use both systems simultaneously?
**A**: Yes! They use the same file structure and don't conflict.

### Q: Do I need to rewrite all bash scripts immediately?
**A**: No. Migrate incrementally, starting with high-value workflows.

### Q: What if the MCP server has a bug?
**A**: Keep bash commands as backup. Report bug, use bash temporarily.

### Q: How do I debug MCP server issues?
**A**:
1. Check MCP server logs
2. Inspect files in LLM-CONTEXT/
3. Run sub-servers directly for testing
4. Use Python debugger (pdb, VS Code debugger)

### Q: Is performance better or worse?
**A**: Better! Parallel execution makes reviews ~3-5x faster.

### Q: Can I contribute new sub-servers?
**A**: Yes! Follow the guide in `docs/GETTING_STARTED.md`

---

## Support During Migration

### Resources
- Architecture: `docs/MCP_ARCHITECTURE.md`
- Implementation Plan: `docs/IMPLEMENTATION_PLAN.md`
- Getting Started: `docs/GETTING_STARTED.md`
- Code Examples: `examples/`

### Getting Help
- GitHub Issues: Report bugs
- GitHub Discussions: Ask questions
- Code Review: Submit PRs for review

---

## Success Checklist

- [ ] Read all migration documentation
- [ ] Understand MCP tool/resource concepts
- [ ] Test MCP servers in dev environment
- [ ] Run both systems in parallel
- [ ] Compare outputs for parity
- [ ] Migrate high-priority workflows
- [ ] Train team on new system
- [ ] Archive bash commands
- [ ] Update documentation
- [ ] Celebrate successful migration! 🎉

---

**Next Steps**: Start with Phase 1 - install and test MCP servers alongside bash commands.
