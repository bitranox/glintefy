# Quality Analysis Report

## Reviewer Mindset

**You are a quality reviewer** - thorough, precise.

**Your approach:**
- ✓ **Verify:** Verify all claims with evidence

## Verdict

**🔧 NEEDS WORK**

- Critical issues: 2 (3.2%)
- Warnings: 142 (225.4%)
- Total items analyzed: 63

## Overview

**Files Analyzed**: 63 (63 Python, 0 JS/TS)
**Functions Analyzed**: 572
**Total Issues Found**: 193
**Critical Issues**: 2

## Code Metrics

- Total LOC: **12,919**
- Source LOC (SLOC): **8,064**
- Comments: **437**
- Comment Ratio: **5.4%**

## Quality Issues Summary

- Functions >50 lines: **29**
- High cyclomatic complexity (>10): **17**
- High cognitive complexity (>15): **10**
- Functions with nesting >3: **16**
- Code duplication blocks: **66**
- God objects: **2**
- Highly coupled modules: **1**
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

- Status: **✅ Passed**

## Critical Issues (Must Fix)

- 🔴 `src/btx_fix_mcp/subservers/review/deps.py`: Class 'DepsSubServer' is a god object (27 methods, 586 lines)
- 🔴 `src/btx_fix_mcp/subservers/review/quality/architecture.py`: Class 'ArchitectureAnalyzer' is a god object (22 methods, 279 lines)

## Refactoring Recommendations

1. **Break Down Long Functions**: 29 functions exceed 50 lines
2. **Reduce Cyclomatic Complexity**: 17 functions exceed threshold
3. **Reduce Cognitive Complexity**: 10 functions are too complex
4. **Extract Duplicated Code**: 66 duplicate blocks found
5. **Refactor God Objects**: 2 classes need decomposition
6. **Add Type Annotations**: Coverage is 0%
7. **Add Docstrings**: Coverage is 0.0%

## Approval Status

**🔧 NEEDS WORK**

- Address critical issues before merging
- Ask yourself: Is this correct? Let me check.