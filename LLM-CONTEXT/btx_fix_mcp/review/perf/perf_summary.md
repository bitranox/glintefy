# Performance Analysis Report

## Reviewer Mindset

**You are a perf reviewer** - thorough, precise.

**Your approach:**
- ✓ **Verify:** Verify all claims with evidence

## Verdict

**🔧 NEEDS WORK**

- Critical issues: 2
- Warnings: 44
- Files analyzed: 62

## Overview

**Files Analyzed**: 62
**Pattern Issues**: 7
**Performance Hotspots**: 3
**Total Issues**: 46

## Performance Hotspots

- **tests/subservers/review/test_deps.py::TestDepsSubServer::test_summary_includes_mindset**: 7.16s
- **tests/subservers/review/test_deps.py::TestDepsSubServer::test_execute_python_project**: 6.11s
- **tests/servers/test_review.py::TestReviewMCPServer::test_run_all**: 1.02s

## Anti-Pattern Detections

- `/media/srv-main-softdev/projects/MCP/btx_fix_mcp/scripts/clean.py:34` - Nested loop detected
- `/media/srv-main-softdev/projects/MCP/btx_fix_mcp/src/btx_fix_mcp/subservers/review/deps_scanners.py:47` - Nested loop detected
- `/media/srv-main-softdev/projects/MCP/btx_fix_mcp/src/btx_fix_mcp/subservers/review/perf.py:224` - Nested loop detected
- `/media/srv-main-softdev/projects/MCP/btx_fix_mcp/src/btx_fix_mcp/subservers/review/perf.py:240` - Using range(len()) - consider enumerate() or direct iteration
- `/media/srv-main-softdev/projects/MCP/btx_fix_mcp/src/btx_fix_mcp/subservers/review/quality/complexity.py:54` - Nested loop detected
- `/media/srv-main-softdev/projects/MCP/btx_fix_mcp/src/btx_fix_mcp/subservers/review/report.py:400` - Nested loop detected
- `/media/srv-main-softdev/projects/MCP/btx_fix_mcp/src/btx_fix_mcp/subservers/review/report.py:457` - Nested loop detected

## Approval Status

**🔧 NEEDS WORK**

- Address critical issues before merging
- Ask yourself: Is this correct? Let me check.