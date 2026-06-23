# Fix Code Review Findings - Orchestrator

## Configuration Constants

```bash
# Cache optimization
readonly DEFAULT_CACHE_SIZE=128  # Default LRU cache size

# Performance thresholds
readonly MIN_IMPROVEMENT_PERCENT=5  # Minimum performance improvement percentage to accept optimization

# Priority scoring
readonly PRIORITY_SCORE_MAX=100  # Maximum priority score for critical issues
```

## Overview

**ACTUALLY FIXES CODE** using evidence-based verification. This orchestrator doesn't just recommend fixes - it MODIFIES CODE, RUNS TESTS 3X, COMPARES METRICS, and KEEPS OR REVERTS based on evidence.

**Philosophy Change:**
- **OLD:** "Create plan, recommend fixes, manual implementation"
- **NEW:** "Measure, fix, verify with evidence, keep if proven, revert if not"

This orchestrator creates an actionable plan, then delegates to specialized sub-agents that:
1. Actually modify code (not just recommendations)
2. Run tests 3x to detect flaky tests
3. Compare before/after metrics with evidence
4. Git commit successful fixes
5. Git revert failed fixes

Maintains the **reviewer mindset** throughout: pedantic, thorough, zero-tolerance for unverified claims or poor quality.

## Reviewer Mindset for Fixes

**You are a meticulous fixer with exceptional attention to detail - pedantic, precise, and relentlessly thorough.**

Your approach:
- ✓ **Every Single Fix:** Verify with tests run 3x (detect flaky tests)
- ✓ **No Trust - Re-measure Everything:** Don't trust review, capture your own baseline
- ✓ **Verify Before AND After:** Prove issue exists, then prove fix works
- ✓ **Evidence Required:** Before/after metrics, test results, profiling data
- ✓ **Root Cause Fixes:** Fix underlying problems, not symptoms
- ✓ **Keep Only Proven Fixes:** Git commit successes, revert failures immediately

**Your Questions:**
- "Does this issue actually exist? Let me measure baseline first."
- "Did my fix actually work? Let me run tests 3x to verify."
- "Are there flaky tests? Let me compare 3 test runs."
- "Did metrics improve? Let me compare before/after evidence."

## Core Principle

**Evidence-Based Fixing Protocol:**

This orchestrator ACTUALLY MODIFIES CODE and uses EVIDENCE-BASED VERIFICATION to determine success:

1. **Measure Before** - Capture baseline metrics (tests 3x, coverage, security scans)
2. **Fix Incrementally** - Make one fix at a time, verify with evidence
3. **Verify After** - Run tests 3x to detect flaky tests, compare metrics
4. **Keep or Revert** - Keep if evidence proves improvement, revert if not
5. **Commit Proven Fixes** - Git commit successful fixes, revert failed ones

**DON'T TRUST REVIEW - RE-MEASURE EVERYTHING:**
- Review identified issues, but **verify they ACTUALLY exist** before fixing (capture baseline)
- After fixing, verify improvement with **EVIDENCE** (not assumptions)
- Tests run **3x** to detect flaky/intermittent failures
- If evidence shows regression, **REVERT immediately**
- Compare against **baseline captured in Step 0.5** (not review's claims)

**Fix in the spirit of the reviewer:**
- Every fix must be verified with evidence (tests, profiling, reproduction)
- No functions >50 lines, no complexity >10, no duplication
- Always use REAL test data, never synthetic benchmarks
- Root cause fixes only - no symptom patching
- Refactor before optimizing
- Every claim must be proven

## Prerequisites

**MUST run `bx_review_anal` first** - This orchestrator requires:
- `LLM-CONTEXT/review-anal/report/review_report.md` - Final review report
- `LLM-CONTEXT/review-anal/quality/refactoring_recommendations.md` - Quality issues
- `LLM-CONTEXT/review-anal/security/security_analysis_report.md` - Security issues
- All other subagent outputs in `LLM-CONTEXT/review-anal/`

## Orchestration Strategy

This command delegates to specialized fix sub-agents that ACTUALLY MODIFY CODE:

1. **Baseline Metrics** - Capture before-fix evidence (tests 3x, coverage, security)
2. **Fix Planning** - Parse findings, create actionable plan with evidence requirements
3. **Critical Fixes** - Actually fix security/test issues, verify 3x, commit or revert
4. **Quality Fixes** - Actually refactor code, verify 3x, commit or revert
5. **Test Refactoring** - Actually refactor test suite, verify 3x, commit or revert
6. **Cache Optimization** - Actually apply caching, verify 3x, commit or revert
7. **Documentation Fixes** - Actually add docs, verify 3x, commit or revert
8. **Verification** - Run tests 3x, compare metrics, detect flaky tests
9. **Evidence Validation** - Verify all evidence exists and metrics improved
10. **Log Analysis** - Analyze logs for errors, git commits, file modifications, diagnostics
11. **Final Report** - Summary of ACTUAL fixes applied with git commits and evidence

## Execution Flow

### Step 0.5: Capture Baseline Metrics (CRITICAL)

**BEFORE making ANY changes, capture baseline metrics for evidence-based comparison:**

```bash
echo "=== CAPTURING BASELINE METRICS ==="
echo "CRITICAL: DON'T TRUST REVIEW - RE-MEASURE EVERYTHING"
echo ""

# Create metrics directory
mkdir -p LLM-CONTEXT/fix-anal/metrics

# Run tests 3x to establish baseline (detect flaky tests)
echo "Running tests 3x to establish baseline and detect flaky tests..."
for i in 1 2 3; do
    echo "Test run $i/3..."
    # Adjust test command for your project (pytest, npm test, go test, etc.)
    # Exclude specified folders from testing
    pytest --verbose --tb=short --ignore=scripts --ignore=LLM-CONTEXT --ignore=.idea --ignore=.git --ignore=.github --ignore=.claude --ignore=.devcontainer --ignore=.pytest_cache --ignore=.qlty --ignore=.ruff_cache > "LLM-CONTEXT/fix-anal/metrics/baseline_tests_run${i}.txt" 2>&1 || true
done

# Capture test summary
echo "Analyzing baseline test stability..."
grep -E "(PASSED|FAILED|ERROR)" LLM-CONTEXT/fix-anal/metrics/baseline_tests_run*.txt > LLM-CONTEXT/fix-anal/metrics/baseline_test_summary.txt 2>&1 || true

# Capture code coverage (if available)
echo "Capturing baseline coverage..."
pytest --cov --cov-report=term --ignore=scripts --ignore=LLM-CONTEXT --ignore=.idea --ignore=.git --ignore=.github --ignore=.claude --ignore=.devcontainer --ignore=.pytest_cache --ignore=.qlty --ignore=.ruff_cache > LLM-CONTEXT/fix-anal/metrics/baseline_coverage.txt 2>&1 || true

# Capture security baseline (if tools available)
echo "Capturing baseline security scan..."
bandit -r . -f txt --exclude './scripts,./LLM-CONTEXT,./.idea,./.git,./.github,./.claude,./.devcontainer,./.pytest_cache,./.qlty,./.ruff_cache' > LLM-CONTEXT/fix-anal/metrics/baseline_security.txt 2>&1 || true

# Capture code quality metrics (if tools available)
echo "Capturing baseline quality metrics..."
radon cc . -a -s --exclude 'scripts,LLM-CONTEXT,.idea,.git,.github,.claude,.devcontainer,.pytest_cache,.qlty,.ruff_cache' > LLM-CONTEXT/fix-anal/metrics/baseline_complexity.txt 2>&1 || true
radon mi . -s --exclude 'scripts,LLM-CONTEXT,.idea,.git,.github,.claude,.devcontainer,.pytest_cache,.qlty,.ruff_cache' > LLM-CONTEXT/fix-anal/metrics/baseline_maintainability.txt 2>&1 || true

echo "✓ Baseline metrics captured"
echo "  - Test runs: LLM-CONTEXT/fix-anal/metrics/baseline_tests_run{1,2,3}.txt"
echo "  - Coverage: LLM-CONTEXT/fix-anal/metrics/baseline_coverage.txt"
echo "  - Security: LLM-CONTEXT/fix-anal/metrics/baseline_security.txt"
echo "  - Complexity: LLM-CONTEXT/fix-anal/metrics/baseline_complexity.txt"
echo ""
```

### Step 1: Initialize Fix Environment

```bash
# Ensure we're in a project directory (detect git root or use current directory)
# Try to find git root first, otherwise use current directory
if git rev-parse --show-toplevel &>/dev/null; then
    PROJECT_ROOT=$(git rev-parse --show-toplevel)
    echo "✓ Detected git repository root: $PROJECT_ROOT"
else
    PROJECT_ROOT=$(pwd)
    echo "✓ Using current directory as project root: $PROJECT_ROOT"
fi

cd "$PROJECT_ROOT" || exit 1
echo "✓ Working directory: $(pwd)"

# Ensure fix directory structure exists
mkdir -p LLM-CONTEXT/fix-anal/{plan,critical,quality,refactor-tests,cache,docs,verification,report,metrics,evidence,logs,scripts}
echo "Created LLM-CONTEXT/fix-anal directory structure"

# Create logging script on the fly
cat > LLM-CONTEXT/fix-anal/scripts/log.sh << 'EOF'
#!/bin/bash
# Logging utility for orchestrator scripts
# LOG_FILE must be set before sourcing this script

log_info() {
    if [ -z "$LOG_FILE" ]; then
        echo "ERROR: LOG_FILE not set" >&2
        return 1
    fi
    mkdir -p "$(dirname "$LOG_FILE")"
    local timestamp=$(date -Iseconds)
    echo "[$timestamp] INFO: $1" | tee -a "$LOG_FILE"
}

log_error() {
    if [ -z "$LOG_FILE" ]; then
        echo "ERROR: LOG_FILE not set" >&2
        return 1
    fi
    mkdir -p "$(dirname "$LOG_FILE")"
    local timestamp=$(date -Iseconds)
    echo "[$timestamp] ERROR: $1" | tee -a "$LOG_FILE" >&2
}

log_warning() {
    if [ -z "$LOG_FILE" ]; then
        echo "ERROR: LOG_FILE not set" >&2
        return 1
    fi
    mkdir -p "$(dirname "$LOG_FILE")"
    local timestamp=$(date -Iseconds)
    echo "[$timestamp] WARNING: $1" | tee -a "$LOG_FILE"
}
EOF
chmod +x LLM-CONTEXT/fix-anal/scripts/log.sh
echo "✓ Created logging script: LLM-CONTEXT/fix-anal/scripts/log.sh"

# Step 1.5: Create Python 3.13 Virtual Environment
echo ""
echo "Setting up Python 3.13 virtual environment..."

# Find Python 3.13 system installation
SYSTEM_PYTHON=""

if command -v python3.13 &> /dev/null; then
    SYSTEM_PYTHON="python3.13"
    PYTHON_VERSION=$(python3.13 --version 2>&1)
    echo "✓ Found system Python: $PYTHON_VERSION at $(which python3.13)"
elif command -v python3 &> /dev/null; then
    # Check if python3 is actually 3.13
    PYTHON_VERSION=$(python3 --version 2>&1)
    if echo "$PYTHON_VERSION" | grep -q "Python 3\.13"; then
        SYSTEM_PYTHON="python3"
        echo "✓ Found system Python: $PYTHON_VERSION at $(which python3)"
    fi
fi

# If not found, error
if [ -z "$SYSTEM_PYTHON" ]; then
    echo ""
    echo "❌ ERROR: Python 3.13 not found"
    echo ""
    echo "Python 3.13 is required for code analysis and fixing tools."
    echo ""
    echo "Please install Python 3.13 and make it available as 'python3.13' in PATH"
    echo "Exiting. Please install Python 3.13."
    exit 1
fi

# Create venv if it doesn't exist
VENV_DIR="LLM-CONTEXT/venv/python-3.13"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment at $VENV_DIR..."
    $SYSTEM_PYTHON -m venv "$VENV_DIR"
    if [ $? -eq 0 ]; then
        echo "✓ Virtual environment created successfully"
    else
        echo "❌ ERROR: Failed to create virtual environment"
        exit 1
    fi
else
    echo "✓ Virtual environment already exists at $VENV_DIR"
fi

# Set PYTHON_CMD to venv python
PYTHON_CMD="$VENV_DIR/bin/python"
if [ ! -f "$PYTHON_CMD" ]; then
    echo "❌ ERROR: venv python not found at $PYTHON_CMD"
    exit 1
fi

# Verify venv python version
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
echo "✓ Using venv Python: $PYTHON_VERSION at $PYTHON_CMD"

# Upgrade pip in venv
echo "Upgrading pip in virtual environment..."
$PYTHON_CMD -m pip install --upgrade pip --quiet
echo "✓ pip upgraded"

# Export for subagents
export PYTHON_CMD
echo "✓ Python interpreter set to: $PYTHON_CMD"
echo ""

# Set log file and source logging functions
LOG_FILE="LLM-CONTEXT/fix-anal/logs/orchestrator.log"
source LLM-CONTEXT/fix-anal/scripts/log.sh

log_info "Fix orchestrator started"
log_info "Python interpreter set to: $PYTHON_CMD"

# Save Python path for subagents
echo "$PYTHON_CMD" > LLM-CONTEXT/fix-anal/python_path.txt
log_info "Python path saved to LLM-CONTEXT/fix-anal/python_path.txt"

# Initialize fix metadata
cat > LLM-CONTEXT/fix-anal/fix_metadata.json << EOF
{
  "fix_started": "$(date -Iseconds)",
  "review_report": "LLM-CONTEXT/review-anal/report/review_report.md",
  "baseline_metrics_captured": true,
  "evidence_based_verification": true,
  "test_runs_per_verification": 3,
  "subagents_used": []
}
EOF

echo "✓ Fix environment initialized"
```

### Step 1.5: Create Rollback Point

**IMPORTANT:** Create git backup before applying any fixes for easy rollback if needed.

```bash
echo "Creating rollback point..."

# Check if we're in a git repository
if git rev-parse --git-dir > /dev/null 2>&1; then
    # Save current commit SHA for rollback
    git rev-parse HEAD > LLM-CONTEXT/fix-anal/pre_fix_commit.txt
    echo "✓ Saved pre-fix commit SHA: $(cat LLM-CONTEXT/fix-anal/pre_fix_commit.txt)"

    # Create git stash as backup
    if git stash push -u -m "Pre-fix backup $(date -Iseconds)" > /dev/null 2>&1; then
        # If stash was created, record it
        STASH_REF=$(git stash list | head -n 1 | cut -d: -f1)
        echo "$STASH_REF" > LLM-CONTEXT/fix-anal/pre_fix_stash.txt
        echo "✓ Created backup stash: $STASH_REF"
    else
        echo "⚠ No changes to stash (working tree clean)"
    fi

    # Document rollback commands
    cat > LLM-CONTEXT/fix-anal/ROLLBACK_INSTRUCTIONS.md << 'EOF'
# Rollback Instructions

If fixes break tests or cause issues, you can rollback using these commands:

## Option 1: Reset to Pre-Fix Commit (Hard Reset)
```bash
# Validate pre-fix commit file exists
if [ ! -f "LLM-CONTEXT/fix-anal/pre_fix_commit.txt" ]; then
    log_error "pre_fix_commit.txt not found - cannot rollback without commit reference"
    echo "❌ ERROR: pre_fix_commit.txt not found"
    echo "Cannot rollback without commit reference"
    exit 1
fi

# Read and validate commit SHA
COMMIT_SHA=$(cat LLM-CONTEXT/fix-anal/pre_fix_commit.txt)

# Validate SHA format (40 hexadecimal characters)
if ! echo "$COMMIT_SHA" | grep -qE '^[0-9a-f]{40}$'; then
    log_error "Invalid commit SHA format: $COMMIT_SHA (expected 40 hexadecimal characters)"
    echo "❌ ERROR: Invalid commit SHA format: $COMMIT_SHA"
    echo "Expected 40 hexadecimal characters"
    exit 1
fi

# Verify commit exists in repository
if ! git cat-file -e "$COMMIT_SHA" 2>/dev/null; then
    log_error "Commit $COMMIT_SHA does not exist in repository"
    echo "❌ ERROR: Commit $COMMIT_SHA does not exist in repository"
    echo "It may have been garbage collected or is from a different repo"
    exit 1
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo "⚠️  WARNING: You have uncommitted changes that will be LOST with hard reset!"
    echo ""
    git status --short
    echo ""
    echo "Uncommitted changes shown above will be permanently deleted."
    echo "Press Ctrl+C to cancel, or Enter to continue with hard reset..."
    read -r
fi

# Show what will happen
echo "About to reset to commit: $COMMIT_SHA"
git log -1 --oneline "$COMMIT_SHA"
echo ""
echo "Press Ctrl+C to cancel, or Enter to proceed..."
read -r

# Perform hard reset
git reset --hard "$COMMIT_SHA"

if [ $? -eq 0 ]; then
    echo "✓ Successfully reset to pre-fix commit"
else
    log_error "Git reset failed"
    echo "❌ ERROR: Git reset failed"
    exit 1
fi
```
**WARNING:** This will discard ALL changes made during fix process.

## Option 2: Apply Pre-Fix Stash (If Available)
```bash
# First, check if stash exists
if [ -f "LLM-CONTEXT/fix-anal/pre_fix_stash.txt" ]; then
    STASH_REF=$(cat LLM-CONTEXT/fix-anal/pre_fix_stash.txt)
    git stash list | grep "$STASH_REF"
    # If found, apply it
    git stash apply "$STASH_REF"
fi
```

## Option 3: Manual Revert
Review the changes and revert specific files:
```bash
git diff $(cat LLM-CONTEXT/fix-anal/pre_fix_commit.txt) HEAD
git checkout $(cat LLM-CONTEXT/fix-anal/pre_fix_commit.txt) -- path/to/file
```

## Verification After Rollback
After rolling back, verify the system is stable:
```bash
# Run tests
pytest --verbose
# Or npm test, go test, etc.

# Verify git status
git status
```
EOF

    echo "✓ Rollback instructions saved to: LLM-CONTEXT/fix-anal/ROLLBACK_INSTRUCTIONS.md"
else
    echo "⚠ Not a git repository - rollback mechanism unavailable"
    echo "⚠ Manual backup recommended before proceeding"
fi

echo ""
```

### Step 2: Validate Prerequisites

```bash
echo "Validating prerequisites..."

# Check that review was run
if [ ! -f "LLM-CONTEXT/review-anal/report/review_report.md" ]; then
    echo "ERROR: Review report not found"
    echo "You must run /bx_review_anal first to generate findings"
    log_error "Review report not found - user must run /bx_review_anal first"
    exit 1
fi

# Check for review findings
if [ ! -d "LLM-CONTEXT/review-anal" ]; then
    echo "ERROR: Review artifacts not found"
    echo "Run /bx_review_anal to perform code review first"
    log_error "Review artifacts directory not found - user must run /bx_review_anal first"
    exit 1
fi

echo "✓ Prerequisites validated"
```

### Step 3: Create Fix Plan

Before delegating to the fix planning subagent, log the start:

```bash
echo "[$(date -Iseconds)] INFO: Starting fix planning subagent" | tee -a LLM-CONTEXT/fix-anal/logs/orchestrator.log
```

Delegate to the **Fix Planning Agent**:

```
Use the Task tool with:
- subagent_type: "general-purpose"
- description: "Create fix plan"
- prompt: "Execute /bx_fix_anal_sub_plan to analyze all findings from bx_review_anal and create a prioritized, ACTIONABLE fix plan. The planner will:
  1. Read the final review report
  2. Parse all subagent findings (quality, security, perf, docs, cicd)
  3. Categorize by severity: CRITICAL → MAJOR → MINOR
  4. Create fixing order respecting dependencies
  5. FOR EACH ISSUE, define:
     - Fix strategy (specific approach to fix)
     - Evidence requirements (what to measure before/after)
     - Success criteria (how to know fix worked)
     - Rollback triggers (when to revert)
  6. Save detailed plan to LLM-CONTEXT/fix-anal/plan/

  Return:
  - Total issues to fix
  - Breakdown by category and severity
  - Fixing order (which to tackle first)
  - Actionable fix strategies with evidence requirements
  - Estimated effort"
```

**Wait for planning to complete before proceeding.**

### Step 3.5: Validate Planning Success

Before proceeding to user approval, verify that planning completed successfully:

```bash
# Check planning status
if [ ! -f "LLM-CONTEXT/fix-anal/plan/status.txt" ]; then
    log_error "Planning status not found - planning subagent did not complete properly"
    echo "ERROR: Planning status not found"
    echo "Planning subagent did not complete properly"
    exit 1
fi

PLAN_STATUS=$(cat LLM-CONTEXT/fix-anal/plan/status.txt)

if [ "$PLAN_STATUS" != "SUCCESS" ]; then
    log_error "Planning failed with status: $PLAN_STATUS"
    echo "ERROR: Planning failed with status: $PLAN_STATUS"
    log_error "Fix planning failed - cannot proceed without valid fix plan"
    echo ""
    echo "Review planning output:"
    echo "  - LLM-CONTEXT/fix-anal/plan/"
    echo "  - Logs: LLM-CONTEXT/fix-anal/logs/plan.log"
    echo ""
    echo "Cannot proceed without valid fix plan"
    exit 1
else
    log_info "Fix planning completed successfully"
fi

log_info "Planning status: SUCCESS - proceeding to user approval"
echo "✓ Planning status: SUCCESS - proceeding to user approval"
```

**STOP if planning status is not SUCCESS.** User approval step requires a valid plan.

### Step 4: Review Plan with User

Present the fix plan and get approval:

```
Use AskUserQuestion tool:
- question: "The fix plan is ready. How would you like to proceed?"
- header: "Fix Strategy"
- multiSelect: false
- options:
  1. "Fix all issues" - "Apply all fixes in priority order (CRITICAL → MAJOR → MINOR)"
     description: "Comprehensive fix - addresses all identified issues"

  2. "Fix critical only" - "Fix only CRITICAL issues (security, test failures)"
     description: "Minimum viable fix - addresses only blocking issues"

  3. "Selective fixes" - "Choose which categories to fix"
     description: "Custom selection - pick specific issue types"

  4. "Review plan only" - "Show detailed plan, don't apply fixes yet"
     description: "Planning mode - review the approach before executing"
```

### Step 4.5: Execute Based on User Choice

Based on the user's selection, execute the appropriate workflow:

**If user selected "Review plan only":**

```bash
echo "Plan review mode selected"
echo ""
echo "Fix plan is available at:"
echo "  - LLM-CONTEXT/fix-anal/plan/fix_plan.md"
echo "  - LLM-CONTEXT/fix-anal/plan/issues.json"
echo "  - LLM-CONTEXT/fix-anal/plan/critical_issues.txt"
echo "  - LLM-CONTEXT/fix-anal/plan/major_issues.txt"
echo "  - LLM-CONTEXT/fix-anal/plan/minor_issues.txt"
echo ""
cat LLM-CONTEXT/fix-anal/plan/fix_plan.md
echo ""
echo "Review complete. Run /bx_fix_anal again to apply fixes."
exit 0
```

**STOP HERE** - Exit without applying any fixes.

**If user selected "Fix critical only":**

Execute only Step 5 (critical fixes), then skip directly to Step 8 (verification) and Step 9 (report). Do NOT execute Steps 6-7 (quality and docs).

**If user selected "Selective fixes":**

```
Use AskUserQuestion tool again:
- question: "Which fix categories would you like to apply?"
- header: "Fix Categories"
- multiSelect: true  # Allow multiple selections
- options:
  1. "Critical" - "Security vulnerabilities and test failures (MANDATORY)"
     description: "Always recommended - fixes blocking issues"

  2. "Quality" - "Code refactoring, complexity reduction, duplication removal"
     description: "Improves maintainability and code quality"

  3. "Documentation" - "Add docstrings, parameter docs, README improvements"
     description: "Improves code clarity and developer experience"
```

Then execute only the selected categories. If "Critical" is not selected, warn the user and ask for confirmation.

**If user selected "Fix all issues":**

Continue with normal flow - execute Steps 5, 6, 7, 8, 9 in order.

---

The following steps (5-9) should be executed conditionally based on the user's choice above.

### Step 5: Fix Critical Issues (MANDATORY for all except "Review plan only")

If user approved fixes, log the start and begin with critical issues:

```bash
echo "[$(date -Iseconds)] INFO: Starting critical fixes subagent" | tee -a LLM-CONTEXT/fix-anal/logs/orchestrator.log
```

```
Use the Task tool with:
- subagent_type: "general-purpose"
- description: "Fix critical issues"
- prompt: "Execute /bx_fix_anal_sub_critical to ACTUALLY MODIFY CODE and fix all CRITICAL issues from the plan. This subagent will:

  FOR EACH CRITICAL ISSUE:
  1. MEASURE BEFORE: Capture evidence proving issue exists
     - Run tests 3x to establish baseline
     - Reproduce the issue with evidence
     - Document current behavior

  2. APPLY FIX: Actually modify the code
     - Implement root cause fix (no symptom patching)
     - Make minimal, focused changes
     - Follow fix strategy from plan

  3. VERIFY AFTER: Run tests 3x to detect flaky tests
     - Compare before/after test results
     - Check for regressions
     - Verify issue is actually fixed

  4. KEEP OR REVERT:
     - If tests pass 3x AND metrics improve: git commit the fix
     - If tests fail OR metrics regress: git revert immediately
     - Document decision with evidence

  5. SAVE EVIDENCE:
     - Before/after test results
     - Git commits created
     - Files modified
     - Evidence of improvement

  CRITICAL PRINCIPLES:
  - ACTUALLY MODIFY CODE (don't just recommend)
  - RUN TESTS 3X to detect flaky tests
  - COMPARE BEFORE/AFTER with evidence
  - REVERT if evidence shows regression
  - COMMIT successful fixes to git

  Save all evidence to LLM-CONTEXT/fix-anal/critical/

  Return:
  - Number of critical issues ACTUALLY FIXED (with git commits)
  - Evidence files created (before/after comparisons)
  - Git commits created for successful fixes
  - Issues reverted due to test failures"
```

**Wait for critical fixes to complete before proceeding.**

**STOP if critical fixes fail** - Do not proceed to quality fixes if critical issues remain.

### Step 5.5: Check Critical Fix Status

After critical fixes complete, verify that they succeeded before proceeding to quality fixes:

```bash
# Check critical fix status
if [ ! -f "LLM-CONTEXT/fix-anal/critical/status.txt" ]; then
    log_error "Critical fix status not found - critical fixes must be run before quality fixes"
    echo "ERROR: Critical fix status not found"
    echo "Critical fixes must be run before quality fixes"
    exit 1
fi

CRITICAL_STATUS=$(cat LLM-CONTEXT/fix-anal/critical/status.txt)

if [ "$CRITICAL_STATUS" != "SUCCESS" ]; then
    log_error "Critical fixes failed with status: $CRITICAL_STATUS"
    echo "ERROR: Critical fixes failed with status: $CRITICAL_STATUS"
    echo "Cannot proceed to quality fixes while critical issues remain"
    echo ""
    echo "Review critical fix results:"
    log_error "Critical fixes failed - cannot proceed to quality improvements"
    echo "  - LLM-CONTEXT/fix-anal/critical/critical_summary.md"
    echo "  - LLM-CONTEXT/fix-anal/critical/test_results.txt"
    echo "  - LLM-CONTEXT/fix-anal/critical/security_fixes.log"
    echo "  - LLM-CONTEXT/fix-anal/critical/test_fixes.log"
    echo "  - Logs: LLM-CONTEXT/fix-anal/logs/critical.log"
    echo ""
    echo "Fix critical issues before proceeding to quality improvements"
    exit 1
fi

log_info "Critical fixes status: SUCCESS - proceeding to quality fixes"
echo "✓ Critical fixes status: SUCCESS - proceeding to quality fixes"
```

**STOP if critical status is not SUCCESS.** Quality and documentation fixes should only proceed after critical issues are resolved.

### Step 6: Fix Quality Issues

If critical fixes succeeded and user approved quality fixes, log the start:

```bash
echo "[$(date -Iseconds)] INFO: Starting quality fixes subagent" | tee -a LLM-CONTEXT/fix-anal/logs/orchestrator.log
```

```
Use the Task tool with:
- subagent_type: "general-purpose"
- description: "Fix quality issues"
- prompt: "Execute /bx_fix_anal_sub_quality to ACTUALLY MODIFY CODE and fix all quality issues from the plan. This subagent will:

  FOR EACH QUALITY ISSUE:
  1. MEASURE BEFORE: Capture evidence of quality problem
     - Run tests 3x to establish baseline
     - Measure complexity, line count, duplication
     - Document current metrics

  2. APPLY FIX: Actually refactor the code
     - Refactor to clean architecture
     - Extract clear, single-purpose functions
     - Eliminate duplication
     - Follow fix strategy from plan

  3. VERIFY AFTER: Run tests 3x to detect regressions
     - Compare before/after test results
     - Measure complexity improvement
     - Verify no functionality broken

  4. KEEP OR REVERT:
     - If tests pass 3x AND quality improves: git commit the fix
     - If tests fail OR quality regresses: git revert immediately
     - Document decision with evidence

  5. SAVE EVIDENCE:
     - Before/after complexity metrics
     - Before/after line counts
     - Git commits created
     - Test results (3x runs)

  QUALITY PRINCIPLES:
  - ACTUALLY MODIFY CODE (don't just recommend)
  - RUN TESTS 3X after each refactoring
  - MEASURE COMPLEXITY before/after
  - REVERT if tests fail
  - COMMIT successful refactorings to git

  QUALITY STANDARDS:
  - No functions >50 lines
  - No complexity >10
  - No code duplication
  - Clear separation of concerns

  Save all evidence to LLM-CONTEXT/fix-anal/quality/

  Return:
  - Number of functions ACTUALLY REFACTORED (with git commits)
  - Evidence files created (before/after metrics)
  - Git commits created for successful refactorings
  - Refactorings reverted due to test failures"
```

**Wait for quality fixes to complete before proceeding.**

### Step 6.5: Check Quality Fix Status

After quality fixes complete, verify that they succeeded before proceeding to test refactoring:

```bash
# Check quality fix status
if [ ! -f "LLM-CONTEXT/fix-anal/quality/status.txt" ]; then
    log_error "Quality fix status not found - quality fixes must be run before test refactoring"
    echo "ERROR: Quality fix status not found"
    echo "Quality fixes must be run before test refactoring"
    exit 1
fi

QUALITY_STATUS=$(cat LLM-CONTEXT/fix-anal/quality/status.txt)

if [ "$QUALITY_STATUS" != "SUCCESS" ]; then
    log_error "Quality fixes failed with status: $QUALITY_STATUS"
    echo "ERROR: Quality fixes failed with status: $QUALITY_STATUS"
    echo "Cannot proceed to test refactoring while quality issues remain"
    echo ""
    echo "Review quality fix results:"
    log_error "Quality fixes failed - cannot proceed to test refactoring"
    echo "  - LLM-CONTEXT/fix-anal/quality/quality_summary.md"
    echo "  - LLM-CONTEXT/fix-anal/quality/refactoring_applied.log"
    echo "  - LLM-CONTEXT/fix-anal/quality/complexity_improved.log"
    echo "  - Logs: LLM-CONTEXT/fix-anal/logs/quality.log"
    echo ""
    echo "Fix quality issues before proceeding to test refactoring"
    exit 1
fi

log_info "Quality fixes status: SUCCESS - proceeding to test refactoring"
echo "✓ Quality fixes status: SUCCESS - proceeding to test refactoring"
```

**STOP if quality status is not SUCCESS.** Test refactoring should only proceed after code quality is improved.

### Step 6.6: Refactor Test Suite

If quality fixes succeeded and user approved quality fixes (test refactoring is part of quality), log the start:

```bash
echo "[$(date -Iseconds)] INFO: Starting test refactoring subagent" | tee -a LLM-CONTEXT/fix-anal/logs/orchestrator.log
```

```
Use the Task tool with:
- subagent_type: "general-purpose"
- description: "Refactor test suite"
- prompt: "Execute /bx_fix_anal_sub_refactor_tests to ACTUALLY MODIFY TEST CODE according to clean architecture principles. This subagent will:

  FOR EACH TEST QUALITY ISSUE:
  1. MEASURE BEFORE: Capture evidence of test quality problems
     - Run tests 3x to establish baseline
     - Identify tests with poor names
     - Detect stub-only tests (mock-heavy, no real behavior)
     - Find tests needing OS-specific markers
     - Measure coverage gaps
     - Detect tests checking multiple behaviors
     - Document current test metrics

  2. APPLY FIX: Actually refactor the tests
     - Rename tests to plain English descriptions
     - Add OS-specific markers (@pytest.mark.skipif)
     - Mark stub tests with TODO comments
     - Add test stubs for coverage gaps
     - Follow fix strategy from plan

  3. VERIFY AFTER: Run tests 3x to detect regressions
     - Compare before/after test results
     - Verify all tests still pass
     - Measure coverage improvement
     - Verify no functionality broken

  4. KEEP OR REVERT:
     - If tests pass 3x AND quality improves: git commit the fix
     - If tests fail OR quality regresses: git revert immediately
     - Document decision with evidence

  5. SAVE EVIDENCE:
     - Before/after test names
     - Before/after coverage metrics
     - Git commits created
     - Test results (3x runs)
     - Tests renamed, marked, or added

  TEST REFACTORING PRINCIPLES:
  - ACTUALLY MODIFY TEST CODE (don't just recommend)
  - RUN TESTS 3X after each refactoring
  - RENAME tests to plain English (describe behavior, not implementation)
  - ADD OS markers where tests are platform-specific
  - MARK stub tests for future replacement with integration tests
  - ADD stubs for coverage gaps
  - REVERT if tests fail
  - COMMIT successful refactorings to git

  TEST QUALITY STANDARDS:
  - Test names in plain English (not test_method_name)
  - OS-specific tests properly marked
  - Stub tests marked with TODO comments
  - High coverage (>80% for core code)
  - Tests check single behavior only
  - Prefer integration tests over mocks

  Save all evidence to LLM-CONTEXT/fix-anal/refactor-tests/

  Return:
  - Number of tests ACTUALLY REFACTORED (with git commits)
  - Evidence files created (before/after test names, coverage)
  - Git commits created for successful refactorings
  - Test refactorings reverted due to test failures"
```

**Wait for test refactoring to complete before proceeding.**

### Step 6.7: Check Test Refactoring Status

After test refactoring completes, verify that it succeeded before proceeding to cache optimization:

```bash
# Check test refactoring status
if [ ! -f "LLM-CONTEXT/fix-anal/refactor-tests/status.txt" ]; then
    log_error "Test refactoring status not found - test refactoring must be run before cache optimization"
    echo "ERROR: Test refactoring status not found"
    echo "Test refactoring must be run before cache optimization"
    exit 1
fi

TEST_REFACTOR_STATUS=$(cat LLM-CONTEXT/fix-anal/refactor-tests/status.txt)

if [ "$TEST_REFACTOR_STATUS" != "SUCCESS" ]; then
    log_error "Test refactoring failed with status: $TEST_REFACTOR_STATUS"
    echo "ERROR: Test refactoring failed with status: $TEST_REFACTOR_STATUS"
    log_error "Test refactoring failed - cannot proceed to cache optimization"
    echo "Cannot proceed to cache optimization while test quality issues remain"
    echo ""
    echo "Review test refactoring results:"
    echo "  - LLM-CONTEXT/fix-anal/refactor-tests/refactor_tests_summary.md"
    echo "  - Logs: LLM-CONTEXT/fix-anal/logs/refactor_tests.log"
    echo ""
    echo "Fix test quality issues before proceeding to cache optimization"
    exit 1
fi

log_info "Test refactoring status: SUCCESS - proceeding to cache optimization"
echo "✓ Test refactoring status: SUCCESS - proceeding to cache optimization"
```

**STOP if test refactoring status is not SUCCESS.** Cache optimization should only proceed after test quality is improved.

### Step 6.8: Apply Cache Optimization

If test refactoring succeeded and user approved quality fixes (cache optimization is part of performance quality), log the start:

```bash
echo "[$(date -Iseconds)] INFO: Starting cache optimization subagent" | tee -a LLM-CONTEXT/fix-anal/logs/orchestrator.log
```

```
Use the Task tool with:
- subagent_type: "general-purpose"
- description: "Apply cache optimization"
- prompt: "Execute /bx_fix_anal_sub_cache to ACTUALLY MODIFY CODE and apply caching to functions identified by cache review. This subagent will:

  FOR EACH CACHE CANDIDATE:
  1. MEASURE BEFORE: Capture baseline performance
     - Run tests 3x to establish baseline
     - Record test suite execution time
     - Document current performance

  2. APPLY CACHE: Actually add @lru_cache decorator
     - Add functools import if needed
     - Add @lru_cache(maxsize=$DEFAULT_CACHE_SIZE) decorator
     - Follow fix strategy from cache review

  3. VERIFY AFTER: Run tests 3x with caching
     - Compare before/after test results
     - Measure performance improvement
     - Verify no functionality broken

  4. CHECK CRITERIA:
     - Tests must pass 3/3 runs
     - Performance improvement must be >$MIN_IMPROVEMENT_PERCENT%
     - If criteria met: git commit the change
     - If criteria NOT met: git revert immediately

  5. SAVE EVIDENCE:
     - Before/after performance metrics
     - Test results (3x runs)
     - Git commits created
     - Functions optimized

  CACHE OPTIMIZATION PRINCIPLES:
  - ACTUALLY MODIFY CODE (add decorators)
  - RUN TESTS 3X after each cache addition
  - MEASURE PERFORMANCE before/after with REAL test suite
  - NEVER use synthetic benchmarks
  - REVERT if tests fail OR improvement <$MIN_IMPROVEMENT_PERCENT%
  - COMMIT successful optimizations to git

  CACHE OPTIMIZATION STANDARDS:
  - Tests must pass 3/3 runs
  - Performance improvement >$MIN_IMPROVEMENT_PERCENT% required
  - Only pure functions (deterministic, no side effects)
  - Verify with real test data, never synthetic

  Save all evidence to LLM-CONTEXT/fix-anal/cache/

  Return:
  - Number of functions ACTUALLY CACHED (with git commits)
  - Evidence files created (before/after performance)
  - Git commits created for successful caching
  - Cache additions reverted due to test failures or insufficient improvement"
```

**Wait for cache optimization to complete before proceeding.**

### Step 7: Fix Documentation Issues

If cache optimization completed and user approved doc fixes, log the start:

```bash
echo "[$(date -Iseconds)] INFO: Starting documentation fixes subagent" | tee -a LLM-CONTEXT/fix-anal/logs/orchestrator.log
```

```
Use the Task tool with:
- subagent_type: "general-purpose"
- description: "Fix documentation issues"
- prompt: "Execute /bx_fix_anal_sub_docs to ACTUALLY MODIFY CODE and fix all documentation issues from the plan. This subagent will:

  FOR EACH DOCUMENTATION ISSUE:
  1. MEASURE BEFORE: Capture evidence of missing docs
     - Run tests 3x to establish baseline
     - Count missing docstrings
     - Document current coverage

  2. APPLY FIX: Actually add documentation
     - Add comprehensive docstrings
     - Document parameters and return values
     - Include examples where helpful
     - Follow fix strategy from plan

  3. VERIFY AFTER: Run tests 3x to ensure docs don't break anything
     - Compare before/after test results
     - Measure documentation coverage improvement
     - Verify syntax is valid

  4. KEEP OR REVERT:
     - If tests pass 3x AND coverage improves: git commit the fix
     - If tests fail OR docs invalid: git revert immediately
     - Document decision with evidence

  5. SAVE EVIDENCE:
     - Before/after documentation coverage
     - Git commits created
     - Test results (3x runs)
     - Files modified

  DOCUMENTATION PRINCIPLES:
  - ACTUALLY MODIFY CODE (don't just recommend)
  - RUN TESTS 3X to verify docs don't break code
  - MEASURE COVERAGE before/after
  - REVERT if tests fail
  - COMMIT successful doc additions to git

  DOCUMENTATION STANDARDS:
  - Every public function has docstring
  - All parameters documented
  - Return values documented
  - Examples for complex APIs

  Save all evidence to LLM-CONTEXT/fix-anal/docs/

  Return:
  - Number of docstrings ACTUALLY ADDED (with git commits)
  - Evidence files created (before/after coverage)
  - Git commits created for successful doc additions
  - Doc additions reverted due to syntax errors"
```

**Wait for documentation fixes to complete before proceeding.**

### Step 8: Comprehensive Verification

After all fixes are applied, log the start and verify everything works:

```bash
echo "[$(date -Iseconds)] INFO: Starting verification subagent" | tee -a LLM-CONTEXT/fix-anal/logs/orchestrator.log
```

```
Use the Task tool with:
- subagent_type: "general-purpose"
- description: "Verify all fixes"
- prompt: "Execute /bx_fix_anal_sub_verify to comprehensively verify all fixes with EVIDENCE-BASED VERIFICATION. This includes:

  1. RUN FULL TEST SUITE 3X (detect flaky tests)
     - Run tests 3 times to detect intermittent failures
     - Compare with baseline test runs (from Step 0.5)
     - Identify any new flaky tests introduced
     - Document test stability

  2. COMPARE BEFORE/AFTER METRICS
     - Code coverage: baseline vs after fixes
     - Security scan: vulnerabilities before vs after
     - Complexity: functions before vs after
     - Test stability: flaky tests detected

  3. VERIFY IMPROVEMENTS
     - All critical issues fixed (evidence required)
     - Quality metrics improved or unchanged
     - No new test failures introduced
     - No regressions detected

  4. DETECT FLAKY TESTS
     - Compare 3 test runs for consistency
     - Flag tests that pass sometimes, fail sometimes
     - Document flaky test patterns

  5. FAIL IF METRICS REGRESS
     - If coverage decreased: FAIL
     - If security vulnerabilities increased: FAIL
     - If test failures increased: FAIL
     - If complexity increased: FAIL

  VERIFICATION PRINCIPLES:
  - RUN TESTS 3X (not once) to detect flaky tests
  - COMPARE with baseline metrics from Step 0.5
  - FAIL FAST if metrics regress
  - Trust evidence, not assumptions
  - Document all flaky tests found

  Save all verification evidence to LLM-CONTEXT/fix-anal/verification/

  Return:
  - Test results (3x runs, pass/fail, flaky tests detected)
  - Before/after metrics comparison
  - Security vulnerabilities fixed
  - Quality improvements verified
  - Overall verification status (SUCCESS if improved, FAILED if regressed)"
```

**Wait for verification to complete before proceeding.**

**CRITICAL:** If verification fails, document failures and DO NOT proceed to final report.

### Step 8.5: Check Verification Status

After verification completes, check that it succeeded before generating the final report:

```bash
# Check verification status
if [ ! -f "LLM-CONTEXT/fix-anal/verification/status.txt" ]; then
    log_error "Verification was not run - cannot generate final report without verification"
    echo "ERROR: Verification was not run"
    echo "Cannot generate final report without verification"
    exit 1
fi

VERIFICATION_STATUS=$(cat LLM-CONTEXT/fix-anal/verification/status.txt)

if [ "$VERIFICATION_STATUS" != "SUCCESS" ]; then
    log_error "Verification failed with status: $VERIFICATION_STATUS"
    echo "ERROR: Verification failed with status: $VERIFICATION_STATUS"
    echo "Cannot generate final report when verification has not passed"
    log_error "Verification failed - fix issues before generating report"
    echo ""
    echo "Review verification results:"
    echo "  - LLM-CONTEXT/fix-anal/verification/verification_report.md"
    echo "  - LLM-CONTEXT/fix-anal/verification/test_results.txt"
    echo "  - LLM-CONTEXT/fix-anal/verification/security_scan_after.txt"
    echo "  - Logs: LLM-CONTEXT/fix-anal/logs/verify.log"
    echo ""
    echo "Fix the issues identified in verification before generating report"
    exit 1
fi

log_info "Verification status: SUCCESS - proceeding to final report"
echo "✓ Verification status: SUCCESS - proceeding to final report"
```

**STOP if verification status is not SUCCESS.** Do not generate the final report if verification has failed.

### Step 9: Generate Fix Report

Before compiling the fix report, log the start:

```bash
echo "[$(date -Iseconds)] INFO: Starting fix report generation subagent" | tee -a LLM-CONTEXT/fix-anal/logs/orchestrator.log
```

Compile comprehensive report of ACTUAL fixes applied:

```
Use the Task tool with:
- subagent_type: "general-purpose"
- description: "Generate fix report"
- prompt: "Execute /bx_fix_anal_sub_report to compile comprehensive report of ACTUAL FIXES APPLIED from:
  - LLM-CONTEXT/fix-anal/plan/fix_plan.md
  - LLM-CONTEXT/fix-anal/critical/critical_summary.md
  - LLM-CONTEXT/fix-anal/quality/quality_summary.md
  - LLM-CONTEXT/fix-anal/refactor-tests/refactor_tests_summary.md
  - LLM-CONTEXT/fix-anal/cache/cache_fix_summary.md
  - LLM-CONTEXT/fix-anal/docs/docs_summary.md
  - LLM-CONTEXT/fix-anal/verification/verification_report.md
  - LLM-CONTEXT/fix-anal/metrics/ (baseline and after metrics)

  Generate FACTUAL report including:
  1. Executive summary (WHAT WAS ACTUALLY FIXED, not recommended)
  2. Git commits created (list all commits with hashes)
  3. Files modified (actual file changes made)
  4. Evidence of improvement (before/after metrics)
  5. Fixes reverted (due to test failures)
  6. Flaky tests detected (from 3x test runs)
  7. Remaining issues (if any)
  8. Metrics comparison:
     - Test results: baseline vs after (3x runs each)
     - Coverage: baseline vs after
     - Security: vulnerabilities before vs after
     - Complexity: functions before vs after
  9. Recommendation (ready for approval / needs more work)

  REPORT PRINCIPLES:
  - Report ACTUAL fixes applied (code modified, not recommendations)
  - Include git commit hashes as proof
  - Show before/after evidence for every fix
  - Document any fixes that were reverted
  - List flaky tests detected during verification

  Save final report to LLM-CONTEXT/fix-anal/report/fix_report.md

  Return:
  - Approval status
  - Number of git commits created
  - Location of final report"
```

**Wait for report generation to complete before proceeding.**

### Step 9.5: Final Evidence Validation

**CRITICAL: Verify all evidence exists and is complete before declaring success:**

```bash
echo "=== FINAL EVIDENCE VALIDATION ==="
echo "Verifying all evidence files exist and metrics improved..."
echo ""

# Track validation failures
VALIDATION_FAILED=0

# 1. Verify baseline metrics exist
echo "1. Checking baseline metrics..."
if [ ! -f "LLM-CONTEXT/fix-anal/metrics/baseline_tests_run1.txt" ] || \
   [ ! -f "LLM-CONTEXT/fix-anal/metrics/baseline_tests_run2.txt" ] || \
   [ ! -f "LLM-CONTEXT/fix-anal/metrics/baseline_tests_run3.txt" ]; then
    echo "✗ FAILED: Baseline test runs missing"
    VALIDATION_FAILED=1
else
    echo "✓ Baseline test runs found"
fi

# 2. Verify after-fix metrics exist
echo "2. Checking after-fix metrics..."
if [ ! -f "LLM-CONTEXT/fix-anal/verification/test_results_run1.txt" ] || \
   [ ! -f "LLM-CONTEXT/fix-anal/verification/test_results_run2.txt" ] || \
   [ ! -f "LLM-CONTEXT/fix-anal/verification/test_results_run3.txt" ]; then
    echo "✗ FAILED: After-fix test runs missing"
    VALIDATION_FAILED=1
else
    echo "✓ After-fix test runs found"
fi

# 3. Verify git commits were created for fixes
echo "3. Checking git commits..."
if [ ! -f "LLM-CONTEXT/fix-anal/report/git_commits.txt" ]; then
    echo "⚠ WARNING: No git commits file found"
    echo "  (This is OK if no fixes were needed)"
else
    COMMIT_COUNT=$(wc -l < LLM-CONTEXT/fix-anal/report/git_commits.txt)
    echo "✓ Git commits file found ($COMMIT_COUNT commits)"
fi

# 4. Verify flaky test detection was performed
echo "4. Checking flaky test detection..."
if [ ! -f "LLM-CONTEXT/fix-anal/verification/flaky_tests.txt" ]; then
    echo "✗ FAILED: Flaky test detection not performed"
    VALIDATION_FAILED=1
else
    FLAKY_COUNT=$(wc -l < LLM-CONTEXT/fix-anal/verification/flaky_tests.txt)
    if [ "$FLAKY_COUNT" -gt 0 ]; then
        echo "⚠ WARNING: $FLAKY_COUNT flaky tests detected"
    else
        echo "✓ No flaky tests detected"
    fi
fi

# 5. Verify metrics comparison exists
echo "5. Checking metrics comparison..."
if [ ! -f "LLM-CONTEXT/fix-anal/verification/metrics_comparison.txt" ]; then
    echo "✗ FAILED: Metrics comparison not performed"
    VALIDATION_FAILED=1
else
    echo "✓ Metrics comparison found"
fi

# 6. Check for evidence of regression
echo "6. Checking for regressions..."
if [ -f "LLM-CONTEXT/fix-anal/verification/regressions_detected.txt" ]; then
    REGRESSION_COUNT=$(wc -l < LLM-CONTEXT/fix-anal/verification/regressions_detected.txt)
    if [ "$REGRESSION_COUNT" -gt 0 ]; then
        echo "✗ FAILED: $REGRESSION_COUNT regressions detected"
        VALIDATION_FAILED=1
    else
        echo "✓ No regressions detected"
    fi
else
    echo "✓ No regressions file (no regressions)"
fi

echo ""

# Final validation result
if [ "$VALIDATION_FAILED" -eq 1 ]; then
    log_error "Evidence validation failed - incomplete or shows regressions"
    echo "════════════════════════════════════════"
    echo "✗ EVIDENCE VALIDATION FAILED"
    echo "════════════════════════════════════════"
    echo ""
    echo "Evidence is incomplete or shows regressions."
    echo "Cannot declare fixes successful without complete evidence."
    echo ""
    echo "Review missing evidence above and ensure all verification steps completed."
    exit 1
else
    echo "════════════════════════════════════════"
    echo "✓ EVIDENCE VALIDATION PASSED"
    echo "════════════════════════════════════════"
    echo ""
    echo "All evidence files present and verified."
    echo "Proceeding to final report."
fi
```

**STOP if evidence validation fails** - Do not present results if evidence is incomplete.

### Step 10: Analyze Command Logs

Before delegating to the log analyzer subagent, log the start:

```bash
echo "[$(date -Iseconds)] INFO: Starting log analysis subagent" | tee -a LLM-CONTEXT/fix-anal/logs/orchestrator.log
```

Delegate to the **Log Analyzer Agent** to diagnose any errors:

```
Use the Task tool with:
- subagent_type: "general-purpose"
- description: "Analyze fix logs"
- prompt: "Execute /bx_fix_anal_sub_analyze_command_logs to analyze all fix command and subcommand logs.

  The analyzer will:
  1. Scan all log files in LLM-CONTEXT/fix-anal/logs/
  2. Identify errors, warnings, test failures, git errors
  3. Check status of all subagents (plan, critical, quality, refactor-tests, cache, docs, verification, report)
  4. Classify errors by type (test failure, git error, syntax error, timeout, permission, missing resources)
  5. Analyze git commits made during fixes
  6. Track files modified during fixes
  7. Generate comprehensive error report with root causes and solutions

  Output:
  - LLM-CONTEXT/fix-anal/logs/log_analysis_report.md - Human-readable analysis
  - LLM-CONTEXT/fix-anal/logs/error_summary.json - Structured error data
  - LLM-CONTEXT/fix-anal/logs/recommendations.txt - Actionable solutions

  NOTE: This step is non-blocking. Errors in log analysis should not fail the fix.
  Return summary of errors found, git commits, files modified, and recommendations."
```

**Wait for log analysis to complete before proceeding.**

After the log analysis Task completes, log the completion:

```bash
echo "[$(date -Iseconds)] INFO: Log analysis completed" | tee -a LLM-CONTEXT/fix-anal/logs/orchestrator.log
echo "[$(date -Iseconds)] INFO: Fix orchestration completed successfully" | tee -a LLM-CONTEXT/fix-anal/logs/orchestrator.log
```

### Step 11: Present Results

Present the final fix report to the user with:
- Executive summary of ACTUAL fixes applied (not recommendations)
- Git commits created (with hashes)
- Files modified
- Verification status (✓ All Tests Pass 3x | ✗ Regressions Detected)
- Metrics improvements (before/after comparison with evidence)
- Flaky tests detected (from 3x runs)
- Next steps (push commits, run review again, etc.)
- Location of all fix artifacts and evidence in LLM-CONTEXT/fix-anal/
- **Log analysis summary** (if errors were detected)

```bash
# Log completion
log_info "Fix orchestrator completed successfully"
log_info "Logs available at: /media/srv-main-softdev/projects/LLM-CONTEXT/fix-anal/logs/orchestrator.log"
log_info "Log analysis available at: /media/srv-main-softdev/projects/LLM-CONTEXT/fix-anal/logs/log_analysis_report.md"
echo ""
echo "Detailed logs available at:"
echo "  - Orchestrator: LLM-CONTEXT/fix-anal/logs/orchestrator.log"
echo "  - Planning: LLM-CONTEXT/fix-anal/logs/plan.log"
echo "  - Critical: LLM-CONTEXT/fix-anal/logs/critical.log"
echo "  - Quality: LLM-CONTEXT/fix-anal/logs/quality.log"
echo "  - Test Refactoring: LLM-CONTEXT/fix-anal/logs/refactor_tests.log"
echo "  - Cache Optimization: LLM-CONTEXT/fix-anal/logs/cache.log"
echo "  - Docs: LLM-CONTEXT/fix-anal/logs/docs.log"
echo "  - Verification: LLM-CONTEXT/fix-anal/logs/verify.log"
echo "  - Report: LLM-CONTEXT/fix-anal/logs/report.log"
echo "  - Log Analysis: LLM-CONTEXT/fix-anal/logs/log_analysis_report.md"
```

## Reviewer Mindset for Fixes

Maintain this mindset throughout all fixes:

- **Pedantic & Thorough:** Every fix must be complete and correct
- **Zero Trust:** Verify every fix works with tests and evidence
- **Quality First:** Refactor to clean architecture, don't just patch
- **Root Cause Focus:** Fix underlying problems, not symptoms
- **Evidence-Based:** Prove every fix works with concrete measurements
- **Perfectionist Standard:** Accept nothing less than perfect implementation

## Evidence-Based Fixing Protocol

**The Measure-Fix-Verify-Commit Cycle:**

Every fix follows this evidence-based cycle:

1. **MEASURE BEFORE (Baseline Evidence)**
   - Run tests 3x to detect flaky tests
   - Capture metrics (coverage, complexity, security)
   - Document current behavior
   - Save all evidence files

2. **FIX (Actual Code Modification)**
   - Actually modify the code (not recommendations)
   - Fix root causes, not symptoms
   - Make minimal, focused changes
   - Follow clean architecture principles

3. **VERIFY AFTER (Run Tests 3x)**
   - Run tests 3 times to detect flaky tests
   - Compare with baseline metrics
   - Check for regressions
   - Verify improvement with evidence

4. **KEEP OR REVERT (Evidence-Based Decision)**
   - If tests pass 3x AND metrics improve: `git commit`
   - If tests fail OR metrics regress: `git revert`
   - Document decision with evidence
   - Never keep unproven fixes

5. **COMMIT PROVEN FIXES**
   - Git commit successful fixes with clear messages
   - Save commit hashes as proof
   - Document files modified
   - Create audit trail

**Why 3x Test Runs?**
- Detects flaky/intermittent test failures
- Ensures fixes are reliable, not lucky
- Catches race conditions and timing issues
- Provides confidence in stability

**Why Evidence Files?**
- Proof that fixes actually worked
- Objective before/after comparison
- Audit trail for review
- Enables rollback if needed

## Fix Principles

**ALWAYS during fixes:**
- **RUN TESTS 3X AFTER EACH FIX** - Detect flaky tests, verify no regressions
- **FIX ROOT CAUSES ONLY** - No symptom patching
- **REFACTOR RUTHLESSLY** - Make code clean and inevitable
- **VERIFY WITH EVIDENCE** - Run tests 3x, measure, compare, prove it works
- **COMMIT PROVEN FIXES** - Git commit successful fixes, revert failures
- **DOCUMENT CHANGES** - Clear commit messages, evidence files, change logs
- **NO FUNCTIONS >50 LINES** - Refactor if necessary
- **NO COMPLEXITY >10** - Simplify if necessary
- **USE REAL TEST DATA** - Never rely on synthetic data
- **SAVE ALL EVIDENCE** - Before/after metrics, test results, git commits

**NEVER during fixes:**
- **NEVER skip 3x test runs** - Always verify stability
- **NEVER skip verification** - Always run tests and compare metrics
- **NEVER patch symptoms** - Always fix root causes
- **NEVER trust without evidence** - Always verify with before/after comparison
- **NEVER keep unproven fixes** - Revert if tests fail or metrics regress
- **NEVER compromise quality** - Maintain perfectionist standards
- **NEVER add technical debt** - Fix properly or not at all
- **NEVER assume success** - Require evidence of improvement

## Fix Categories & Priorities

### CRITICAL (Must Fix - Blockers)
1. **Security vulnerabilities** - HIGH/CRITICAL severity
2. **Test failures** - Tests that fail after dependency updates
3. **Runtime errors** - Code that crashes or throws exceptions
4. **Data corruption risks** - Code that could corrupt user data

### MAJOR (Should Fix - Important)
1. **Functions >50 lines** - Refactor to smaller, focused functions
2. **Complex functions** - Flatten nesting, extract logic
3. **Code duplication** - Extract to shared functions
4. **Architecture issues** - God objects, tight coupling
5. **MEDIUM security issues** - Less severe vulnerabilities

### MINOR (Nice to Fix - Improvements)
1. **Missing docstrings** - Add comprehensive documentation
2. **Brief docstrings** - Expand for clarity
3. **Missing README sections** - Complete project documentation
4. **Code style issues** - Linting warnings, formatting

## Default Behavior

**By default, fix ALL issues** identified in the review, starting with CRITICAL and proceeding through MAJOR to MINOR.

User can choose selective fixing via the approval step.

## Key Principles

- **ALWAYS VERIFY FIXES** - Run tests after every change
- **ALWAYS FIX ROOT CAUSES** - Investigate deeply, fix properly
- **ALWAYS MAINTAIN QUALITY** - No compromise on standards
- **ALWAYS USE TEST DATA** - Verify with real scenarios
- **ALWAYS DOCUMENT CHANGES** - Clear, thorough commit messages
- **NEVER PATCH SYMPTOMS** - Find and fix the real problem
- **NEVER SKIP VERIFICATION** - Evidence required for every fix

## Sub-Agent Architecture

This orchestrator delegates to specialized fix sub-agents that ACTUALLY MODIFY CODE:

1. **bx_fix_anal_sub_plan** - Parse findings, create actionable plan with evidence requirements
2. **bx_fix_anal_sub_critical** - Actually fix security/test issues, verify 3x, commit or revert
3. **bx_fix_anal_sub_quality** - Actually refactor code, verify 3x, commit or revert
4. **bx_fix_anal_sub_refactor_tests** - Actually refactor test suite, verify 3x, commit or revert
5. **bx_fix_anal_sub_cache** - Actually apply caching, verify 3x, commit or revert
6. **bx_fix_anal_sub_docs** - Actually add documentation, verify 3x, commit or revert
7. **bx_fix_anal_sub_verify** - Run tests 3x, compare metrics, detect flaky tests
8. **bx_fix_anal_sub_report** - Compile report of ACTUAL fixes with git commits

Each sub-agent:
- **Actually modifies code** (not just recommendations)
- **Runs tests 3x** to detect flaky tests
- **Compares before/after metrics** with evidence
- **Git commits successful fixes** with clear messages
- **Git reverts failed fixes** immediately
- Maintains the reviewer mindset (pedantic, thorough, evidence-based)
- Reports back structured results with evidence
- Saves all artifacts and evidence to LLM-CONTEXT/fix-anal/<subagent>/

## Integration Protocol

**All subagents MUST follow this integration protocol for orchestration to work correctly:**

### Required Outputs

Every subagent must create the following files in its designated subdirectory:

1. **status.txt** - Machine-readable status indicator
   - Content: Single line with "SUCCESS" or "FAILED"
   - Location: `LLM-CONTEXT/fix-anal/<subagent>/status.txt`
   - Purpose: Orchestrator uses this to determine if workflow should continue
   - Example: `echo "SUCCESS" > LLM-CONTEXT/fix-anal/critical/status.txt`

2. **<subagent>_summary.md** - Human-readable summary report
   - Content: Comprehensive markdown report of all work performed
   - Location: `LLM-CONTEXT/fix-anal/<subagent>/<subagent>_summary.md`
   - Purpose: Provides detailed results for final report compilation
   - Examples:
     - `LLM-CONTEXT/fix-anal/critical/critical_summary.md`
     - `LLM-CONTEXT/fix-anal/quality/quality_summary.md`
     - `LLM-CONTEXT/fix-anal/docs/docs_summary.md`
     - `LLM-CONTEXT/fix-anal/verification/verification_report.md`

3. **Additional logs** - Category-specific detailed logs
   - Content: Detailed operation logs for debugging and auditing
   - Location: `LLM-CONTEXT/fix-anal/<subagent>/*.log`
   - Purpose: Provides detailed audit trail
   - Examples:
     - `security_fixes.log`, `test_fixes.log` (critical)
     - `long_functions.log`, `complexity.log`, `duplication.log` (quality)
     - `missing_docstrings.log`, `missing_params.log` (docs)

### Required Behaviors

1. **Exit Codes**
   - Exit with code `0` on success
   - Exit with code `1` on failure
   - Orchestrator checks exit codes to detect failures

2. **Status File Format**
   - Status must be exactly "SUCCESS" or "FAILED" (all caps, no extra whitespace)
   - Written at the END of subagent execution
   - Initial status can be "IN_PROGRESS" while running

3. **Directory Structure**
   - All outputs MUST go into designated subdirectory:
     - `LLM-CONTEXT/fix-anal/plan/` for planner
     - `LLM-CONTEXT/fix-anal/critical/` for critical fixes
     - `LLM-CONTEXT/fix-anal/quality/` for quality fixes
     - `LLM-CONTEXT/fix-anal/refactor-tests/` for test refactoring
     - `LLM-CONTEXT/fix-anal/cache/` for cache optimization
     - `LLM-CONTEXT/fix-anal/docs/` for documentation fixes
     - `LLM-CONTEXT/fix-anal/verification/` for verification
     - `LLM-CONTEXT/fix-anal/report/` for final report

4. **Error Handling**
   - On error, write "FAILED" to status.txt
   - Include error details in summary report
   - Exit with code 1
   - Do NOT leave partial/incomplete outputs

5. **Summary Report Format**
   - Must include:
     - Executive summary section
     - Detailed findings/actions taken
     - Statistics and counts
     - Status indication
   - Use markdown formatting
   - Include timestamps

### Integration Checklist

Before a subagent is considered complete, verify:

- [ ] status.txt created with "SUCCESS" or "FAILED"
- [ ] *_summary.md created with comprehensive results
- [ ] All detailed logs saved to correct subdirectory
- [ ] Exit code matches status (0 for SUCCESS, 1 for FAILED)
- [ ] No outputs written outside designated subdirectory
- [ ] Error messages logged if status is FAILED
- [ ] Timestamps included in all reports

### Why This Protocol Matters

This protocol enables:
- **Orchestration**: Main command knows when to proceed vs stop
- **Debugging**: Clear audit trail when things go wrong
- **Reporting**: Final report can compile all subagent outputs
- **Reliability**: Standardized interface reduces integration bugs
- **Automation**: Scripts can parse status.txt for automation

## File Locations

```
LLM-CONTEXT/fix-anal/
├── fix_metadata.json                      # Fix session metadata
├── metrics/                               # Baseline Metrics (Step 0.5)
│   ├── baseline_tests_run1.txt            # First test run (baseline)
│   ├── baseline_tests_run2.txt            # Second test run (baseline)
│   ├── baseline_tests_run3.txt            # Third test run (baseline)
│   ├── baseline_test_summary.txt          # Summary of baseline runs
│   ├── baseline_coverage.txt              # Coverage before fixes
│   ├── baseline_security.txt              # Security scan before fixes
│   ├── baseline_complexity.txt            # Complexity before fixes
│   └── baseline_maintainability.txt       # Maintainability before fixes
├── plan/                                  # Fix Planning
│   ├── fix_plan.md                        # Actionable fix plan with evidence requirements
│   ├── critical_issues.txt                # CRITICAL issues to fix
│   ├── major_issues.txt                   # MAJOR issues to fix
│   ├── minor_issues.txt                   # MINOR issues to fix
│   └── fix_order.txt                      # Order to apply fixes
├── evidence/                              # Evidence Files (all subagents)
│   ├── critical/                          # Critical fix evidence
│   │   ├── issue_1_before_tests.txt       # Before evidence for issue 1
│   │   ├── issue_1_after_tests.txt        # After evidence for issue 1
│   │   └── issue_1_git_commit.txt         # Git commit for issue 1
│   ├── quality/                           # Quality fix evidence
│   └── docs/                              # Documentation fix evidence
├── critical/                              # Critical Fixes
│   ├── security_fixes.log                 # Security fixes ACTUALLY APPLIED
│   ├── test_fixes.log                     # Test fixes ACTUALLY APPLIED
│   ├── security_fixes_reverted.log        # Fixes reverted due to failures
│   ├── git_commits.txt                    # Git commits created
│   ├── files_modified.txt                 # Files actually modified
│   ├── status.txt                         # SUCCESS or FAILED
│   └── critical_summary.md                # Summary with evidence
├── quality/                               # Quality Fixes
│   ├── refactoring_applied.log            # Refactorings ACTUALLY APPLIED
│   ├── complexity_improved.log            # Complexity improvements
│   ├── refactorings_reverted.log          # Refactorings reverted
│   ├── git_commits.txt                    # Git commits created
│   ├── files_modified.txt                 # Files actually modified
│   ├── before_after_metrics.txt           # Metrics comparison
│   ├── status.txt                         # SUCCESS or FAILED
│   └── quality_summary.md                 # Summary with evidence
├── refactor-tests/                        # Test Refactoring Fixes
│   ├── tests_renamed.log                  # Tests ACTUALLY RENAMED
│   ├── os_markers_added.log               # OS markers ACTUALLY ADDED
│   ├── stubs_marked.log                   # Stub tests marked with TODO
│   ├── coverage_stubs_added.log           # Test stubs for coverage gaps
│   ├── tests_reverted.log                 # Test refactorings reverted
│   ├── git_commits.txt                    # Git commits created
│   ├── files_modified.txt                 # Files actually modified
│   ├── before_after_test_names.txt        # Test names before/after
│   ├── coverage_improvement.txt           # Coverage before/after
│   ├── status.txt                         # SUCCESS or FAILED
│   └── refactor_tests_summary.md          # Summary with evidence
├── cache/                                 # Cache Optimization
│   ├── caching_applied.log                # Functions ACTUALLY CACHED
│   ├── caching_reverted.log               # Cache additions reverted
│   ├── caching_results.json               # Detailed results with metrics
│   ├── git_commits.txt                    # Git commits created
│   ├── files_modified.txt                 # Files actually modified
│   ├── before_after_performance.txt       # Performance before/after
│   ├── status.txt                         # SUCCESS or FAILED
│   └── cache_fix_summary.md               # Summary with evidence
├── docs/                                  # Documentation Fixes
│   ├── docstrings_added.log               # Docstrings ACTUALLY ADDED
│   ├── docs_reverted.log                  # Doc additions reverted
│   ├── git_commits.txt                    # Git commits created
│   ├── files_modified.txt                 # Files actually modified
│   ├── coverage_improvement.txt           # Coverage before/after
│   ├── status.txt                         # SUCCESS or FAILED
│   └── docs_summary.md                    # Summary with evidence
├── verification/                          # Verification
│   ├── test_results_run1.txt              # After-fix test run 1
│   ├── test_results_run2.txt              # After-fix test run 2
│   ├── test_results_run3.txt              # After-fix test run 3
│   ├── flaky_tests.txt                    # Flaky tests detected
│   ├── metrics_comparison.txt             # Before vs after comparison
│   ├── regressions_detected.txt           # Regressions found (if any)
│   ├── security_scan_after.txt            # Security scan after fixes
│   ├── coverage_after.txt                 # Coverage after fixes
│   ├── complexity_after.txt               # Complexity after fixes
│   ├── status.txt                         # SUCCESS or FAILED
│   └── verification_report.md             # Evidence-based verification report
└── report/                                # Final Report
    ├── git_commits.txt                    # All git commits created
    ├── files_modified.txt                 # All files modified
    └── fix_report.md                      # FINAL REPORT with evidence
```

## Usage Examples

### Fix All Issues (Default) - Evidence-Based Workflow

```
User: /bx_fix_anal

Orchestrator:
1. Captures baseline metrics (tests 3x, coverage, security, complexity)
2. Validates review was run
3. Creates actionable fix plan with evidence requirements
4. User approves "Fix all issues"
5. Fixes critical issues:
   - For each issue: measure before, fix code, verify 3x, commit or revert
   - Saves git commits, evidence files, before/after metrics
6. Fixes quality issues:
   - For each refactoring: measure before, refactor, verify 3x, commit or revert
   - Saves complexity improvements, evidence
7. Refactors test suite:
   - For each test issue: measure before, refactor tests, verify 3x, commit or revert
   - Renames tests, adds OS markers, marks stubs, adds coverage stubs
   - Saves test improvements, evidence
8. Applies cache optimization:
   - For each cache candidate: measure before, add @lru_cache, verify 3x, commit or revert
   - Verifies >$MIN_IMPROVEMENT_PERCENT% improvement, tests pass 3x
   - Reverts if criteria not met
   - Saves performance improvements, evidence
9. Fixes documentation issues:
   - For each doc: measure before, add docs, verify 3x, commit or revert
   - Saves coverage improvements, evidence
10. Comprehensive verification:
   - Runs tests 3x, detects flaky tests
   - Compares before/after metrics
   - Fails if metrics regressed
11. Evidence validation:
   - Verifies all evidence files exist
   - Confirms metrics improved
   - Checks git commits created
12. Generates report with ACTUAL fixes, git commits, evidence
13. Presents results
```

### Fix Critical Only - With Evidence

```
User: /bx_fix_anal

Orchestrator:
1. Captures baseline metrics (tests 3x)
2. Creates fix plan
3. User selects "Fix critical only"
4. Fixes security vulnerabilities:
   - Measure before, fix, verify 3x, commit or revert
5. Fixes test failures:
   - Measure before, fix, verify 3x, commit or revert
6. Verification:
   - Tests 3x, compare metrics, detect flaky tests
7. Evidence validation
8. Report with git commits and evidence
```

### Review Plan Without Fixing

```
User: /bx_fix_anal

Orchestrator:
1. Captures baseline metrics (for future comparison)
2. Creates actionable fix plan with evidence requirements
3. User selects "Review plan only"
4. Shows detailed plan with:
   - Fix strategies
   - Evidence requirements
   - Success criteria
5. Exits without applying fixes (baseline metrics saved for later)
```

## Integration with Review System

**Evidence-Based Review-Fix Workflow:**

1. Run `/bx_review_anal` → Identify issues (review's opinion)
2. Review findings in `LLM-CONTEXT/review-anal/report/review_report.md`
3. Run `/bx_fix_anal` → ACTUALLY FIX with evidence:
   - Capture baseline metrics (don't trust review, re-measure)
   - Fix code, verify 3x, commit or revert
   - Compare before/after metrics
   - Keep only proven improvements
4. Verify ACTUAL fixes in `LLM-CONTEXT/fix-anal/report/fix_report.md`:
   - Git commits created (proof of changes)
   - Evidence files (before/after comparison)
   - Flaky tests detected
   - Metrics improvements
5. Run `/bx_review_anal` again → Verify improvements objectively
6. Compare review reports:
   - Before: `LLM-CONTEXT/review-anal-OLD/report/review_report.md`
   - After: `LLM-CONTEXT/review-anal/report/review_report.md`

**Iteration:**
- Review → Fix (with evidence) → Review → Fix → ...until perfect
- Each iteration MUST show objective metric improvements
- Failed fixes are reverted immediately (evidence-based)

## Notes

- Each fix sub-agent ACTUALLY MODIFIES CODE (not recommendations)
- Each sub-agent runs tests 3x to detect flaky tests
- Each sub-agent compares before/after metrics with evidence
- Each sub-agent git commits successful fixes, reverts failures
- The orchestrator coordinates the flow but delegates fixing to sub-agents
- All fix artifacts and evidence stored in LLM-CONTEXT/fix-anal/ for audit trail
- Sub-agents run sequentially (critical → quality → test refactoring → cache → docs) due to dependencies
- Each fix is verified with tests 3x before proceeding
- The evidence-based reviewer mindset is maintained throughout

## Best Practices

1. **Always capture baseline metrics first** - Step 0.5 is CRITICAL for comparison
2. **Always run review first** - This orchestrator requires review findings
3. **Don't trust review blindly** - Re-measure everything before fixing
4. **Fix critical issues first** - Security and tests are blockers
5. **Verify after each fix with 3x runs** - Detect flaky tests, catch regressions
6. **Keep only proven fixes** - Revert if tests fail or metrics regress
7. **Git commit successful fixes** - Create audit trail with clear messages
8. **Git revert failed fixes** - Don't keep unproven changes
9. **Save all evidence** - Before/after metrics, test results, git commits
10. **Validate evidence completeness** - Step 9.5 ensures all proof exists
11. **Re-run review after fixes** - Verify improvements objectively
12. **Trust evidence only** - Not assumptions, not hopes - only measured proof

## Troubleshooting

### "Review report not found"
- Run `/bx_review_anal` first to generate findings
- Ensure `LLM-CONTEXT/review-anal/` exists

### "Baseline metrics missing"
- Step 0.5 failed or was skipped
- Re-run from beginning to capture baseline
- Check test command is correct for your project

### "Critical fixes failed"
- Review `LLM-CONTEXT/fix-anal/critical/critical_summary.md`
- Check `LLM-CONTEXT/fix-anal/critical/security_fixes_reverted.log`
- Some issues may require manual intervention
- Review test output: `LLM-CONTEXT/fix-anal/evidence/critical/issue_*_after_tests.txt`

### "Tests fail after fixes"
- Check if fix was automatically reverted
- Review `LLM-CONTEXT/fix-anal/verification/test_results_run{1,2,3}.txt`
- Compare with baseline: `LLM-CONTEXT/fix-anal/metrics/baseline_tests_run{1,2,3}.txt`
- Check for flaky tests: `LLM-CONTEXT/fix-anal/verification/flaky_tests.txt`

### "Flaky tests detected"
- Review `LLM-CONTEXT/fix-anal/verification/flaky_tests.txt`
- These tests pass sometimes, fail sometimes
- Fix flaky tests before relying on test results
- Flaky tests make evidence unreliable

### "Evidence validation failed"
- Check Step 9.5 output for missing files
- Ensure all subagents completed successfully
- Verify metrics were captured in Step 0.5
- Check that verification ran 3x test runs

### "Metrics regressed"
- Check `LLM-CONTEXT/fix-anal/verification/regressions_detected.txt`
- Review `LLM-CONTEXT/fix-anal/verification/metrics_comparison.txt`
- Fixes should have been automatically reverted
- Investigate why fix caused regression

### "Fix plan is empty"
- Review found no fixable issues
- Review report may indicate "✓ APPROVED"
- No fixes needed!

### "Git commits not found"
- Check `LLM-CONTEXT/fix-anal/report/git_commits.txt`
- If empty, no fixes were successfully committed
- Review revert logs: `*_reverted.log` files
- All fixes may have failed verification

---

**Last Updated:** 2025-11-19
**Architecture Version:** 2.0 (Evidence-Based Fixing - Major Update)
**Companion Command:** bx_review_anal.md

**Version 2.0 Changes:**
- Added Step 0.5: Capture Baseline Metrics (CRITICAL for evidence-based comparison)
- Updated all fix subagent prompts to ACTUALLY MODIFY CODE (not just recommend)
- All subagents now run tests 3x to detect flaky tests
- All subagents compare before/after metrics with evidence
- All subagents git commit successful fixes, revert failures
- Updated Step 8: Verification now runs tests 3x and detects flaky tests
- Added Step 9.5: Final Evidence Validation
- Updated Step 9: Report now includes ACTUAL fixes, git commits, evidence
- Added "Evidence-Based Fixing Protocol" section
- Updated "Fix Principles" with 3x test runs and evidence requirements
- Philosophy: FROM "recommendations" TO "measure, fix, verify, commit or revert"
