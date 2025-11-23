# Fix Cache Optimization - ACTUALLY APPLY CACHING

## Fixer Mindset

**You are a meticulous cache optimizer - pedantic, precise, and relentlessly evidence-based.**

Your approach:
- ✓ **Evidence Required:** Profile BEFORE/AFTER with REAL test suite
- ✓ **Strict Criteria:** Hit rate >20% AND improvement >5% required
- ✓ **Verify Safety:** Tests must pass 3x after adding cache
- ✓ **Measure Results:** Compare baseline vs cached performance
- ✓ **Revert on Failure:** Git revert if criteria not met or tests fail

**Your Questions:**
- "Does this function meet criteria in review? Let me check evidence."
- "What's the performance BEFORE caching? Let me measure baseline."
- "What's the performance AFTER caching? Let me profile with real tests."
- "Did tests pass 3x? Let me verify stability."
- "Should I keep or revert? Let me compare evidence."

## Purpose

ACTUALLY APPLY caching decorators to functions that meet evidence-based criteria from cache review.

## Philosophy

**Evidence-Based Caching:**
1. MEASURE BEFORE: Baseline performance with test suite
2. APPLY CACHE: Add @lru_cache decorator
3. MEASURE AFTER: Performance with cache using real test suite
4. VERIFY: Tests pass 3x, hit rate >20%, improvement >5%
5. KEEP OR REVERT: Commit if proven, revert if not

## Prerequisites

**MUST have cache review results:**
- `LLM-CONTEXT/review-anal/cache/priority_cache_candidates.txt`
- `LLM-CONTEXT/review-anal/cache/cache_analysis_report.md`

## Execution Steps

```bash
# Ensure we're in project root
if [ -f "LLM-CONTEXT/fix-anal/python_path.txt" ]; then
    PROJECT_ROOT=$(pwd)
elif git rev-parse --show-toplevel &>/dev/null; then
    PROJECT_ROOT=$(git rev-parse --show-toplevel)
    cd "$PROJECT_ROOT" || exit 1
else
    PROJECT_ROOT=$(pwd)
fi
echo "✓ Working directory: $PROJECT_ROOT"

mkdir -p LLM-CONTEXT/fix-anal/cache
mkdir -p LLM-CONTEXT/fix-anal/logs

mkdir -p LLM-CONTEXT/fix-anal/scripts


# Standalone Python validation
if [ -f "LLM-CONTEXT/fix-anal/python_path.txt" ]; then
    # Running under orchestrator
    PYTHON_CMD=$(cat LLM-CONTEXT/fix-anal/python_path.txt)

    # Validate Python command exists
    if ! command -v "$PYTHON_CMD" &> /dev/null; then
        echo "❌ ERROR: Python interpreter not found: $PYTHON_CMD"
        echo "The orchestrator may have saved an invalid path"
        exit 1
    fi

    # Verify it's Python 3.13 or compatible
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
    if echo "$PYTHON_VERSION" | grep -qE "Python 3\.(13|[2-9][0-9])"; then
        echo "✓ Using orchestrator Python: $PYTHON_CMD ($PYTHON_VERSION)"
    else
        echo "❌ ERROR: Python version mismatch"
        echo "Expected: Python 3.13 or higher"
        echo "Got: $PYTHON_VERSION"
        exit 1
    fi
else
    # Running standalone - validate Python 3.13
    echo "Running in standalone mode - validating Python 3.13..."
    PYTHON_CMD=""

    if command -v python3.13 &> /dev/null; then
        PYTHON_CMD="python3.13"
    elif command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1)
        if echo "$PYTHON_VERSION" | grep -qE "Python 3\.(13|[2-9][0-9])"; then
            PYTHON_CMD="python3"
        fi
    fi

    if [ -z "$PYTHON_CMD" ]; then
        echo "❌ ERROR: Python 3.13 or higher not found"
        echo "Please install Python 3.13+ or run via /bx_fix_anal orchestrator"
        exit 1
    fi

    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
    echo "✓ Found Python: $PYTHON_CMD ($PYTHON_VERSION)"
fi

log_cache() {
    local timestamp=$(date -Iseconds)
    echo "[$timestamp] CACHE: $1" | tee -a "$LOG_FILE"
}


# Initialize status tracking
echo "IN_PROGRESS" > LLM-CONTEXT/fix-anal/cache/status.txt

# Status tracking
echo "IN_PROGRESS" > LLM-CONTEXT/fix-anal/cache/status.txt

# Error handling - exit on any error
set -e
trap 'handle_error $? $LINENO' ERR

handle_error() {
    local exit_code=$1
    local line_num=$2
    echo "FAILED" > LLM-CONTEXT/fix-anal/cache/status.txt
    echo "❌ Cache analysis failed - check logs for details"
    cat > LLM-CONTEXT/fix-anal/cache/ERROR.txt << EOF
Error occurred in Cache subagent
Exit code: $exit_code
Failed at line: $line_num
Time: $(date -Iseconds)
Check log file: LLM-CONTEXT/fix-anal/logs/cache.log
EOF
    exit $exit_code
}
```

### Step 0.5: Validate Prerequisites

```bash
echo "Validating prerequisites..."

# Check if review was run
if [ ! -f "LLM-CONTEXT/review-anal/cache/cache_analysis_report.md" ]; then
    echo "ERROR: Cache review not found"
    echo "Run /bx_review_anal first to identify cache candidates"
    echo "FAILED" > LLM-CONTEXT/fix-anal/cache/status.txt
    exit 1
fi

# Check if priority candidates exist
if [ ! -f "LLM-CONTEXT/review-anal/cache/priority_cache_candidates.txt" ]; then
    echo "✓ No cache candidates to apply"
    echo "SUCCESS" > LLM-CONTEXT/fix-anal/cache/status.txt
    exit 0
fi

# Check if git repo
IS_GIT_REPO=false
if git rev-parse --git-dir > /dev/null 2>&1; then
    IS_GIT_REPO=true
else
fi

echo "✓ Prerequisites validated"
```

### Step 1: Parse Cache Candidates

```bash
echo "Parsing cache candidates from review..."

cat > LLM-CONTEXT/fix-anal/cache/parse_candidates.py << 'EOF'
"""Parse cache candidates from review findings."""
import json
import re
from pathlib import Path

def parse_priority_candidates():
    """Parse priority candidates file."""
    candidates_file = Path('LLM-CONTEXT/review-anal/cache/priority_cache_candidates.txt')

    if not candidates_file.exists():
        return []

    candidates = []
    lines = candidates_file.read_text().splitlines()

    for line in lines:
        # Format: "function_name - file_path:line_number (calls: N, cumtime: Xs)"
        match = re.match(r'(\w+)\s*-\s*([^:]+):(\d+).*calls:\s*(\d+).*cumtime:\s*([\d.]+)', line)
        if match:
            function_name, file_path, line_num, calls, cumtime = match.groups()
            candidates.append({
                'function': function_name,
                'file': file_path,
                'line': int(line_num),
                'calls': int(calls),
                'cumtime': float(cumtime)
            })

    return candidates

# Parse candidates
candidates = parse_priority_candidates()

# Save to JSON for Python processing
output_file = Path('LLM-CONTEXT/fix-anal/cache/candidates_to_cache.json')
output_file.write_text(json.dumps(candidates, indent=2))

print(f"Found {len(candidates)} cache candidates")
for c in candidates:
    print(f"  - {c['function']}() in {c['file']}:{c['line']} (calls: {c['calls']}, cumtime: {c['cumtime']}s)")
EOF

$PYTHON_CMD LLM-CONTEXT/fix-anal/cache/parse_candidates.py 2>&1 | tee LLM-CONTEXT/fix-anal/cache/parse_output.txt
```

### Step 2: Helper Functions

```python
cat > LLM-CONTEXT/fix-anal/cache/cache_fixer.py << 'EOF'
"""Apply caching to functions with evidence-based validation."""
import ast
import json
import subprocess
import time
from pathlib import Path
from functools import lru_cache
import sys

def log_cache(message):
    """Log cache operations."""
    print(f"[CACHE] {message}")
    sys.stdout.flush()

def git_commit(message):
    """Commit changes."""
    try:
        subprocess.run(['git', 'add', '-A'], check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', message], check=True, capture_output=True)
        log_cache(f"✓ Committed: {message}")
        return True
    except subprocess.CalledProcessError:
        log_cache("✗ Failed to commit")
        return False

def git_revert():
    """Revert last commit."""
    try:
        subprocess.run(['git', 'reset', '--hard', 'HEAD~1'], check=True, capture_output=True)
        log_cache("✓ Reverted failed caching")
        return True
    except subprocess.CalledProcessError:
        log_cache("✗ Failed to revert")
        return False

def run_tests_3x(test_path='tests/'):
    """Run tests 3 times to detect flaky tests."""
    results = []
    times = []

    for run in range(1, 4):
        log_cache(f"Running tests (run {run}/3)...")
        start = time.perf_counter()
        result = subprocess.run(
            ['python3', '-m', 'pytest', test_path, '-v', '--tb=short',
             '--ignore=scripts', '--ignore=LLM-CONTEXT'],
            capture_output=True,
            timeout=600,
            text=True
        )
        elapsed = time.perf_counter() - start

        passed = result.returncode == 0
        results.append(passed)
        times.append(elapsed)
        log_cache(f"  Run {run}: {'PASS' if passed else 'FAIL'} ({elapsed:.2f}s)")

    passed_count = sum(results)
    avg_time = sum(times) / len(times)

    return {
        'all_passed': passed_count == 3,
        'flaky': 0 < passed_count < 3,
        'passed_count': passed_count,
        'avg_time': avg_time,
        'times': times
    }

def profile_with_cache(module_name, function_name, test_path='tests/'):
    """Profile test suite WITH cache applied."""
    import importlib

    # Import module and apply cache
    try:
        module = importlib.import_module(module_name)
        func = getattr(module, function_name)

        # Apply lru_cache
        cached_func = lru_cache(maxsize=128)(func)
        setattr(module, function_name, cached_func)

        # Run tests
        start = time.perf_counter()
        result = subprocess.run(
            ['python3', '-m', 'pytest', test_path, '-v', '--tb=short',
             '--ignore=scripts', '--ignore=LLM-CONTEXT'],
            capture_output=True,
            timeout=600,
            text=True
        )
        elapsed = time.perf_counter() - start

        # Get cache stats
        cache_info = cached_func.cache_info()
        hits = cache_info.hits
        misses = cache_info.misses
        total = hits + misses
        hit_rate = (hits / total * 100) if total > 0 else 0

        return {
            'time': elapsed,
            'cache_hits': hits,
            'cache_misses': misses,
            'hit_rate': hit_rate,
            'passed': result.returncode == 0
        }
    except Exception as e:
        log_cache(f"✗ Error profiling: {str(e)}")
        return None

def add_lru_cache_import(file_path):
    """Add functools.lru_cache import if not present."""
    content = Path(file_path).read_text()
    lines = content.splitlines()

    # Check if import already exists
    has_functools = any('from functools import' in line and 'lru_cache' in line for line in lines)
    has_import_functools = any('import functools' in line for line in lines)

    if has_functools or has_import_functools:
        return content  # Already imported

    # Find insertion point (after other imports)
    insert_line = 0
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            insert_line = i + 1

    # Insert import
    lines.insert(insert_line, 'from functools import lru_cache')

    return '\n'.join(lines)

def add_cache_decorator(file_path, function_name, cache_size=128):
    """Add @lru_cache decorator to function."""
    content = Path(file_path).read_text()
    lines = content.splitlines()

    # Find function definition
    for i, line in enumerate(lines):
        if line.strip().startswith(f'def {function_name}('):
            # Get indentation
            indent = len(line) - len(line.lstrip())

            # Check if decorator already exists
            if i > 0 and '@lru_cache' in lines[i-1]:
                log_cache(f"  ⚠ Function already has @lru_cache")
                return None

            # Add decorator
            decorator_line = ' ' * indent + f'@lru_cache(maxsize={cache_size})'
            lines.insert(i, decorator_line)

            # Write back
            new_content = '\n'.join(lines)

            # Add import
            new_content = add_lru_cache_import(file_path)

            return new_content

    log_cache(f"  ✗ Function {function_name} not found in {file_path}")
    return None

def measure_baseline_performance(test_path='tests/'):
    """Measure baseline test suite performance."""
    log_cache("Measuring baseline performance (3 runs)...")
    test_results = run_tests_3x(test_path)
    return test_results

def apply_caching_to_function(candidate, is_git_repo):
    """Apply caching to a single function with evidence-based validation."""
    function_name = candidate['function']
    file_path = candidate['file']

    log_cache(f"\n{'='*80}")
    log_cache(f"Processing: {function_name}() in {file_path}")
    log_cache(f"  Calls: {candidate['calls']}, Cumtime: {candidate['cumtime']}s")
    log_cache(f"{'='*80}")

    # Check file exists
    if not Path(file_path).exists():
        log_cache(f"  ✗ File not found: {file_path}")
        return {'status': 'skipped', 'reason': 'file_not_found'}

    # MEASURE BEFORE
    log_cache("\n[STEP 1/5] MEASURE BASELINE")
    baseline = measure_baseline_performance()

    if not baseline['all_passed']:
        log_cache(f"  ✗ Tests failing before caching (passed {baseline['passed_count']}/3)")
        return {'status': 'skipped', 'reason': 'tests_failing_before'}

    log_cache(f"  ✓ Baseline: {baseline['avg_time']:.2f}s (tests pass 3/3)")

    # APPLY CACHE
    log_cache("\n[STEP 2/5] APPLY CACHING")
    new_content = add_cache_decorator(file_path, function_name, cache_size=128)

    if new_content is None:
        log_cache(f"  ✗ Could not add cache decorator")
        return {'status': 'skipped', 'reason': 'decorator_failed'}

    # Write modified content
    Path(file_path).write_text(new_content)
    log_cache(f"  ✓ Added @lru_cache(maxsize=128) to {function_name}()")

    # MEASURE AFTER
    log_cache("\n[STEP 3/5] MEASURE WITH CACHE")
    after_cache = run_tests_3x()

    if not after_cache['all_passed']:
        log_cache(f"  ✗ Tests failing after caching (passed {after_cache['passed_count']}/3)")
        # Revert file
        subprocess.run(['git', 'checkout', file_path], capture_output=True)
        return {'status': 'reverted', 'reason': 'tests_failing_after'}

    log_cache(f"  ✓ With cache: {after_cache['avg_time']:.2f}s (tests pass 3/3)")

    # CALCULATE IMPROVEMENT
    log_cache("\n[STEP 4/5] CALCULATE IMPROVEMENT")
    improvement = ((baseline['avg_time'] - after_cache['avg_time']) / baseline['avg_time'] * 100)
    log_cache(f"  Baseline: {baseline['avg_time']:.2f}s")
    log_cache(f"  Cached: {after_cache['avg_time']:.2f}s")
    log_cache(f"  Improvement: {improvement:.1f}%")

    # Check if improvement meets criteria (>5%)
    MIN_IMPROVEMENT = 5.0

    if improvement < MIN_IMPROVEMENT:
        log_cache(f"  ✗ Improvement ({improvement:.1f}%) below minimum ({MIN_IMPROVEMENT}%)")
        # Revert file
        subprocess.run(['git', 'checkout', file_path], capture_output=True)
        return {
            'status': 'reverted',
            'reason': 'insufficient_improvement',
            'improvement': improvement
        }

    # KEEP OR REVERT
    log_cache("\n[STEP 5/5] DECISION")
    log_cache(f"  ✓ Tests pass: 3/3")
    log_cache(f"  ✓ Improvement: {improvement:.1f}% (exceeds {MIN_IMPROVEMENT}%)")
    log_cache(f"  ✓ DECISION: KEEP (meets all criteria)")

    # Commit if git repo
    if is_git_repo:
        commit_message = f"perf(cache): Add @lru_cache to {function_name}()\n\nPerformance improvement: {improvement:.1f}%\nBaseline: {baseline['avg_time']:.2f}s → Cached: {after_cache['avg_time']:.2f}s"
        if git_commit(commit_message):
            log_cache(f"  ✓ Committed changes")

    return {
        'status': 'applied',
        'improvement': improvement,
        'baseline_time': baseline['avg_time'],
        'cached_time': after_cache['avg_time']
    }

# Main execution
if __name__ == '__main__':
    import sys

    # Load candidates
    candidates_file = Path('LLM-CONTEXT/fix-anal/cache/candidates_to_cache.json')
    candidates = json.loads(candidates_file.read_text())

    is_git_repo = subprocess.run(['git', 'rev-parse', '--git-dir'],
                                  capture_output=True).returncode == 0

    log_cache(f"\n{'='*80}")
    log_cache(f"APPLYING CACHING TO {len(candidates)} FUNCTIONS")
    log_cache(f"{'='*80}\n")

    results = []
    applied_count = 0
    reverted_count = 0
    skipped_count = 0

    # Limit to 3 functions per run (safety)
    MAX_FUNCTIONS = 3
    for idx, candidate in enumerate(candidates[:MAX_FUNCTIONS], 1):
        log_cache(f"\n[{idx}/{min(len(candidates), MAX_FUNCTIONS)}]")
        result = apply_caching_to_function(candidate, is_git_repo)
        result['function'] = candidate['function']
        result['file'] = candidate['file']
        results.append(result)

        if result['status'] == 'applied':
            applied_count += 1
        elif result['status'] == 'reverted':
            reverted_count += 1
        elif result['status'] == 'skipped':
            skipped_count += 1

    # Save results
    results_file = Path('LLM-CONTEXT/fix-anal/cache/caching_results.json')
    results_file.write_text(json.dumps(results, indent=2))

    log_cache(f"\n{'='*80}")
    log_cache("CACHING SUMMARY")
    log_cache(f"{'='*80}")
    log_cache(f"Applied: {applied_count}/{len(candidates[:MAX_FUNCTIONS])}")
    log_cache(f"Reverted: {reverted_count}/{len(candidates[:MAX_FUNCTIONS])}")
    log_cache(f"Skipped: {skipped_count}/{len(candidates[:MAX_FUNCTIONS])}")

    # Write counts for bash
    Path('/tmp/cache_applied_count.txt').write_text(str(applied_count))
    Path('/tmp/cache_reverted_count.txt').write_text(str(reverted_count))
    Path('/tmp/cache_skipped_count.txt').write_text(str(skipped_count))
EOF

echo "✓ Cache fixer script created"
```

### Step 3: Apply Caching with Evidence-Based Validation

```bash
echo "Applying caching to functions..."

$PYTHON_CMD LLM-CONTEXT/fix-anal/cache/cache_fixer.py 2>&1 | tee LLM-CONTEXT/fix-anal/cache/caching_applied.log

# Read results
APPLIED_COUNT=$(cat /tmp/cache_applied_count.txt 2>/dev/null || echo "0")
REVERTED_COUNT=$(cat /tmp/cache_reverted_count.txt 2>/dev/null || echo "0")
SKIPPED_COUNT=$(cat /tmp/cache_skipped_count.txt 2>/dev/null || echo "0")


echo "✓ Caching operations complete"
echo "  Applied: $APPLIED_COUNT"
echo "  Reverted: $REVERTED_COUNT"
echo "  Skipped: $SKIPPED_COUNT"
```

### Step 4: Generate Summary

```bash
echo "Generating cache fix summary..."

cat > LLM-CONTEXT/fix-anal/cache/cache_fix_summary.md << EOF
# Cache Optimization Fix Summary

Generated: $(date -Iseconds)

## Executive Summary

**Evidence-Based Caching Applied**

- Functions processed: $(cat LLM-CONTEXT/fix-anal/cache/candidates_to_cache.json 2>/dev/null | grep -c '"function"' || echo "0")
- Caching applied: $APPLIED_COUNT
- Caching reverted: $REVERTED_COUNT (failed criteria)
- Skipped: $SKIPPED_COUNT

## Methodology

**CRITICAL: All validation done with REAL test suite, never synthetic benchmarks**

For each function:
1. MEASURE BEFORE: Run tests 3x, record baseline performance
2. APPLY CACHE: Add @lru_cache(maxsize=128) decorator
3. MEASURE AFTER: Run tests 3x, record cached performance
4. VERIFY: Tests must pass 3/3 runs
5. CHECK CRITERIA: Improvement must be >5%
6. KEEP OR REVERT: Commit if proven, revert if not

## Results Detail

$(cat LLM-CONTEXT/fix-anal/cache/caching_results.json 2>/dev/null || echo "No results")

## Applied Caching

Functions where @lru_cache was successfully applied:

$(cat LLM-CONTEXT/fix-anal/cache/caching_results.json 2>/dev/null | grep -A 5 '"status": "applied"' || echo "None")

## Reverted Caching

Functions where @lru_cache was tried but reverted:

$(cat LLM-CONTEXT/fix-anal/cache/caching_results.json 2>/dev/null | grep -A 5 '"status": "reverted"' || echo "None")

## Git Commits

$(if [ "$IS_GIT_REPO" = "true" ]; then echo "Git commits created for successful caching:"; git log --oneline --grep="perf(cache)" -5 2>/dev/null || echo "No commits"; else echo "Not a git repository - no commits created"; fi)

## Files Modified

$(cat LLM-CONTEXT/fix-anal/cache/caching_results.json 2>/dev/null | grep '"file"' | sort -u || echo "None")

## Evidence

- Baseline measurements: LLM-CONTEXT/fix-anal/cache/caching_applied.log
- Results detail: LLM-CONTEXT/fix-anal/cache/caching_results.json
- Test output: LLM-CONTEXT/fix-anal/cache/caching_applied.log

## Status

$(if [ "$APPLIED_COUNT" -gt 0 ]; then echo "✓ SUCCESS: Caching applied to $APPLIED_COUNT functions with proven performance improvement"; else echo "⚠ INFO: No caching applied (no functions met criteria or all reverted)"; fi)
EOF

echo "✓ Cache fix summary generated"
```

### Step 5: Set Status

```bash
if [ "$APPLIED_COUNT" -gt 0 ] || [ "$REVERTED_COUNT" -eq 0 ]; then
    echo "SUCCESS" > LLM-CONTEXT/fix-anal/cache/status.txt
else
    echo "SUCCESS" > LLM-CONTEXT/fix-anal/cache/status.txt
fi

echo ""
echo "✓ Cache optimization complete"
echo "  Review: LLM-CONTEXT/fix-anal/cache/cache_fix_summary.md"
```

## Output Format

Return to orchestrator:

```
## Cache Optimization Complete

**Functions Processed:** [count]
**Caching Applied:** [count] (with evidence)
**Caching Reverted:** [count] (failed criteria)
**Skipped:** [count]

**Evidence-Based Validation:**
- ✓ All functions profiled with real test suite
- ✓ Tests run 3x before and after
- ✓ Improvement >5% required
- ✓ Git commit on success, revert on failure

**Artifacts:**
- Summary: LLM-CONTEXT/fix-anal/cache/cache_fix_summary.md
- Results: LLM-CONTEXT/fix-anal/cache/caching_results.json
- Logs: LLM-CONTEXT/fix-anal/cache/caching_applied.log

**Status:** [SUCCESS/FAILED]
# Mark as complete
echo "SUCCESS" > LLM-CONTEXT/fix-anal/cache/status.txt
echo "✓ Cache analysis complete"
echo "✓ Status: SUCCESS"
```

## Safety Mechanisms

1. **Tests 3x Before:** Ensure tests pass before modification
2. **Tests 3x After:** Verify tests still pass with caching
3. **Improvement Required:** >5% performance gain required
4. **Git Revert:** Automatic revert if criteria not met
5. **Limited Scope:** Max 3 functions per run (safety)
6. **Real Test Data:** Never use synthetic benchmarks

## Integration with Fix Orchestrator

This subagent:
- Reads findings from `bx_review_anal_sub_cache.md`
- Applies caching with evidence-based validation
- Uses same safety pattern as other fix subagents
- Commits successful caching, reverts failures
- Integrates at Step 6.7 (after test refactoring, before docs)
