# Performance Analysis Report

## Reviewer Mindset

**You are a perf reviewer** - thorough, precise.

**Your approach:**
- ✓ **Verify:** Verify all claims with evidence

## Verdict

**🔧 NEEDS WORK**

- Critical issues: 2
- Warnings: 54
- Files analyzed: 55

## Overview

**Files Analyzed**: 55
**Pattern Issues**: 11
**Performance Hotspots**: 5
**Total Issues**: 56

## Performance Hotspots

- **tests/subservers/review/test_deps.py::TestDepsSubServer::test_execute_python_project**: 7.78s
- **tests/subservers/review/test_deps.py::TestDepsSubServer::test_summary_includes_mindset**: 7.45s
- **tests/servers/test_review.py::TestReviewMCPServer::test_run_quality**: 1.30s
- **tests/servers/test_review.py::TestReviewMCPServer::test_run_all**: 1.27s
- **tests/subservers/review/test_quality.py::TestQualitySubServer::test_execute_with_simple_code**: 1.04s

## Anti-Pattern Detections

- `/media/srv-main-softdev/projects/MCP/btx_fix_mcp/scripts/clean.py:34` - Nested loop detected
- `/media/srv-main-softdev/projects/MCP/btx_fix_mcp/src/btx_fix_mcp/subservers/review/deps.py:292` - Nested loop detected
- `/media/srv-main-softdev/projects/MCP/btx_fix_mcp/src/btx_fix_mcp/subservers/review/docs.py:235` - Regex not precompiled
- `/media/srv-main-softdev/projects/MCP/btx_fix_mcp/src/btx_fix_mcp/subservers/review/perf.py:230` - Nested loop detected
- `/media/srv-main-softdev/projects/MCP/btx_fix_mcp/src/btx_fix_mcp/subservers/review/perf.py:244` - Using range(len()) - consider enumerate() or direct iteration
- `/media/srv-main-softdev/projects/MCP/btx_fix_mcp/src/btx_fix_mcp/subservers/review/quality.py:253` - Nested loop detected
- `/media/srv-main-softdev/projects/MCP/btx_fix_mcp/src/btx_fix_mcp/subservers/review/quality/__init__.py:518` - Nested loop detected
- `/media/srv-main-softdev/projects/MCP/btx_fix_mcp/src/btx_fix_mcp/subservers/review/quality/complexity.py:52` - Nested loop detected
- `/media/srv-main-softdev/projects/MCP/btx_fix_mcp/src/btx_fix_mcp/subservers/review/quality/types.py:129` - Regex not precompiled
- `/media/srv-main-softdev/projects/MCP/btx_fix_mcp/src/btx_fix_mcp/subservers/review/report.py:330` - Nested loop detected
- ... and 1 more

## Approval Status

**🔧 NEEDS WORK**

- Address critical issues before merging
- Ask yourself: Is this correct? Let me check.