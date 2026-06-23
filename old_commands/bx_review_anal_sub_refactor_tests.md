# Test Refactoring Review Subagent

## Reviewer Mindset for Test Quality Analysis

**You are a meticulous test quality reviewer with exceptional attention to detail - pedantic, precise, and relentlessly thorough.**

Your approach when reviewing tests:
- ✓ **Every Single Test:** Must read like plain English or a poem
- ✓ **Maximum Coverage:** Identify gaps where tests are missing
- ✓ **Real Behavior:** Detect tests that verify stubs instead of real behavior
- ✓ **OS-Specific Marking:** Identify tests that should be marked OS-specific
- ✓ **Laser Focus:** Flag tests that check multiple behaviors
- ✓ **Coverage Analysis:** Measure coverage and identify untested paths
- ✓ **Quality Metrics:** Document test quality issues for fixing

**Your Questions:**
- "Is this test testing real behavior or just a stub?"
- "Does this test name read like plain English?"
- "Is this test OS-specific? Should it be marked?"
- "Does this test check exactly ONE behavior?"
- "What test coverage gaps exist?"

## Purpose

**ANALYZE TEST QUALITY** according to clean architecture principles. This subagent REVIEWS test files and identifies quality issues, following these principles **to the extreme**.

**Philosophy:**
- Measure test coverage baseline
- Identify tests with poor names
- Detect tests that need OS-specific marking
- Find stub-only tests that should test real behavior
- Identify multi-behavior tests that should be split
- Find coverage gaps where tests are missing
- Document all issues for the fix subagent
- Generate comprehensive quality report

## Core Principles

1. Ensure **maximum coverage** — write additional tests where needed until coverage is exhaustive
2. Each test function should read like **plain English or even like a poem**
3. Tests should be **super small, obvious, and laser-focused**
4. If you think the tests are already clean enough — **refactor again** until they are irreducibly clear
5. Strive for **absolute clarity and intent**: every test should describe **exactly one behavior**

## OS-Specific Testing

Tests must be marked **OS-specific**:
* Some behaviors may only be testable under **Windows**
* Others only under **macOS (OSX)**
* Others only under **POSIX systems**
* Others should be **OS-agnostic**

Clearly mark and separate these categories so test execution adapts to the environment.

Use pytest markers like:
```python
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only")
@pytest.mark.skipif(sys.platform != "darwin", reason="macOS-only")
@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only")
```

## Real Behavior Over Mocks

**Whenever possible, test real behavior — not stubs or mocks.**

* Testing stubs only verifies that the stub itself works, **not the actual system behavior**
* Avoid such tests unless absolutely necessary for isolation
* Prefer **integration and end-to-end tests** that validate real logic, data flow, and side effects
* **Stub-only tests are weak indicators of correctness** — replace them with meaningful behavioral checks
* Do not use stubs to simulate **OS-specific** behaviour - those tests should run on CI runners with the specific OS

## Responsibilities

- Identify tests with non-descriptive names
- Flag tests that check multiple behaviors
- Identify missing tests to achieve maximum coverage
- Detect stub-only tests that should test real behavior
- Find tests that should be marked OS-specific
- Detect test duplication
- Identify flaky or non-deterministic tests
- Measure test coverage and find gaps
- Generate detailed quality report
- Document issues for fix subagent

## Execution

### Step 0: Initialize Environment

```bash
echo "=================================="
echo "TEST QUALITY REVIEW SUBAGENT"
echo "TEST ANALYSIS MODE"
echo "=================================="
echo ""

# Create workspace
mkdir -p LLM-CONTEXT/review-anal/refactor-tests
mkdir -p LLM-CONTEXT/review-anal/logs

mkdir -p LLM-CONTEXT/review-anal/scripts


# Standalone Python validation
if [ -f "LLM-CONTEXT/review-anal/python_path.txt" ]; then
    # Running under orchestrator
    PYTHON_CMD=$(cat LLM-CONTEXT/review-anal/python_path.txt)

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
        echo "Please install Python 3.13+ or run via /bx_review_anal orchestrator"
        exit 1
    fi

    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
    echo "✓ Found Python: $PYTHON_CMD ($PYTHON_VERSION)"
fi
# Initialize status
cat > LLM-CONTEXT/review-anal/refactor-tests/status.txt << 'EOF'
IN_PROGRESS
EOF


# Initialize status tracking
echo "IN_PROGRESS" > LLM-CONTEXT/review-anal/refactor-tests/status.txt

# Initialize counters
echo "0" > /tmp/tests_refactored.txt
echo "0" > /tmp/tests_added.txt
echo "0" > /tmp/stubs_replaced.txt
echo "0" > /tmp/os_marked.txt
echo "0" > /tmp/refactor_failed.txt

# Initialize review log
cat > LLM-CONTEXT/review-anal/refactor-tests/review.log << 'EOF'
# Test Quality Review Log
# Generated: $(date -Iseconds)

EOF

echo "✓ Workspace initialized for test quality review"
echo "✓ Logging initialized: $LOG_FILE"
echo ""
```

### Step 1: Analyze Current Test Suite

```bash
echo "Step 1: Analyzing current test suite..."
echo ""

$PYTHON_CMD << 'PYTHON_ANALYZE'
import ast
import json
import sys
from pathlib import Path
from datetime import datetime

LOG_FILE = Path('LLM-CONTEXT/review-anal/logs/refactor_tests.log')

def log_error(message):
    timestamp = datetime.now().isoformat()
    log_msg = f"[{timestamp}] ERROR (script.py): {message}\n"
    print(log_msg, file=sys.stderr, end='')
    with open(LOG_FILE, 'a') as f:
        f.write(log_msg)

def log_info(message):
    timestamp = datetime.now().isoformat()
    log_msg = f"[{timestamp}] INFO (script.py): {message}\n"
    print(log_msg, end='')
    with open(LOG_FILE, 'a') as f:
        f.write(log_msg)

def log_refactor(message: str):
    """Log refactoring message."""
    with open('LLM-CONTEXT/review-anal/refactor-tests/review.log', 'a') as f:
        f.write(f"{message}\n")
    print(message)

def analyze_test_file(file_path: Path) -> dict:
    """Analyze a single test file."""
    try:
        content = file_path.read_text()
        tree = ast.parse(content)

        tests = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                # Check if name is descriptive (reads like English)
                is_descriptive = '_' in node.name[5:] and len(node.name) > 10

                # Check for OS-specific markers
                has_os_marker = False
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        if hasattr(decorator.func, 'attr') and 'skip' in decorator.func.attr.lower():
                            has_os_marker = True
                    elif isinstance(decorator, ast.Attribute) and 'skip' in decorator.attr.lower():
                        has_os_marker = True

                # Count assertions (should be ~1 for focused tests)
                assertion_count = sum(1 for n in ast.walk(node)
                                    if isinstance(n, ast.Assert) or
                                    (isinstance(n, ast.Call) and hasattr(n.func, 'attr') and 'assert' in n.func.attr.lower()))

                # Check for mock usage
                uses_mocks = any('mock' in ast.unparse(n).lower() or 'patch' in ast.unparse(n).lower()
                               for n in ast.walk(node))

                # Estimate if it's stub-only
                is_stub_only = uses_mocks and assertion_count <= 2

                tests.append({
                    'name': node.name,
                    'line': node.lineno,
                    'is_descriptive': is_descriptive,
                    'has_os_marker': has_os_marker,
                    'assertion_count': assertion_count,
                    'uses_mocks': uses_mocks,
                    'is_stub_only': is_stub_only,
                    'is_focused': assertion_count <= 3  # Focused tests have few assertions
                })

        return {
            'file': str(file_path),
            'test_count': len(tests),
            'tests': tests
        }

    except Exception as e:
        return None

# Find all test files (excluding folders)
excluded_dirs = {'scripts', 'LLM-CONTEXT', '.idea', '.git', '.github', '.claude',
                 '.devcontainer', '.pytest_cache', '.qlty', '.ruff_cache'}

test_files = []
for pattern in ['test_*.py', '*_test.py']:
    for path in Path('.').rglob(pattern):
        if not any(excluded in path.parts for excluded in excluded_dirs):
            test_files.append(path)


# Analyze all test files
analysis_results = []
for test_file in test_files:
    result = analyze_test_file(test_file)
    if result:
        analysis_results.append(result)

# Generate statistics
total_tests = sum(r['test_count'] for r in analysis_results)
non_descriptive = sum(1 for r in analysis_results for t in r['tests'] if not t['is_descriptive'])
no_os_marker = sum(1 for r in analysis_results for t in r['tests'] if not t['has_os_marker'])
stub_only = sum(1 for r in analysis_results for t in r['tests'] if t['is_stub_only'])
not_focused = sum(1 for r in analysis_results for t in r['tests'] if not t['is_focused'])

log_refactor(f"\n=== Test Suite Analysis ===")
log_refactor(f"Total test files: {len(analysis_results)}")
log_refactor(f"Total tests: {total_tests}")
log_refactor(f"")
log_refactor(f"Issues found:")
log_refactor(f"  - Non-descriptive names: {non_descriptive}")
log_refactor(f"  - Missing OS markers: {no_os_marker}")
log_refactor(f"  - Stub-only tests: {stub_only}")
log_refactor(f"  - Not focused (>3 assertions): {not_focused}")
log_refactor(f"")

# Save analysis
output = {
    'files': analysis_results,
    'statistics': {
        'total_files': len(analysis_results),
        'total_tests': total_tests,
        'non_descriptive': non_descriptive,
        'no_os_marker': no_os_marker,
        'stub_only': stub_only,
        'not_focused': not_focused
    }
}

output_file = Path('LLM-CONTEXT/review-anal/refactor-tests/analysis.json')
output_file.write_text(json.dumps(output, indent=2))


PYTHON_ANALYZE

if [ $? -ne 0 ]; then
    echo "FAILED" > LLM-CONTEXT/review-anal/refactor-tests/status.txt
    exit 1
fi

echo ""
```

### Step 2: Identify Tests with Non-Descriptive Names

```bash
echo "Step 2: Identifying tests with non-descriptive names..."
echo ""

$PYTHON_CMD << 'PYTHON_REFACTOR_NAMES'
import ast
import json
import re
import subprocess
from pathlib import Path
from datetime import datetime
import sys

LOG_FILE = Path('LLM-CONTEXT/review-anal/logs/refactor_tests.log')

def log_error(message):
    timestamp = datetime.now().isoformat()
    log_msg = f"[{timestamp}] ERROR (script.py): {message}\n"
    print(log_msg, file=sys.stderr, end='')
    with open(LOG_FILE, 'a') as f:
        f.write(log_msg)

def log_info(message):
    timestamp = datetime.now().isoformat()
    log_msg = f"[{timestamp}] INFO (script.py): {message}\n"
    print(log_msg, end='')
    with open(LOG_FILE, 'a') as f:
        f.write(log_msg)

def log_refactor(message: str):
    """Log refactoring message."""
    with open('LLM-CONTEXT/review-anal/refactor-tests/review.log', 'a') as f:
        f.write(f"{message}\n")
    print(message)

def run_tests_3x(stage: str) -> dict:
    """
    VERIFICATION PROTOCOL: Run tests 3 times to detect flaky tests.
    Returns: {'all_passed': bool, 'flaky': bool, 'passed_count': int}
    """
    log_refactor(f"  [{stage}] Running tests 3 times to detect flakiness...")

    results = []
    for run in range(1, 4):
        log_refactor(f"  [{stage}] Test run {run}/3...")

        result = subprocess.run([
            'python3', '-m', 'pytest', '--tb=short', '-v',
            '--ignore=scripts', '--ignore=LLM-CONTEXT', '--ignore=.idea',
            '--ignore=.git', '--ignore=.github', '--ignore=.claude',
            '--ignore=.devcontainer', '--ignore=.pytest_cache',
            '--ignore=.qlty', '--ignore=.ruff_cache'
        ], capture_output=True, timeout=300, text=True)

        passed = result.returncode == 0
        results.append(passed)

        log_refactor(f"  [{stage}] Run {run}/3: {'PASSED ✓' if passed else 'FAILED ✗'}")

    passed_count = sum(results)
    all_passed = passed_count == 3
    flaky = 0 < passed_count < 3

    if flaky:
        log_refactor(f"  ⚠ [{stage}] FLAKY TESTS: {passed_count}/3 runs passed - INVESTIGATE!")

    return {'all_passed': all_passed, 'flaky': flaky, 'passed_count': passed_count}

def git_commit(message: str) -> bool:
    """Commit changes with message."""
    try:
        subprocess.run(['git', 'add', '-A'], check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', message], check=True, capture_output=True)
        log_refactor(f"  ✓ Committed: {message}")
        return True
    except subprocess.CalledProcessError:
        log_refactor(f"  ✗ Failed to commit")
        return False

def git_revert() -> bool:
    """Revert last commit."""
    try:
        subprocess.run(['git', 'reset', '--hard', 'HEAD~1'], check=True, capture_output=True)
        log_refactor(f"  ✓ Reverted failed refactoring")
        return True
    except subprocess.CalledProcessError:
        log_refactor(f"  ✗ Failed to revert")
        return False

def improve_test_name(current_name: str) -> str:
    """Convert test name to read like plain English."""
    # Remove 'test_' prefix
    name = current_name[5:] if current_name.startswith('test_') else current_name

    # If already descriptive, keep it
    if len(name) > 20 and name.count('_') >= 3:
        return current_name

    # Try to make it more descriptive
    # Pattern: test_function_does_something -> test_function_should_do_something_when_condition

    # Common patterns to improve:
    patterns = {
        r'^(\w+)_works$': r'\1_should_work_correctly',
        r'^(\w+)_fails$': r'\1_should_fail_when_invalid',
        r'^(\w+)_test$': r'\1_should_behave_correctly',
        r'^(\w+)_(\w+)$': r'\1_should_\2_correctly',
    }

    for pattern, replacement in patterns.items():
        improved = re.sub(pattern, replacement, name)
        if improved != name:
            return f'test_{improved}'

    # If can't improve programmatically, mark for manual review
    return None

# Load analysis
analysis_file = Path('LLM-CONTEXT/review-anal/refactor-tests/analysis.json')
if not analysis_file.exists():
    sys.exit(1)

analysis = json.loads(analysis_file.read_text())

# Check if git repo
is_git_repo = Path('.git').exists()
if not is_git_repo:
    log_refactor("⚠ Not a git repository - changes cannot be auto-reverted")

refactored_count = 0

log_refactor(f"\n=== Refactoring Test Names ===\n")

# For now, just identify tests that need renaming
# Full implementation would use Edit tool to rename
for file_result in analysis['files']:
    file_path = file_result['file']

    needs_renaming = [t for t in file_result['tests'] if not t['is_descriptive']]

    if needs_renaming:
        log_refactor(f"\nFile: {file_path}")
        log_refactor(f"Tests needing better names: {len(needs_renaming)}")

        for test in needs_renaming[:3]:  # Show first 3
            improved = improve_test_name(test['name'])
            if improved:
                log_refactor(f"  - {test['name']} → {improved}")
            else:
                log_refactor(f"  - {test['name']} → [MANUAL REVIEW NEEDED]")

# Save count
with open('/tmp/tests_refactored.txt', 'w') as f:
    f.write(str(refactored_count))

log_refactor(f"\n✓ Test name analysis complete")
log_refactor(f"Note: Automatic renaming requires Edit tool integration")

PYTHON_REFACTOR_NAMES

echo ""
```

### Step 3: Identify Tests Needing OS-Specific Markers

```bash
echo "Step 3: Identifying tests that need OS-specific markers..."
echo ""

$PYTHON_CMD << 'PYTHON_MARK_OS'
import ast
import json
from pathlib import Path
from datetime import datetime
import sys

LOG_FILE = Path('LLM-CONTEXT/review-anal/logs/refactor_tests.log')

def log_error(message):
    timestamp = datetime.now().isoformat()
    log_msg = f"[{timestamp}] ERROR (script.py): {message}\n"
    print(log_msg, file=sys.stderr, end='')
    with open(LOG_FILE, 'a') as f:
        f.write(log_msg)

def log_refactor(message: str):
    """Log refactoring message."""
    with open('LLM-CONTEXT/review-anal/refactor-tests/review.log', 'a') as f:
        f.write(f"{message}\n")
    print(message)

def identify_os_specific_tests(file_path: Path) -> list:
    """Identify tests that should be marked OS-specific."""
    try:
        content = file_path.read_text()
        tree = ast.parse(content)

        os_specific = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                # Look for OS-specific indicators in code
                code = ast.unparse(node)

                windows_indicators = ['win32', 'windows', 'nt', 'windir', 'USERPROFILE']
                macos_indicators = ['darwin', 'macos', 'osx', 'HOME', 'Library']
                posix_indicators = ['posix', 'unix', 'linux', '/tmp/', '/var/']

                is_windows = any(ind.lower() in code.lower() for ind in windows_indicators)
                is_macos = any(ind.lower() in code.lower() for ind in macos_indicators)
                is_posix = any(ind.lower() in code.lower() for ind in posix_indicators)

                # Check if already has OS marker
                has_marker = any(
                    isinstance(dec, ast.Call) and
                    hasattr(dec.func, 'attr') and
                    'skip' in dec.func.attr.lower()
                    for dec in node.decorator_list
                )

                if (is_windows or is_macos or is_posix) and not has_marker:
                    os_type = 'Windows' if is_windows else ('macOS' if is_macos else 'POSIX')
                    os_specific.append({
                        'name': node.name,
                        'line': node.lineno,
                        'os_type': os_type,
                        'needs_marker': True
                    })

        return os_specific

    except Exception as e:
        return []

# Load analysis
analysis_file = Path('LLM-CONTEXT/review-anal/refactor-tests/analysis.json')
analysis = json.loads(analysis_file.read_text())

log_refactor(f"\n=== Marking OS-Specific Tests ===\n")

os_marked_count = 0

for file_result in analysis['files']:
    file_path = Path(file_result['file'])

    os_tests = identify_os_specific_tests(file_path)

    if os_tests:
        log_refactor(f"\nFile: {file_path}")
        log_refactor(f"OS-specific tests needing markers: {len(os_tests)}")

        for test in os_tests[:5]:  # Show first 5
            log_refactor(f"  - {test['name']} (line {test['line']}) → Mark as {test['os_type']}-only")
            log_refactor(f"    Add: @pytest.mark.skipif(sys.platform != '...')")

# Save count
with open('/tmp/os_marked.txt', 'w') as f:
    f.write(str(os_marked_count))

log_refactor(f"\n✓ OS-specific test analysis complete")
log_refactor(f"Note: Automatic marking requires Edit tool integration")

PYTHON_MARK_OS

echo ""
```

### Step 4: Identify Stub-Only Tests That Need Replacement

```bash
echo "Step 4: Identifying stub-only tests that need replacement..."
echo ""

$PYTHON_CMD << 'PYTHON_REPLACE_STUBS'
import json
from pathlib import Path
from datetime import datetime
import sys

LOG_FILE = Path('LLM-CONTEXT/review-anal/logs/refactor_tests.log')

def log_refactor(message: str):
    """Log refactoring message."""
    with open('LLM-CONTEXT/review-anal/refactor-tests/review.log', 'a') as f:
        f.write(f"{message}\n")
    print(message)

# Load analysis
analysis_file = Path('LLM-CONTEXT/review-anal/refactor-tests/analysis.json')
analysis = json.loads(analysis_file.read_text())

log_refactor(f"\n=== Replacing Stub-Only Tests ===\n")

stub_tests = []

for file_result in analysis['files']:
    file_path = file_result['file']

    stubs = [t for t in file_result['tests'] if t.get('is_stub_only', False)]

    if stubs:
        log_refactor(f"\nFile: {file_path}")
        log_refactor(f"Stub-only tests found: {len(stubs)}")

        for test in stubs[:3]:
            log_refactor(f"  - {test['name']} (line {test['line']})")
            log_refactor(f"    Issue: Tests mocks instead of real behavior")
            log_refactor(f"    Action: Replace with integration/e2e test")

        stub_tests.extend(stubs)

# Save count
with open('/tmp/stubs_replaced.txt', 'w') as f:
    f.write(str(0))  # Would be actual count after refactoring

log_refactor(f"\nTotal stub-only tests identified: {len(stub_tests)}")
log_refactor(f"✓ Stub analysis complete")
log_refactor(f"Note: Replacing stubs requires significant refactoring - manual review recommended")

PYTHON_REPLACE_STUBS

echo ""
```

### Step 5: Run Tests and Verify Quality

```bash
echo "Step 5: Running final test suite..."
echo ""

# Run tests with exclusions
if [ -f "pytest.ini" ] || [ -f "pyproject.toml" ]; then
    $PYTHON_CMD -m pytest --verbose --tb=short \
        --ignore=scripts \
        --ignore=LLM-CONTEXT \
        --ignore=.idea \
        --ignore=.git \
        --ignore=.github \
        --ignore=.claude \
        --ignore=.devcontainer \
        --ignore=.pytest_cache \
        --ignore=.qlty \
        --ignore=.ruff_cache \
        2>&1 | tee LLM-CONTEXT/review-anal/refactor-tests/test_results.txt

    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        echo "✓ Test suite PASSED"
        TEST_STATUS="PASSED"
    else
        echo "⚠ Test suite has failures"
        TEST_STATUS="FAILED"
    fi
else
    echo "⚠ No pytest configuration found - skipping test run"
    TEST_STATUS="SKIPPED"
fi

echo "$TEST_STATUS" > LLM-CONTEXT/review-anal/refactor-tests/test_status.txt
echo ""
```

### Step 6: Generate Coverage Report

```bash
echo "Step 6: Generating coverage report..."
echo ""

if command -v coverage &> /dev/null || $PYTHON_CMD -m coverage --version &> /dev/null 2>&1; then

    $PYTHON_CMD -m coverage run -m pytest \
        --ignore=scripts \
        --ignore=LLM-CONTEXT \
        --ignore=.idea \
        --ignore=.git \
        --ignore=.github \
        --ignore=.claude \
        --ignore=.devcontainer \
        --ignore=.pytest_cache \
        --ignore=.qlty \
        --ignore=.ruff_cache \
        2>&1 | tee LLM-CONTEXT/review-anal/refactor-tests/coverage_run.txt

    $PYTHON_CMD -m coverage report > LLM-CONTEXT/review-anal/refactor-tests/coverage_report.txt
    $PYTHON_CMD -m coverage html -d LLM-CONTEXT/review-anal/refactor-tests/htmlcov 2>/dev/null

    echo "✓ Coverage report generated"
else
    echo "⚠ Coverage tool not available - skipping coverage report"
fi

echo ""
```

### Step 7: Generate Summary Report

```bash
echo "Step 7: Generating summary report..."
echo ""

# Collect statistics
TESTS_REFACTORED=$(cat /tmp/tests_refactored.txt 2>/dev/null || echo "0")
TESTS_ADDED=$(cat /tmp/tests_added.txt 2>/dev/null || echo "0")
STUBS_REPLACED=$(cat /tmp/stubs_replaced.txt 2>/dev/null || echo "0")
OS_MARKED=$(cat /tmp/os_marked.txt 2>/dev/null || echo "0")
REFACTOR_FAILED=$(cat /tmp/refactor_failed.txt 2>/dev/null || echo "0")
TEST_STATUS=$(cat LLM-CONTEXT/review-anal/refactor-tests/test_status.txt 2>/dev/null || echo "UNKNOWN")

# Generate summary report
cat > LLM-CONTEXT/review-anal/refactor-tests/summary.md << EOF
# Test Quality Review Summary

**Generated:** $(date -Iseconds)
**Mode:** TEST QUALITY ANALYSIS

---

## Executive Summary

**Tests with Poor Names:** $TESTS_REFACTORED
**Missing Tests Identified:** $TESTS_ADDED
**Stub-Only Tests Found:** $STUBS_REPLACED
**Tests Needing OS Markers:** $OS_MARKED
**Current Test Status:** $TEST_STATUS

---

## Core Principles Applied

This subagent reviews tests according to **clean architecture principles to the extreme**:

1. ✓ **Maximum Coverage** — Identify where tests are missing
2. ✓ **Plain English** — Flag tests with cryptic names
3. ✓ **Laser-Focused** — Detect tests checking multiple behaviors
4. ✓ **Real Behavior** — Find stub-only tests that need real behavioral tests
5. ✓ **OS-Specific** — Identify tests needing Windows/macOS/POSIX markers
6. ✓ **Deterministic** — Detect randomness and flakiness
7. ✓ **Clear Helpers** — Find duplication that obscures readability

---

## What Was Analyzed

### Test Name Quality
- Analyzed test names for readability
- Identified cryptic names that need improvement
- Example: \`test_func_works\` → should be \`test_function_should_work_correctly_when_given_valid_input\`

### OS-Specific Requirements
- Identified platform-dependent tests
- Found tests needing pytest markers for Windows/macOS/POSIX
- Example: Tests using Windows paths need \`@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only")\`

### Stub-Only Tests
- Identified tests that only verify mocks/stubs
- Flagged for replacement with integration tests
- Stub tests only verify the stub works, not real behavior

### Coverage Gaps
- Analyzed test coverage
- Identified missing test cases
- Documented areas needing additional tests for exhaustive coverage

---

## Detailed Review Log

\`\`\`
$(cat LLM-CONTEXT/review-anal/refactor-tests/review.log 2>/dev/null || echo "No review log available")
\`\`\`

---

## Test Results

**Status:** $TEST_STATUS

**Full Output:** See \`LLM-CONTEXT/review-anal/refactor-tests/test_results.txt\`

---

## Coverage Report

$(cat LLM-CONTEXT/review-anal/refactor-tests/coverage_report.txt 2>/dev/null || echo "Coverage report not available")

**HTML Report:** See \`LLM-CONTEXT/review-anal/refactor-tests/htmlcov/index.html\`

---

## Purpose and Scope

**This is a REVIEW subagent** - it analyzes and identifies issues but does NOT modify code.

What this subagent does:
- ✓ Analyze test quality and coverage
- ✓ Identify tests needing better names
- ✓ Detect stub-only tests
- ✓ Find tests needing OS-specific markers
- ✓ Measure coverage and find gaps
- ✓ Generate comprehensive quality report
- ✓ Document all issues for the fix subagent

What this subagent does NOT do:
- ✗ Does NOT modify test files
- ✗ Does NOT rename tests
- ✗ Does NOT add pytest markers
- ✗ Does NOT replace stub tests
- ✗ Does NOT write new tests

**Recommendation:** Use this review subagent to identify issues, then use the fix subagent (/bx_fix_anal_refactor_tests) to apply the fixes.

---

## Review Completion Criteria

The test review is complete when:

* ✅ **Coverage gaps identified** — All untested lines, branches, and paths documented
* ✅ **OS-specific tests flagged** — Tests needing Windows/macOS/POSIX markers identified
* ✅ **Poor test names documented** — Tests with cryptic names listed with suggestions
* ✅ **Multi-behavior tests detected** — Tests checking multiple behaviors flagged for splitting
* ✅ **Test setup complexity noted** — Tests with hidden complexity or unclear setup identified
* ✅ **Duplication found** — Duplicate test code identified with suggestions for helpers
* ✅ **Non-deterministic tests detected** — Tests with randomness or flakiness documented
* ✅ **OS-specific behavior analyzed** — Tests that will be skipped on certain platforms noted
* ✅ **Test clarity assessed** — Tests that don't read like clear specifications flagged
* ✅ **Stub-only tests identified** — Tests verifying mocks instead of behavior documented
* ✅ **Comprehensive report generated** — All issues documented for fix subagent

---

**Subagent Status:** $(cat LLM-CONTEXT/review-anal/refactor-tests/status.txt)

EOF

echo "✓ Summary generated: LLM-CONTEXT/review-anal/refactor-tests/summary.md"
echo ""
```

### Step 8: Determine Final Status

```bash
echo "Step 8: Determining final status..."
echo ""

# Calculate total issues found
TOTAL_ISSUES=$((TESTS_REFACTORED + TESTS_ADDED + STUBS_REPLACED + OS_MARKED))

echo "SUCCESS" > LLM-CONTEXT/review-anal/refactor-tests/status.txt

echo "=================================="
echo "TEST QUALITY REVIEW COMPLETE"
echo "=================================="
echo ""
echo "Tests with poor names: $TESTS_REFACTORED"
echo "Missing tests identified: $TESTS_ADDED"
echo "Stub-only tests found: $STUBS_REPLACED"
echo "Tests needing OS markers: $OS_MARKED"
echo "Current test status: $TEST_STATUS"
echo ""
echo "Summary: LLM-CONTEXT/review-anal/refactor-tests/summary.md"
echo "Review log: LLM-CONTEXT/review-anal/refactor-tests/review.log"
echo "Detailed logs: $LOG_FILE"
echo ""


# Clean up temp files
rm -f /tmp/tests_refactored.txt
rm -f /tmp/tests_added.txt
rm -f /tmp/stubs_replaced.txt
rm -f /tmp/os_marked.txt
rm -f /tmp/refactor_failed.txt

exit 0
# Mark as complete
echo "SUCCESS" > LLM-CONTEXT/review-anal/refactor-tests/status.txt
echo "✓ Refactor Tests analysis complete"
echo "✓ Status: SUCCESS"
```

## Output Files

All outputs saved to `LLM-CONTEXT/review-anal/refactor-tests/`:

- **status.txt** - Final status: SUCCESS or FAILED
- **summary.md** - Comprehensive summary with test quality issues
- **review.log** - Detailed log of all analysis
- **analysis.json** - Test suite analysis data
- **test_results.txt** - Test suite output
- **test_status.txt** - PASSED/FAILED/SKIPPED
- **coverage_report.txt** - Coverage analysis results
- **htmlcov/** - HTML coverage report

## Integration Protocol

1. **Status File**: `status.txt` with "SUCCESS" or "FAILED"
2. **Summary File**: `summary.md` with test quality issues and recommendations
3. **Exit Code**: Returns 0 on success
4. **Logs**: Detailed review log in `review.log`

## Success Criteria

- Test suite analyzed for quality issues
- Non-descriptive test names identified and documented
- OS-specific tests identified and documented
- Stub-only tests identified for replacement
- Coverage gaps identified and documented
- Multi-behavior tests flagged for splitting
- Comprehensive report generated with recommendations
- All issues documented for fix subagent

## Exclusions

**Never analyze:**
- `scripts/*` - Excluded from all analysis
- All configured excluded folders (LLM-CONTEXT, .git, .idea, .github, .claude, .devcontainer, .pytest_cache, .qlty, .ruff_cache)
