# Quality Analysis Report

## Reviewer Mindset

**You are a quality reviewer** - thorough, precise.

**Your approach:**
- ✓ **Verify:** Verify all claims with evidence

## Verdict

**🔧 NEEDS WORK**

- Critical issues: 1 (1.6%)
- Warnings: 173 (279.0%)
- Total items analyzed: 62

## Overview

**Files Analyzed**: 62 (62 Python, 0 JS/TS)
**Functions Analyzed**: 521
**Total Issues Found**: 218
**Critical Issues**: 1

## Code Metrics

- Total LOC: **12,307**
- Source LOC (SLOC): **7,820**
- Comments: **406**
- Comment Ratio: **5.2%**

## Quality Issues Summary

- Functions >50 lines: **28**
- High cyclomatic complexity (>10): **23**
- High cognitive complexity (>15): **19**
- Functions with nesting >3: **32**
- Code duplication blocks: **66**
- God objects: **1**
- Highly coupled modules: **1**
- Import cycles: **0**
- Dead code items: **1**

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

- Status: **✅ Passed**

## Critical Issues (Must Fix)

- 🔴 `src/btx_fix_mcp/subservers/review/deps.py`: Class 'DepsSubServer' is a god object (27 methods, 590 lines)

## Refactoring Recommendations

1. **Break Down Long Functions**: 28 functions exceed 50 lines
2. **Reduce Cyclomatic Complexity**: 23 functions exceed threshold
3. **Reduce Cognitive Complexity**: 19 functions are too complex
4. **Extract Duplicated Code**: 66 duplicate blocks found
5. **Refactor God Objects**: 1 classes need decomposition
6. **Add Type Annotations**: Coverage is 0%
7. **Add Docstrings**: Coverage is 0.0%
8. **Remove Dead Code**: 1 unused items found

## Approval Status

**🔧 NEEDS WORK**

- Address critical issues before merging
- Ask yourself: Is this correct? Let me check.