# Quality Analysis Report

## Reviewer Mindset

**You are a quality reviewer** - thorough, precise.

**Your approach:**
- ✓ **Verify:** Verify all claims with evidence

## Verdict

**🔧 NEEDS WORK**

- Critical issues: 3 (4.8%)
- Warnings: 179 (288.7%)
- Total items analyzed: 62

## Overview

**Files Analyzed**: 62 (62 Python, 0 JS/TS)
**Functions Analyzed**: 501
**Total Issues Found**: 226
**Critical Issues**: 3

## Code Metrics

- Total LOC: **12,206**
- Source LOC (SLOC): **7,749**
- Comments: **420**
- Comment Ratio: **5.4%**

## Quality Issues Summary

- Functions >50 lines: **31**
- High cyclomatic complexity (>10): **26**
- High cognitive complexity (>15): **21**
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

- 🔴 `src/btx_fix_mcp/subservers/review/report.py`: Function '_generate_report' is 109 lines (max: 50)
- 🔴 `src/btx_fix_mcp/subservers/review/security.py`: Function '_generate_summary' is 116 lines (max: 50)
- 🔴 `src/btx_fix_mcp/subservers/review/deps.py`: Class 'DepsSubServer' is a god object (19 methods, 550 lines)

## Refactoring Recommendations

1. **Break Down Long Functions**: 31 functions exceed 50 lines
2. **Reduce Cyclomatic Complexity**: 26 functions exceed threshold
3. **Reduce Cognitive Complexity**: 21 functions are too complex
4. **Extract Duplicated Code**: 66 duplicate blocks found
5. **Refactor God Objects**: 1 classes need decomposition
6. **Add Type Annotations**: Coverage is 0%
7. **Add Docstrings**: Coverage is 0.0%
8. **Remove Dead Code**: 1 unused items found

## Approval Status

**🔧 NEEDS WORK**

- Address critical issues before merging
- Ask yourself: Is this correct? Let me check.