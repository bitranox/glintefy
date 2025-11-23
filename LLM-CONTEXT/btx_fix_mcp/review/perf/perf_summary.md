# Performance Analysis Report

## Reviewer Mindset

**You are a perf reviewer** - thorough, precise.

**Your approach:**
- ✓ **Verify:** Verify all claims with evidence

## Verdict

**🔧 NEEDS WORK**

- Critical issues: 2
- Warnings: 47
- Files analyzed: 43

## Overview

**Files Analyzed**: 43
**Pattern Issues**: 8
**Performance Hotspots**: 4
**Total Issues**: 49

## Performance Hotspots (showing 4 of 4)

- **tests/subservers/review/test_deps.py::TestDepsSubServer::test_execute_python_project**: 7.59s
- **tests/subservers/review/test_deps.py::TestDepsSubServer::test_summary_includes_mindset**: 6.93s
- **tests/servers/test_review.py::TestReviewMCPServer::test_run_quality**: 1.55s
- **tests/servers/test_review.py::TestReviewMCPServer::test_run_all**: 1.29s

## Anti-Pattern Detections (showing 8 of 8)

- `/media/srv-main-softdev/projects/MCP/btx_fix_mcp/src/btx_fix_mcp/subservers/common/chunked_writer.py:161` - Nested loop detected
- `/media/srv-main-softdev/projects/MCP/btx_fix_mcp/src/btx_fix_mcp/subservers/review/deps_scanners.py:49` - Nested loop detected
- `/media/srv-main-softdev/projects/MCP/btx_fix_mcp/src/btx_fix_mcp/subservers/review/docs.py:418` - Nested loop detected
- `/media/srv-main-softdev/projects/MCP/btx_fix_mcp/src/btx_fix_mcp/subservers/review/perf.py:237` - Nested loop detected
- `/media/srv-main-softdev/projects/MCP/btx_fix_mcp/src/btx_fix_mcp/subservers/review/perf.py:253` - Using range(len()) - consider enumerate() or direct iteration
- `/media/srv-main-softdev/projects/MCP/btx_fix_mcp/src/btx_fix_mcp/subservers/review/quality/complexity.py:78` - Nested loop detected
- `/media/srv-main-softdev/projects/MCP/btx_fix_mcp/src/btx_fix_mcp/subservers/review/report.py:419` - Nested loop detected
- `/media/srv-main-softdev/projects/MCP/btx_fix_mcp/src/btx_fix_mcp/subservers/review/report.py:493` - Nested loop detected

## Approval Status

**🔧 NEEDS WORK**

- Address critical issues before merging
- Ask yourself: Is this correct? Let me check.