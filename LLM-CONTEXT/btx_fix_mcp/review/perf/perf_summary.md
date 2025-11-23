# Performance Analysis Report

## Reviewer Mindset

**You are a perf reviewer** - thorough, precise.

**Your approach:**
- ✓ **Verify:** Verify all claims with evidence

## Verdict

**🔧 NEEDS WORK**

- Critical issues: 2
- Warnings: 41
- Files analyzed: 63

## Overview

**Files Analyzed**: 63
**Pattern Issues**: 8
**Performance Hotspots**: 4
**Total Issues**: 43

## Performance Hotspots

- **tests/subservers/review/test_deps.py::TestDepsSubServer::test_execute_python_project**: 5.91s
- **tests/subservers/review/test_deps.py::TestDepsSubServer::test_summary_includes_mindset**: 5.53s
- **tests/servers/test_review.py::TestReviewMCPServer::test_run_all**: 1.11s
- **tests/servers/test_review.py::TestReviewMCPServer::test_run_quality**: 1.05s

## Anti-Pattern Detections

- `/media/srv-main-softdev/projects/MCP/btx_fix_mcp/scripts/clean.py:34` - Nested loop detected
- `/media/srv-main-softdev/projects/MCP/btx_fix_mcp/src/btx_fix_mcp/subservers/common/chunked_writer.py:161` - Nested loop detected
- `/media/srv-main-softdev/projects/MCP/btx_fix_mcp/src/btx_fix_mcp/subservers/review/deps_scanners.py:47` - Nested loop detected
- `/media/srv-main-softdev/projects/MCP/btx_fix_mcp/src/btx_fix_mcp/subservers/review/perf.py:228` - Nested loop detected
- `/media/srv-main-softdev/projects/MCP/btx_fix_mcp/src/btx_fix_mcp/subservers/review/perf.py:244` - Using range(len()) - consider enumerate() or direct iteration
- `/media/srv-main-softdev/projects/MCP/btx_fix_mcp/src/btx_fix_mcp/subservers/review/quality/complexity.py:76` - Nested loop detected
- `/media/srv-main-softdev/projects/MCP/btx_fix_mcp/src/btx_fix_mcp/subservers/review/report.py:413` - Nested loop detected
- `/media/srv-main-softdev/projects/MCP/btx_fix_mcp/src/btx_fix_mcp/subservers/review/report.py:470` - Nested loop detected

## Approval Status

**🔧 NEEDS WORK**

- Address critical issues before merging
- Ask yourself: Is this correct? Let me check.