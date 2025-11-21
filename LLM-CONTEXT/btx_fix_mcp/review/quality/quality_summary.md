# Quality Analysis Report

## Reviewer Mindset

**You are a quality reviewer** - thorough, precise.

**Your approach:**
- ✓ **Verify:** Verify all claims with evidence

## Verdict

**❌ REJECTED**

- Critical issues: 13 (23.2%)
- Warnings: 252 (450.0%)
- Total items analyzed: 56

## Overview

**Files Analyzed**: 56 (56 Python, 0 JS/TS)
**Functions Analyzed**: 452
**Total Issues Found**: 302
**Critical Issues**: 13

## Code Metrics

- Total LOC: **11,676**
- Source LOC (SLOC): **7,663**
- Comments: **462**
- Comment Ratio: **6.0%**

## Quality Issues Summary

- Functions >50 lines: **37**
- High cyclomatic complexity (>10): **32**
- High cognitive complexity (>15): **28**
- Functions with nesting >3: **38**
- Code duplication blocks: **104**
- God objects: **1**
- Highly coupled modules: **1**
- Import cycles: **0**
- Dead code items: **2**

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

- 🔴 `src/btx_fix_mcp/subservers/review/quality/__init__.py`: Function 'execute' has complexity 34 (threshold: 10)
- 🔴 `src/btx_fix_mcp/subservers/review/quality/__init__.py`: Function '_generate_comprehensive_summary' has complexity 31 (threshold: 10)
- 🔴 `src/btx_fix_mcp/subservers/review/quality/__init__.py`: Function '_compile_all_issues' has complexity 27 (threshold: 10)
- 🔴 `src/btx_fix_mcp/subservers/review/quality/__init__.py`: Function '_run_analyzers_parallel' has complexity 21 (threshold: 10)
- 🔴 `src/btx_fix_mcp/subservers/review/quality/metrics.py`: Function '_analyze_code_churn' has complexity 21 (threshold: 10)
- 🔴 `src/btx_fix_mcp/subservers/review/quality/__init__.py`: File has maintainability index 8.1 (threshold: 20)
- 🔴 `src/btx_fix_mcp/subservers/review/quality/__init__.py`: Function '_run_analyzers_parallel' is 102 lines (max: 50)
- 🔴 `src/btx_fix_mcp/subservers/review/quality/__init__.py`: Function 'execute' is 143 lines (max: 50)
- 🔴 `src/btx_fix_mcp/subservers/review/quality/__init__.py`: Function '_compile_all_issues' is 160 lines (max: 50)
- 🔴 `src/btx_fix_mcp/subservers/review/quality/__init__.py`: Function '_generate_comprehensive_summary' is 132 lines (max: 50)
- 🔴 `src/btx_fix_mcp/subservers/review/quality/metrics.py`: Function '_analyze_code_churn' is 119 lines (max: 50)
- 🔴 `src/btx_fix_mcp/subservers/review/security.py`: Function '_generate_summary' is 110 lines (max: 50)
- 🔴 `src/btx_fix_mcp/subservers/review/quality/__init__.py`: Class 'QualitySubServer' is a god object (41 methods, 1014 lines)

## Refactoring Recommendations

1. **Break Down Long Functions**: 37 functions exceed 50 lines
2. **Reduce Cyclomatic Complexity**: 32 functions exceed threshold
3. **Reduce Cognitive Complexity**: 28 functions are too complex
4. **Extract Duplicated Code**: 104 duplicate blocks found
5. **Refactor God Objects**: 1 classes need decomposition
6. **Add Type Annotations**: Coverage is 0%
7. **Add Docstrings**: Coverage is 0.0%
8. **Remove Dead Code**: 2 unused items found

## Approval Status

**❌ REJECTED**

- Address critical issues before merging
- Ask yourself: Is this correct? Let me check.