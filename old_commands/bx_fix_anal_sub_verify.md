# Verification Subagent: bx_fix_anal_sub_verify

## Purpose
**VERIFY WITH EVIDENCE, NOT ASSUMPTIONS.**

This subagent validates fixes through rigorous, repeatable testing with quantified measurements. No fix is accepted without concrete proof of improvement. Every claim must be backed by data, every test must run multiple times, and all evidence must be preserved.

## Core Principle
**DON'T TRUST - VERIFY WITH EVIDENCE**
- Run tests MULTIPLE times (3x) to detect flaky tests
- Measure ACTUAL metrics before/after, not assumptions
- Quantify ALL improvements with numbers and percentages
- Preserve ALL evidence files for audit trail
- FAIL verification if ANY evidence contradicts success

## Execution Steps

### Step 0: Initialize Evidence Directory
```bash
echo "Initializing verification with evidence collection..."
mkdir -p LLM-CONTEXT/fix-anal/verification/evidence
mkdir -p LLM-CONTEXT/fix-anal/logs
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

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
# Create status file immediately
echo "IN_PROGRESS" > LLM-CONTEXT/fix-anal/verification/status.txt


# Initialize status tracking
echo "IN_PROGRESS" > LLM-CONTEXT/fix-anal/verification/status.txt

# Create evidence directory structure
mkdir -p LLM-CONTEXT/fix-anal/verification/evidence/test_run_1
mkdir -p LLM-CONTEXT/fix-anal/verification/evidence/test_run_2
mkdir -p LLM-CONTEXT/fix-anal/verification/evidence/test_run_3
mkdir -p LLM-CONTEXT/fix-anal/verification/evidence/metrics
mkdir -p LLM-CONTEXT/fix-anal/verification/evidence/security

echo "Evidence collection initialized"
echo "✓ Status file initialized"
echo "✓ Python interpreter: $PYTHON_CMD"
echo ""
```

### Step 1: Load Baseline Metrics (Before Fixes)
**CRITICAL:** Load the baseline metrics captured by orchestrator BEFORE any fixes were applied.

```bash
echo "=========================================="
echo "STEP 1: Loading Baseline Metrics"
echo "=========================================="
echo ""

BASELINE_FILE="LLM-CONTEXT/fix-anal/metrics_before.json"

if [ ! -f "$BASELINE_FILE" ]; then
    echo "❌ VERIFICATION FAILED: No baseline metrics found!"
    echo "   Expected: $BASELINE_FILE"
    echo "   The orchestrator must capture baseline metrics BEFORE fixes."
    echo "FAILED" > LLM-CONTEXT/fix-anal/verification/status.txt
    exit 1
fi

echo "✓ Baseline metrics found: $BASELINE_FILE"
echo ""
echo "Baseline Metrics (BEFORE fixes):"
echo "--------------------------------"

$PYTHON_CMD << 'PYTHON_LOAD_BASELINE'
import json
from pathlib import Path

baseline_file = Path('LLM-CONTEXT/fix-anal/metrics_before.json')
baseline = json.loads(baseline_file.read_text())

print(f"  Function Count:         {baseline.get('function_count', 0)}")
print(f"  Long Functions (>50):   {baseline.get('long_functions', 0)}")
print(f"  Complex Functions (>10): {baseline.get('complex_functions', 0)}")
print(f"  Test Count:             {baseline.get('test_count', 0)}")
print(f"  Security Issues:        {baseline.get('security_issues', 0)}")
if baseline.get('test_coverage'):
    print(f"  Test Coverage:          {baseline['test_coverage']:.1f}%")
else:
    print(f"  Test Coverage:          Not available")

print(f"\n  Files Analyzed:         {baseline.get('files_analyzed', 0)}")
print(f"  Captured:               {baseline.get('timestamp', 'Unknown')}")
PYTHON_LOAD_BASELINE

echo ""
echo "Baseline loaded successfully."
echo ""
```

### Step 2: Detect Available Testing Tools
```bash
echo "=========================================="
echo "STEP 2: Detecting Testing Tools"
echo "=========================================="
echo ""

# Initialize tool detection results
PYTEST_AVAILABLE=false
NPM_AVAILABLE=false
GO_AVAILABLE=false
MAVEN_AVAILABLE=false
GRADLE_AVAILABLE=false
CARGO_AVAILABLE=false
RSPEC_AVAILABLE=false

# Detect Python/pytest
if command -v pytest >/dev/null 2>&1; then
    echo "✓ pytest found"
    PYTEST_AVAILABLE=true
elif command -v python3.13 >/dev/null 2>&1 && python3.13 -m pytest --version >/dev/null 2>&1; then
    echo "✓ pytest found (via python3.13)"
    PYTEST_AVAILABLE=true
elif command -v python >/dev/null 2>&1 && python -m pytest --version >/dev/null 2>&1; then
    echo "✓ pytest found (via python)"
    PYTEST_AVAILABLE=true
else
    echo "⚠ pytest not available"
fi

# Detect Node/npm
if [ -f "package.json" ] && command -v npm >/dev/null 2>&1; then
    if grep -q '"test"' package.json 2>/dev/null; then
        echo "✓ npm test script found"
        NPM_AVAILABLE=true
    else
        echo "⚠ npm found but no test script"
    fi
else
    echo "⚠ npm not available"
fi

# Detect Go
if [ -f "go.mod" ] && command -v go >/dev/null 2>&1; then
    echo "✓ go test available"
    GO_AVAILABLE=true
else
    echo "⚠ go test not available"
fi

# Detect Maven
if [ -f "pom.xml" ] && command -v mvn >/dev/null 2>&1; then
    echo "✓ maven test available"
    MAVEN_AVAILABLE=true
else
    echo "⚠ maven not available"
fi

# Detect Gradle
if [ -f "build.gradle" ] || [ -f "build.gradle.kts" ]; then
    if command -v gradle >/dev/null 2>&1; then
        echo "✓ gradle test available"
        GRADLE_AVAILABLE=true
    elif [ -f "gradlew" ]; then
        echo "✓ gradle wrapper available"
        GRADLE_AVAILABLE=true
    else
        echo "⚠ gradle not available"
    fi
else
    echo "⚠ gradle not available"
fi

# Detect Rust/Cargo
if [ -f "Cargo.toml" ] && command -v cargo >/dev/null 2>&1; then
    echo "✓ cargo test available"
    CARGO_AVAILABLE=true
else
    echo "⚠ cargo test not available"
fi

# Detect RSpec
if [ -f "Gemfile" ] && command -v rspec >/dev/null 2>&1; then
    echo "✓ rspec available"
    RSPEC_AVAILABLE=true
elif [ -f "Gemfile" ] && command -v bundle >/dev/null 2>&1; then
    if bundle exec rspec --version >/dev/null 2>&1; then
        echo "✓ rspec available (via bundle)"
        RSPEC_AVAILABLE=true
    else
        echo "⚠ rspec not available"
    fi
else
    echo "⚠ rspec not available"
fi

# Summary
TOOLS_FOUND=0
[ "$PYTEST_AVAILABLE" = true ] && TOOLS_FOUND=$((TOOLS_FOUND + 1))
[ "$NPM_AVAILABLE" = true ] && TOOLS_FOUND=$((TOOLS_FOUND + 1))
[ "$GO_AVAILABLE" = true ] && TOOLS_FOUND=$((TOOLS_FOUND + 1))
[ "$MAVEN_AVAILABLE" = true ] && TOOLS_FOUND=$((TOOLS_FOUND + 1))
[ "$GRADLE_AVAILABLE" = true ] && TOOLS_FOUND=$((TOOLS_FOUND + 1))
[ "$CARGO_AVAILABLE" = true ] && TOOLS_FOUND=$((TOOLS_FOUND + 1))
[ "$RSPEC_AVAILABLE" = true ] && TOOLS_FOUND=$((TOOLS_FOUND + 1))

echo ""
echo "Testing tools available: $TOOLS_FOUND"

if [ $TOOLS_FOUND -eq 0 ]; then
    echo ""
    echo "❌ VERIFICATION FAILED: No testing frameworks detected!"
    echo "   Cannot verify fixes without running tests."
    echo "FAILED" > LLM-CONTEXT/fix-anal/verification/status.txt
    exit 1
fi

echo ""
```

### Step 3: Run Tests Multiple Times (3x) - Detect Flaky Tests
**CRITICAL:** Run tests 3 times to detect unreliable tests. Flaky tests invalidate verification.

```bash
echo "=========================================="
echo "STEP 3: Running Tests Multiple Times"
echo "=========================================="
echo ""
echo "Running tests 3 times to detect flaky tests..."
echo ""

# Track test results across runs
declare -A test_results
RUN_1_STATUS="UNKNOWN"
RUN_2_STATUS="UNKNOWN"
RUN_3_STATUS="UNKNOWN"

# Function to run a single test execution
run_test_suite() {
    local RUN_NUM=$1
    local OUTPUT_DIR="LLM-CONTEXT/fix-anal/verification/evidence/test_run_${RUN_NUM}"

    echo "--- Test Run #${RUN_NUM} ---"
    echo "Output directory: $OUTPUT_DIR"
    echo ""

    ALL_PASSED=true

    # Python/pytest
    if [ "$PYTEST_AVAILABLE" = true ]; then
        echo "Running pytest (run ${RUN_NUM})..."
        if command -v pytest >/dev/null 2>&1; then
            pytest --verbose --tb=short --junit-xml="${OUTPUT_DIR}/pytest_results.xml" 2>&1 | tee "${OUTPUT_DIR}/pytest_output.txt"
        else
            $PYTHON_CMD -m pytest --verbose --tb=short --junit-xml="${OUTPUT_DIR}/pytest_results.xml" 2>&1 | tee "${OUTPUT_DIR}/pytest_output.txt"
        fi
        [ ${PIPESTATUS[0]} -ne 0 ] && ALL_PASSED=false
        echo ""
    fi

    # Node/npm
    if [ "$NPM_AVAILABLE" = true ]; then
        echo "Running npm test (run ${RUN_NUM})..."
        npm test 2>&1 | tee "${OUTPUT_DIR}/npm_output.txt"
        [ ${PIPESTATUS[0]} -ne 0 ] && ALL_PASSED=false
        echo ""
    fi

    # Ruby/RSpec
    if [ "$RSPEC_AVAILABLE" = true ]; then
        echo "Running rspec (run ${RUN_NUM})..."
        if command -v rspec >/dev/null 2>&1; then
            rspec --format progress --format json --out "${OUTPUT_DIR}/rspec_results.json" 2>&1 | tee "${OUTPUT_DIR}/rspec_output.txt"
        else
            bundle exec rspec --format progress --format json --out "${OUTPUT_DIR}/rspec_results.json" 2>&1 | tee "${OUTPUT_DIR}/rspec_output.txt"
        fi
        [ ${PIPESTATUS[0]} -ne 0 ] && ALL_PASSED=false
        echo ""
    fi

    # Go
    if [ "$GO_AVAILABLE" = true ]; then
        echo "Running go test (run ${RUN_NUM})..."
        go test ./... -v -race -coverprofile="${OUTPUT_DIR}/coverage.out" 2>&1 | tee "${OUTPUT_DIR}/go_output.txt"
        [ ${PIPESTATUS[0]} -ne 0 ] && ALL_PASSED=false
        echo ""
    fi

    # Maven
    if [ "$MAVEN_AVAILABLE" = true ]; then
        echo "Running maven test (run ${RUN_NUM})..."
        mvn clean test 2>&1 | tee "${OUTPUT_DIR}/maven_output.txt"
        [ ${PIPESTATUS[0]} -ne 0 ] && ALL_PASSED=false
        echo ""
    fi

    # Gradle
    if [ "$GRADLE_AVAILABLE" = true ]; then
        echo "Running gradle test (run ${RUN_NUM})..."
        if command -v gradle >/dev/null 2>&1; then
            gradle test 2>&1 | tee "${OUTPUT_DIR}/gradle_output.txt"
        else
            ./gradlew test 2>&1 | tee "${OUTPUT_DIR}/gradle_output.txt"
        fi
        [ ${PIPESTATUS[0]} -ne 0 ] && ALL_PASSED=false
        echo ""
    fi

    # Cargo
    if [ "$CARGO_AVAILABLE" = true ]; then
        echo "Running cargo test (run ${RUN_NUM})..."
        cargo test 2>&1 | tee "${OUTPUT_DIR}/cargo_output.txt"
        [ ${PIPESTATUS[0]} -ne 0 ] && ALL_PASSED=false
        echo ""
    fi

    if [ "$ALL_PASSED" = true ]; then
        echo "✓ Run ${RUN_NUM}: ALL TESTS PASSED"
        echo "PASSED" > "${OUTPUT_DIR}/status.txt"
        return 0
    else
        echo "✗ Run ${RUN_NUM}: TESTS FAILED"
        echo "FAILED" > "${OUTPUT_DIR}/status.txt"
        return 1
    fi
}

# Execute 3 test runs
echo "======================================"
run_test_suite 1
RUN_1_STATUS=$?
echo ""

echo "======================================"
run_test_suite 2
RUN_2_STATUS=$?
echo ""

echo "======================================"
run_test_suite 3
RUN_3_STATUS=$?
echo ""

# Analyze consistency across runs
echo "=========================================="
echo "Test Run Analysis"
echo "=========================================="
echo ""

PASSED_COUNT=0
[ $RUN_1_STATUS -eq 0 ] && PASSED_COUNT=$((PASSED_COUNT + 1))
[ $RUN_2_STATUS -eq 0 ] && PASSED_COUNT=$((PASSED_COUNT + 1))
[ $RUN_3_STATUS -eq 0 ] && PASSED_COUNT=$((PASSED_COUNT + 1))

echo "Results across 3 runs:"
[ $RUN_1_STATUS -eq 0 ] && echo "  Run 1: ✓ PASSED" || echo "  Run 1: ✗ FAILED"
[ $RUN_2_STATUS -eq 0 ] && echo "  Run 2: ✓ PASSED" || echo "  Run 2: ✗ FAILED"
[ $RUN_3_STATUS -eq 0 ] && echo "  Run 3: ✓ PASSED" || echo "  Run 3: ✗ FAILED"
echo ""
echo "Summary: ${PASSED_COUNT}/3 runs passed"
echo ""

# Determine reliability
if [ $PASSED_COUNT -eq 3 ]; then
    echo "✓ TEST RELIABILITY: RELIABLE (3/3 passed)"
    echo "  Tests are consistent and trustworthy."
    echo "PASSED" > LLM-CONTEXT/fix-anal/verification/test_reliability.txt
    TEST_STATUS="PASSED"
elif [ $PASSED_COUNT -eq 0 ]; then
    echo "✗ TEST RELIABILITY: CONSISTENTLY FAILING (0/3 passed)"
    echo "  All test runs failed - fixes did not work."
    echo "FAILED" > LLM-CONTEXT/fix-anal/verification/test_reliability.txt
    TEST_STATUS="FAILED"
else
    echo "⚠ TEST RELIABILITY: FLAKY (${PASSED_COUNT}/3 passed)"
    echo "  Tests are UNRELIABLE - inconsistent results detected!"
    echo "  Flaky tests invalidate verification."
    echo ""
    echo "❌ VERIFICATION FAILED: FLAKY TESTS DETECTED"
    echo "FLAKY" > LLM-CONTEXT/fix-anal/verification/test_reliability.txt
    TEST_STATUS="FLAKY"
fi

echo ""
echo "Evidence saved:"
echo "  - LLM-CONTEXT/fix-anal/verification/evidence/test_run_1/"
echo "  - LLM-CONTEXT/fix-anal/verification/evidence/test_run_2/"
echo "  - LLM-CONTEXT/fix-anal/verification/evidence/test_run_3/"
echo ""

# Store test status for final report
echo "$TEST_STATUS" > LLM-CONTEXT/fix-anal/verification/test_status.txt

if [ "$TEST_STATUS" = "FLAKY" ]; then
    echo "FAILED" > LLM-CONTEXT/fix-anal/verification/status.txt
    exit 1
fi

if [ "$TEST_STATUS" = "FAILED" ]; then
    echo "FAILED" > LLM-CONTEXT/fix-anal/verification/status.txt
    exit 1
fi

echo ""
```

### Step 4: Measure Metrics After Fixes
Capture actual measurements after fixes have been applied.

```bash
echo "=========================================="
echo "STEP 4: Measuring Metrics After Fixes"
echo "=========================================="
echo ""

$PYTHON_CMD << 'PYTHON_MEASURE_AFTER'
import json
import os
import re
from pathlib import Path
from datetime import datetime

metrics_after = {
    'timestamp': datetime.now().isoformat(),
    'function_count': 0,
    'long_functions': 0,
    'complex_functions': 0,
    'test_count': 0,
    'security_issues': 0,
    'test_coverage': None,
    'files_analyzed': 0
}

print("Analyzing codebase after fixes...")
print("")

# Analyze Python files
for root, dirs, files in os.walk('.'):
    # Skip non-source directories
    dirs[:] = [d for d in dirs if d not in [
        '.git', '.pytest_cache', '__pycache__', 'node_modules',
        '.tox', 'venv', 'env', '.venv', 'dist', 'build',
        'LLM-CONTEXT'
    ]]

    for file in files:
        if file.endswith('.py'):
            filepath = Path(root) / file
            try:
                content = filepath.read_text(encoding='utf-8', errors='ignore')
                metrics_after['files_analyzed'] += 1

                # Count functions
                func_matches = re.findall(r'^def\s+\w+\s*\(', content, re.MULTILINE)
                metrics_after['function_count'] += len(func_matches)

                # Count long functions (>50 lines)
                for match in re.finditer(r'^def\s+(\w+)\s*\([^)]*\):', content, re.MULTILINE):
                    func_start = match.start()
                    remaining = content[func_start:]

                    # Find next function or end of file
                    next_def = remaining.find('\ndef ', 1)
                    func_body = remaining if next_def == -1 else remaining[:next_def]

                    lines = func_body.count('\n')
                    if lines > 50:
                        metrics_after['long_functions'] += 1

                # Count test functions
                test_matches = re.findall(r'^def\s+test_\w+\s*\(', content, re.MULTILINE)
                metrics_after['test_count'] += len(test_matches)

            except Exception as e:
                pass

# Try to extract coverage from test runs
try:
    # Check for pytest coverage
    for run_dir in Path('LLM-CONTEXT/fix-anal/verification/evidence').glob('test_run_*'):
        coverage_file = run_dir / 'coverage.json'
        if coverage_file.exists():
            coverage_data = json.loads(coverage_file.read_text())
            if 'totals' in coverage_data:
                metrics_after['test_coverage'] = coverage_data['totals'].get('percent_covered')
                break
except:
    pass

# Security issues (if scanner ran)
try:
    security_dir = Path('LLM-CONTEXT/fix-anal/verification/evidence/security')
    if security_dir.exists():
        for sec_file in security_dir.glob('*.json'):
            data = json.loads(sec_file.read_text())
            if isinstance(data, dict) and 'vulnerabilities' in data:
                metrics_after['security_issues'] = len(data['vulnerabilities'])
            elif isinstance(data, list):
                metrics_after['security_issues'] = len(data)
            break
except:
    pass

# Save metrics
output_file = Path('LLM-CONTEXT/fix-anal/verification/evidence/metrics/metrics_after.json')
output_file.parent.mkdir(parents=True, exist_ok=True)
with open(output_file, 'w') as f:
    json.dump(metrics_after, f, indent=2)

print(f"✓ Metrics captured AFTER fixes:")
print(f"  Files Analyzed:          {metrics_after['files_analyzed']}")
print(f"  Function Count:          {metrics_after['function_count']}")
print(f"  Long Functions (>50):    {metrics_after['long_functions']}")
print(f"  Complex Functions (>10): {metrics_after['complex_functions']}")
print(f"  Test Count:              {metrics_after['test_count']}")
print(f"  Security Issues:         {metrics_after['security_issues']}")
if metrics_after['test_coverage'] is not None:
    print(f"  Test Coverage:           {metrics_after['test_coverage']:.1f}%")
else:
    print(f"  Test Coverage:           Not available")
print("")
print(f"Saved: {output_file}")

PYTHON_MEASURE_AFTER

echo ""
```

### Step 5: Run Security Scanner (If Available)
```bash
echo "=========================================="
echo "STEP 5: Security Scanning"
echo "=========================================="
echo ""

SECURITY_DIR="LLM-CONTEXT/fix-anal/verification/evidence/security"
mkdir -p "$SECURITY_DIR"

echo "Running security scanners..."
echo ""

SECURITY_SCAN_RAN=false

# npm audit
if [ -f "package.json" ] && command -v npm >/dev/null 2>&1; then
    echo "Running npm audit..."
    npm audit --json > "$SECURITY_DIR/npm_audit.json" 2>&1 || true
    SECURITY_SCAN_RAN=true
    echo "✓ npm audit completed"
fi

# pip safety check (if available)
if command -v safety >/dev/null 2>&1; then
    echo "Running safety check..."
    safety check --json > "$SECURITY_DIR/safety_check.json" 2>&1 || true
    SECURITY_SCAN_RAN=true
    echo "✓ safety check completed"
fi

# bundle audit
if [ -f "Gemfile" ] && command -v bundle >/dev/null 2>&1; then
    echo "Running bundle audit..."
    bundle audit check --format json > "$SECURITY_DIR/bundle_audit.json" 2>&1 || true
    SECURITY_SCAN_RAN=true
    echo "✓ bundle audit completed"
fi

# cargo audit
if [ -f "Cargo.toml" ] && command -v cargo-audit >/dev/null 2>&1; then
    echo "Running cargo audit..."
    cargo audit --json > "$SECURITY_DIR/cargo_audit.json" 2>&1 || true
    SECURITY_SCAN_RAN=true
    echo "✓ cargo audit completed"
fi

# semgrep (if available)
if command -v semgrep >/dev/null 2>&1; then
    echo "Running semgrep..."
    semgrep --config=auto --json > "$SECURITY_DIR/semgrep_results.json" 2>&1 || true
    SECURITY_SCAN_RAN=true
    echo "✓ semgrep completed"
fi

if [ "$SECURITY_SCAN_RAN" = false ]; then
    echo "⚠ No security scanners available - skipping security scan"
    echo "NOT_AVAILABLE" > "$SECURITY_DIR/status.txt"
else
    echo ""
    echo "✓ Security scans completed"
    echo "COMPLETED" > "$SECURITY_DIR/status.txt"
fi

echo ""
```

### Step 6: Evidence-Based Comparison
**CRITICAL:** Compare actual measurements before/after. Calculate improvements.

```bash
echo "=========================================="
echo "STEP 6: Evidence-Based Comparison"
echo "=========================================="
echo ""

$PYTHON_CMD << 'PYTHON_COMPARE_EVIDENCE'
import json
from pathlib import Path
from datetime import datetime

# Load before/after metrics
before_file = Path('LLM-CONTEXT/fix-anal/metrics_before.json')
after_file = Path('LLM-CONTEXT/fix-anal/verification/evidence/metrics/metrics_after.json')

if not before_file.exists():
    print("❌ ERROR: Baseline metrics not found!")
    exit(1)

if not after_file.exists():
    print("❌ ERROR: After metrics not found!")
    exit(1)

before = json.loads(before_file.read_text())
after = json.loads(after_file.read_text())

print("=" * 70)
print("EVIDENCE-BASED COMPARISON: BEFORE → AFTER")
print("=" * 70)
print()

# Calculate deltas and percentages
comparisons = []
has_regression = False

# Function count (neutral metric)
func_delta = after['function_count'] - before['function_count']
comparisons.append({
    'metric': 'Function Count',
    'before': before['function_count'],
    'after': after['function_count'],
    'delta': func_delta,
    'status': 'INFO'
})
print(f"Function Count:           {before['function_count']:4d} → {after['function_count']:4d}  ({func_delta:+4d})  [INFO]")

# Long functions (improvement = reduction)
long_delta = after['long_functions'] - before['long_functions']
long_pct_change = (long_delta / before['long_functions'] * 100) if before['long_functions'] > 0 else 0
if long_delta < 0:
    long_status = "IMPROVED"
elif long_delta > 0:
    long_status = "REGRESSION"
    has_regression = True
else:
    long_status = "UNCHANGED"
comparisons.append({
    'metric': 'Long Functions (>50 lines)',
    'before': before['long_functions'],
    'after': after['long_functions'],
    'delta': long_delta,
    'percent_change': long_pct_change,
    'status': long_status
})
print(f"Long Functions (>50):     {before['long_functions']:4d} → {after['long_functions']:4d}  ({long_delta:+4d})  [{long_status}]")
if long_delta != 0 and before['long_functions'] > 0:
    print(f"                          ({long_pct_change:+.1f}% change)")

# Complex functions (improvement = reduction)
complex_delta = after['complex_functions'] - before['complex_functions']
complex_pct_change = (complex_delta / before['complex_functions'] * 100) if before['complex_functions'] > 0 else 0
if complex_delta < 0:
    complex_status = "IMPROVED"
elif complex_delta > 0:
    complex_status = "REGRESSION"
    has_regression = True
else:
    complex_status = "UNCHANGED"
comparisons.append({
    'metric': 'Complex Functions (>10)',
    'before': before['complex_functions'],
    'after': after['complex_functions'],
    'delta': complex_delta,
    'percent_change': complex_pct_change,
    'status': complex_status
})
print(f"Complex Functions (>10):  {before['complex_functions']:4d} → {after['complex_functions']:4d}  ({complex_delta:+4d})  [{complex_status}]")
if complex_delta != 0 and before['complex_functions'] > 0:
    print(f"                          ({complex_pct_change:+.1f}% change)")

# Test count (improvement = increase)
test_delta = after['test_count'] - before['test_count']
test_pct_change = (test_delta / before['test_count'] * 100) if before['test_count'] > 0 else 0
if test_delta > 0:
    test_status = "IMPROVED"
elif test_delta < 0:
    test_status = "REGRESSION"
    has_regression = True
else:
    test_status = "UNCHANGED"
comparisons.append({
    'metric': 'Test Count',
    'before': before['test_count'],
    'after': after['test_count'],
    'delta': test_delta,
    'percent_change': test_pct_change,
    'status': test_status
})
print(f"Test Count:               {before['test_count']:4d} → {after['test_count']:4d}  ({test_delta:+4d})  [{test_status}]")
if test_delta != 0 and before['test_count'] > 0:
    print(f"                          ({test_pct_change:+.1f}% change)")

# Security issues (improvement = reduction)
security_delta = after['security_issues'] - before['security_issues']
if security_delta < 0:
    security_status = "IMPROVED"
elif security_delta > 0:
    security_status = "REGRESSION"
    has_regression = True
else:
    security_status = "UNCHANGED"
comparisons.append({
    'metric': 'Security Issues',
    'before': before['security_issues'],
    'after': after['security_issues'],
    'delta': security_delta,
    'status': security_status
})
print(f"Security Issues:          {before['security_issues']:4d} → {after['security_issues']:4d}  ({security_delta:+4d})  [{security_status}]")

# Test coverage (improvement = increase)
if before.get('test_coverage') is not None and after.get('test_coverage') is not None:
    coverage_delta = after['test_coverage'] - before['test_coverage']
    if coverage_delta > 0:
        coverage_status = "IMPROVED"
    elif coverage_delta < 0:
        coverage_status = "REGRESSION"
        has_regression = True
    else:
        coverage_status = "UNCHANGED"
    comparisons.append({
        'metric': 'Test Coverage',
        'before': before['test_coverage'],
        'after': after['test_coverage'],
        'delta': coverage_delta,
        'status': coverage_status
    })
    print(f"Test Coverage:           {before['test_coverage']:5.1f}% → {after['test_coverage']:5.1f}%  ({coverage_delta:+.1f}%)  [{coverage_status}]")

print()
print("=" * 70)
print()

# Regression check
if has_regression:
    print("⚠ WARNING: METRICS REGRESSION DETECTED!")
    print("   One or more metrics got worse after fixes.")
    print()

# Save comparison
comparison_data = {
    'timestamp': datetime.now().isoformat(),
    'before': before,
    'after': after,
    'comparisons': comparisons,
    'has_regression': has_regression
}

comp_file = Path('LLM-CONTEXT/fix-anal/verification/evidence/metrics/comparison.json')
with open(comp_file, 'w') as f:
    json.dump(comparison_data, f, indent=2)

print(f"✓ Comparison saved: {comp_file}")
print()

# Exit with error if regression detected
if has_regression:
    exit(1)

PYTHON_COMPARE_EVIDENCE

COMPARISON_STATUS=$?

if [ $COMPARISON_STATUS -ne 0 ]; then
    echo "❌ VERIFICATION FAILED: Metrics regression detected!"
    echo "FAILED" > LLM-CONTEXT/fix-anal/verification/status.txt
    exit 1
fi

echo "✓ No metrics regression detected"
echo ""
```

### Step 7: Generate Evidence Report
Create comprehensive report with all evidence and measurements.

```bash
echo "=========================================="
echo "STEP 7: Generating Evidence Report"
echo "=========================================="
echo ""

$PYTHON_CMD << 'PYTHON_GENERATE_REPORT'
import json
from pathlib import Path
from datetime import datetime

# Load all evidence
before = json.loads(Path('LLM-CONTEXT/fix-anal/metrics_before.json').read_text())
after = json.loads(Path('LLM-CONTEXT/fix-anal/verification/evidence/metrics/metrics_after.json').read_text())
comparison = json.loads(Path('LLM-CONTEXT/fix-anal/verification/evidence/metrics/comparison.json').read_text())

# Load test status
test_status = Path('LLM-CONTEXT/fix-anal/verification/test_status.txt').read_text().strip()
test_reliability = Path('LLM-CONTEXT/fix-anal/verification/test_reliability.txt').read_text().strip()

# Check for test run evidence
test_run_1 = Path('LLM-CONTEXT/fix-anal/verification/evidence/test_run_1')
test_run_2 = Path('LLM-CONTEXT/fix-anal/verification/evidence/test_run_2')
test_run_3 = Path('LLM-CONTEXT/fix-anal/verification/evidence/test_run_3')

# Generate report
report = []
report.append("# VERIFICATION EVIDENCE REPORT")
report.append("")
report.append(f"**Generated:** {datetime.now().isoformat()}")
report.append(f"**Repository:** {Path.cwd().absolute()}")
report.append("")
report.append("---")
report.append("")

# Test Reliability Section
report.append("## Test Reliability")
report.append("")
report.append("**CRITICAL:** Tests were run 3 times to detect flaky tests.")
report.append("")
report.append(f"**Test Reliability Status:** {test_reliability}")
report.append(f"**Final Test Status:** {test_status}")
report.append("")

if test_run_1.exists() and test_run_2.exists() and test_run_3.exists():
    run1_status = (test_run_1 / 'status.txt').read_text().strip() if (test_run_1 / 'status.txt').exists() else 'UNKNOWN'
    run2_status = (test_run_2 / 'status.txt').read_text().strip() if (test_run_2 / 'status.txt').exists() else 'UNKNOWN'
    run3_status = (test_run_3 / 'status.txt').read_text().strip() if (test_run_3 / 'status.txt').exists() else 'UNKNOWN'

    report.append("### Multiple Test Run Results:")
    report.append(f"- **Run 1:** {run1_status}")
    report.append(f"- **Run 2:** {run2_status}")
    report.append(f"- **Run 3:** {run3_status}")
    report.append("")

    passed_count = sum(1 for status in [run1_status, run2_status, run3_status] if status == 'PASSED')
    report.append(f"**Reliability:** {passed_count}/3 runs passed")
    report.append("")

    if passed_count == 3:
        report.append("✓ Tests are RELIABLE - consistent pass rate across all runs")
    elif passed_count == 0:
        report.append("✗ Tests are CONSISTENTLY FAILING - all runs failed")
    else:
        report.append("⚠ Tests are FLAKY - inconsistent results detected!")
        report.append("  **VERIFICATION FAILED DUE TO FLAKY TESTS**")
    report.append("")

report.append("**Evidence Files:**")
report.append("- `evidence/test_run_1/` - First test execution")
report.append("- `evidence/test_run_2/` - Second test execution")
report.append("- `evidence/test_run_3/` - Third test execution")
report.append("")
report.append("---")
report.append("")

# Metrics Comparison Section
report.append("## Metrics Comparison: BEFORE → AFTER")
report.append("")
report.append("**Principle:** Verify with quantified measurements, not assumptions.")
report.append("")

report.append("### Baseline (BEFORE Fixes)")
report.append(f"- Function Count: {before['function_count']}")
report.append(f"- Long Functions (>50 lines): {before['long_functions']}")
report.append(f"- Complex Functions (>10): {before['complex_functions']}")
report.append(f"- Test Count: {before['test_count']}")
report.append(f"- Security Issues: {before['security_issues']}")
if before.get('test_coverage'):
    report.append(f"- Test Coverage: {before['test_coverage']:.1f}%")
report.append(f"- Files Analyzed: {before['files_analyzed']}")
report.append(f"- Captured: {before['timestamp']}")
report.append("")

report.append("### Measurements (AFTER Fixes)")
report.append(f"- Function Count: {after['function_count']}")
report.append(f"- Long Functions (>50 lines): {after['long_functions']}")
report.append(f"- Complex Functions (>10): {after['complex_functions']}")
report.append(f"- Test Count: {after['test_count']}")
report.append(f"- Security Issues: {after['security_issues']}")
if after.get('test_coverage'):
    report.append(f"- Test Coverage: {after['test_coverage']:.1f}%")
report.append(f"- Files Analyzed: {after['files_analyzed']}")
report.append(f"- Captured: {after['timestamp']}")
report.append("")

report.append("### Quantified Changes")
report.append("")
report.append("| Metric | Before | After | Change | Status |")
report.append("|--------|--------|-------|--------|--------|")

for comp in comparison['comparisons']:
    metric = comp['metric']
    before_val = comp['before']
    after_val = comp['after']
    delta = comp['delta']
    status = comp['status']

    if 'Coverage' in metric and isinstance(before_val, float):
        report.append(f"| {metric} | {before_val:.1f}% | {after_val:.1f}% | {delta:+.1f}% | {status} |")
    else:
        report.append(f"| {metric} | {before_val} | {after_val} | {delta:+d} | {status} |")

report.append("")

if comparison.get('has_regression'):
    report.append("⚠ **WARNING: METRICS REGRESSION DETECTED**")
    report.append("")
    report.append("One or more metrics degraded after fixes. This indicates:")
    report.append("- Fixes may have introduced new issues")
    report.append("- Code quality decreased in some areas")
    report.append("- Further investigation required")
    report.append("")
else:
    report.append("✓ **NO REGRESSIONS:** All metrics improved or maintained")
    report.append("")

report.append("**Evidence Files:**")
report.append("- `evidence/metrics/metrics_after.json` - Post-fix measurements")
report.append("- `evidence/metrics/comparison.json` - Before/after comparison")
report.append("- `../metrics_before.json` - Baseline measurements")
report.append("")
report.append("---")
report.append("")

# Security Section
report.append("## Security Verification")
report.append("")

security_dir = Path('LLM-CONTEXT/fix-anal/verification/evidence/security')
if security_dir.exists() and list(security_dir.glob('*.json')):
    report.append("Security scanners executed:")
    for sec_file in sorted(security_dir.glob('*.json')):
        report.append(f"- `{sec_file.name}`")
    report.append("")
    report.append("**Evidence Files:**")
    report.append("- `evidence/security/` - All security scan results")
else:
    report.append("⚠ No security scanners available - security scan skipped")
report.append("")
report.append("---")
report.append("")

# Final Verdict
report.append("## Final Verdict")
report.append("")

# Determine overall status
verification_passed = True
failure_reasons = []

if test_status != "PASSED":
    verification_passed = False
    if test_status == "FLAKY":
        failure_reasons.append("Tests are flaky (inconsistent results)")
    else:
        failure_reasons.append("Tests failed")

if comparison.get('has_regression'):
    verification_passed = False
    failure_reasons.append("Metrics regression detected")

if verification_passed:
    report.append("### ✓ VERIFICATION PASSED")
    report.append("")
    report.append("**Evidence Summary:**")
    report.append("- Tests passed reliably (3/3 runs)")
    report.append("- No flaky tests detected")
    report.append("- Metrics improved or maintained")
    report.append("- No regressions detected")
    report.append("")
    report.append("**All fixes verified with concrete evidence.**")
    verification_status = "PASSED"
else:
    report.append("### ✗ VERIFICATION FAILED")
    report.append("")
    report.append("**Failure Reasons:**")
    for reason in failure_reasons:
        report.append(f"- {reason}")
    report.append("")
    report.append("**Fixes did not meet verification standards.**")
    verification_status = "FAILED"

report.append("")
report.append("---")
report.append("")
report.append("## Evidence Archive")
report.append("")
report.append("All evidence preserved in: `LLM-CONTEXT/fix-anal/verification/evidence/`")
report.append("")
report.append("**Directory Structure:**")
report.append("```")
report.append("evidence/")
report.append("├── test_run_1/          # First test execution")
report.append("├── test_run_2/          # Second test execution")
report.append("├── test_run_3/          # Third test execution")
report.append("├── metrics/")
report.append("│   ├── metrics_after.json")
report.append("│   └── comparison.json")
report.append("└── security/            # Security scan results")
report.append("```")
report.append("")
report.append("**Principle:** Evidence, not assumptions. Measurements, not claims.")
report.append("")

# Save report
report_file = Path('LLM-CONTEXT/fix-anal/verification/VERIFICATION_REPORT.md')
report_file.write_text('\n'.join(report))

print(f"✓ Evidence report generated: {report_file}")
print()
print("=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)
print()
print(f"Final Status: {verification_status}")
print()
print(f"Full report: {report_file}")
print()

# Save final status (Integration Protocol: use status.txt not status.txt)
status_file = Path('LLM-CONTEXT/fix-anal/verification/status.txt')
status_file.write_text(verification_status)

# Exit with appropriate code
exit(0 if verification_status == "PASSED" else 1)

PYTHON_GENERATE_REPORT

FINAL_STATUS=$?

if [ $FINAL_STATUS -eq 0 ]; then
else
fi

echo ""
echo "Verification process complete."
echo "Detailed logs: $LOG_FILE"
echo ""


exit $FINAL_STATUS
# Mark as complete
echo "SUCCESS" > LLM-CONTEXT/fix-anal/verification/status.txt
echo "✓ Verify analysis complete"
echo "✓ Status: SUCCESS"
```

## Verification Principles

### ALWAYS DO THESE THINGS
1. **ALWAYS load baseline metrics** - Compare against actual before state
2. **ALWAYS run tests 3 times** - Detect flaky/unreliable tests
3. **ALWAYS measure actual metrics** - Don't assume or estimate
4. **ALWAYS calculate deltas** - Show quantified improvements
5. **ALWAYS preserve evidence** - Save all test runs and measurements
6. **ALWAYS fail on flaky tests** - Unreliable tests invalidate verification
7. **ALWAYS fail on regressions** - Metrics must improve or stay same

### NEVER DO THESE THINGS
1. **NEVER trust tests without multiple runs** - One pass doesn't prove reliability
2. **NEVER assume metrics improved** - Always measure and compare
3. **NEVER accept flaky tests** - Inconsistent results = verification failure
4. **NEVER ignore regressions** - Any metric degradation fails verification
5. **NEVER delete evidence** - All test runs must be preserved
6. **NEVER claim success without numbers** - Every claim needs quantified proof
7. **NEVER skip baseline comparison** - Must compare before/after

## Evidence Requirements

**For PASS verdict, must provide:**
- ✓ Tests passed 3/3 runs (reliable)
- ✓ No flaky tests detected
- ✓ Baseline metrics loaded
- ✓ After metrics measured
- ✓ Before/after comparison with deltas
- ✓ No metrics regressions
- ✓ All evidence files saved

**Automatic FAIL if:**
- ✗ Tests flaky (1-2/3 runs passed)
- ✗ Tests consistently fail (0/3 runs passed)
- ✗ Any metric regressed (got worse)
- ✗ Baseline metrics missing
- ✗ Cannot measure after metrics

## Key Principle
**DON'T TRUST - VERIFY WITH EVIDENCE**

Every claim must be backed by:
- Multiple test runs (not just one)
- Actual measurements (not assumptions)
- Quantified improvements (not claims)
- Preserved evidence (not just logs)

No fix is accepted without proof.
