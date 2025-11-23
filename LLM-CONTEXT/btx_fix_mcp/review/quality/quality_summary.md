# Quality Analysis Report

## Reviewer Mindset

**You are a quality reviewer** - thorough, precise.

**Your approach:**
- ✓ **Verify:** Verify all claims with evidence

## Verdict

**❌ REJECTED**

- Critical issues: 8 (18.6%)
- Warnings: 102 (237.2%)
- Total items analyzed: 43

## Overview

**Files Analyzed**: 43 (43 Python, 0 JS/TS)
**Functions Analyzed**: 420
**Total Issues Found**: 136
**Critical Issues**: 8

## Code Metrics

- Total LOC: **10,855**
- Source LOC (SLOC): **6,558**
- Comments: **390**
- Comment Ratio: **5.9%**

## Quality Issues Summary

- Functions >50 lines: **29**
- High cyclomatic complexity (>10): **19**
- High cognitive complexity (>15): **9**
- Functions with nesting >3: **14**
- Code duplication blocks: **32**
- God objects: **4**
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

- 🔴 `src/btx_fix_mcp/subservers/review/docs.py`: Function '_generate_summary' has complexity 21 (threshold: 10)
- 🔴 `src/btx_fix_mcp/subservers/review/perf.py`: Function '_generate_summary' has complexity 22 (threshold: 10)
- 🔴 `src/btx_fix_mcp/subservers/review/security.py`: Function '_run_bandit' has complexity 21 (threshold: 10)
- 🔴 `src/btx_fix_mcp/subservers/review/deps.py`: Class 'DepsSubServer' is a god object (27 methods, 623 lines)
- 🔴 `src/btx_fix_mcp/subservers/review/docs.py`: Class 'DocsSubServer' is a god object (11 methods, 545 lines)
- 🔴 `src/btx_fix_mcp/subservers/review/quality/architecture.py`: Class 'ArchitectureAnalyzer' is a god object (22 methods, 303 lines)
- 🔴 `src/btx_fix_mcp/subservers/review/security.py`: Class 'SecuritySubServer' is a god object (16 methods, 550 lines)
- 🔴 : Test run timed out

## Refactoring Recommendations

1. **Break Down Long Functions**: 29 functions exceed 50 lines
2. **Reduce Cyclomatic Complexity**: 19 functions exceed threshold
3. **Reduce Cognitive Complexity**: 9 functions are too complex
4. **Extract Duplicated Code**: 32 duplicate blocks found
5. **Refactor God Objects**: 4 classes need decomposition
6. **Add Type Annotations**: Coverage is 0%
7. **Add Docstrings**: Coverage is 0.0%

## Approval Status

**❌ REJECTED**

- Address critical issues before merging
- Ask yourself: Is this correct? Let me check.