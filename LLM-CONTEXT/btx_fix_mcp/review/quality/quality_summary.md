# Quality Analysis Report

## Reviewer Mindset

**You are a quality reviewer** - thorough, precise.

**Your approach:**
- ✓ **Verify:** Verify all claims with evidence

## Verdict

**❌ REJECTED**

- Critical issues: 6 (14.0%)
- Warnings: 66 (153.5%)
- Total items analyzed: 43

## Overview

**Files Analyzed**: 43 (43 Python, 0 JS/TS)
**Functions Analyzed**: 503
**Total Issues Found**: 99
**Critical Issues**: 6

## Code Metrics

- Total LOC: **11,297**
- Source LOC (SLOC): **6,888**
- Comments: **331**
- Comment Ratio: **4.8%**

## Quality Issues Summary

- Functions >50 lines: **17**
- High cyclomatic complexity (>10): **0**
- High cognitive complexity (>15): **4**
- Functions with nesting >3: **12**
- Code duplication blocks: **30**
- God objects: **5**
- Highly coupled modules: **0**
- Import cycles: **0**
- Dead code items: **0**

## Coverage Metrics

- Type coverage: **0%** (minimum: 80%)
- Docstring coverage: **0.0%** (minimum: 80%)

## Test Suite Analysis

- Total tests: **0**
- Total assertions: **0**
- Assertions per test: **0**
- Unit tests: 0
- Integration tests: 0
- E2E tests: 0
- Test issues: **0**

## Runtime Type Checking (Beartype)

- Status: **❌ Failed**

## Critical Issues (Must Fix)

- 🔴 `src/btx_fix_mcp/subservers/review/deps.py`: Class 'DepsSubServer' is a god object (27 methods, 623 lines)
- 🔴 `src/btx_fix_mcp/subservers/review/docs.py`: Class 'DocsSubServer' is a god object (42 methods, 714 lines)
- 🔴 `src/btx_fix_mcp/subservers/review/perf.py`: Class 'PerfSubServer' is a god object (19 methods, 526 lines)
- 🔴 `src/btx_fix_mcp/subservers/review/quality/architecture.py`: Class 'ArchitectureAnalyzer' is a god object (22 methods, 303 lines)
- 🔴 `src/btx_fix_mcp/subservers/review/security.py`: Class 'SecuritySubServer' is a god object (25 methods, 606 lines)
- 🔴 : Test run timed out

## Refactoring Recommendations

1. **Break Down Long Functions**: 17 functions exceed 50 lines
2. **Reduce Cognitive Complexity**: 4 functions are too complex
3. **Extract Duplicated Code**: 30 duplicate blocks found
4. **Refactor God Objects**: 5 classes need decomposition
5. **Add Type Annotations**: Coverage is 0%
6. **Add Docstrings**: Coverage is 0.0%

## Approval Status

**❌ REJECTED**

- Address critical issues before merging
- Ask yourself: Is this correct? Let me check.