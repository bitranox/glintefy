# Fix Findings - Planning Sub-Agent

## Purpose

Parse all findings from bx_review_anal and create a comprehensive, prioritized fix plan. This planner determines WHAT needs to be fixed, in WHAT order, estimates the effort required, and defines ACTIONABLE fix strategies with evidence requirements.

## Key Enhancement: Actionable Fix Plans

This subagent now creates **fully actionable** fix plans by adding to each issue:

1. **Fix Strategy** - Specific implementation steps (not vague "fix it")
2. **Evidence Before** - What to measure/capture before fixing
3. **Evidence After** - How to verify the fix worked
4. **Success Criteria** - Quantifiable metrics (e.g., "reduce to <50 lines", "vulnerabilities decrease by >=1")
5. **Rollback Trigger** - Clear conditions for reverting (e.g., "if tests fail OR coverage decreases")

### Example Output

```json
{
  "issue_id": "SEC_CRI_001",
  "category": "security",
  "severity": "CRITICAL",
  "description": "SQL injection vulnerability in user login",
  "file": "auth/login.py",
  "line": "45",
  "fix_strategy": "Replace f-string SQL query with parameterized query using cursor.execute(sql, params)",
  "evidence_before": [
    "Run bandit -t B608 on auth/login.py",
    "Count SQL injection issues",
    "Document exact vulnerability location"
  ],
  "evidence_after": [
    "Re-run bandit -t B608",
    "Verify SQL injection count = 0",
    "Run database tests 3x"
  ],
  "success_criteria": "SQL injection count = 0 AND database tests pass 3/3 runs",
  "rollback_trigger": "Database tests fail OR new security issues detected"
}
```

This makes the plan **actionable** - other subagents know exactly:
- What to do (specific code changes)
- How to verify it worked (evidence)
- When to keep or revert (success criteria & rollback triggers)

## Responsibilities

1. Read the final review report from bx_review_anal
2. Parse findings from all subagents (scope, deps, quality, security, perf, cache, docs, cicd)
3. Categorize issues by severity: CRITICAL → MAJOR → MINOR
4. Determine fixing order respecting dependencies
5. Estimate complexity and risk for each fix
6. **Define fix strategies and evidence requirements for each issue** (NEW)
7. Generate comprehensive fix plan with actionable strategies

## Execution Steps

### Step 0: Initialize Directory Structure

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

mkdir -p LLM-CONTEXT/fix-anal/plan
mkdir -p LLM-CONTEXT/fix-anal/logs

# Create status file immediately with IN_PROGRESS
echo "IN_PROGRESS" > LLM-CONTEXT/fix-anal/plan/status.txt

# Load Python interpreter path from orchestrator
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



# Initialize status tracking
echo "IN_PROGRESS" > LLM-CONTEXT/fix-anal/plan/status.txt
echo "✓ Plan directory created"
echo "✓ Status file initialized"
echo "✓ Logging initialized: $LOG_FILE"
echo "✓ Python interpreter: $PYTHON_CMD"

# Error handling - exit on any error
set -e
trap 'handle_error $? $LINENO' ERR

handle_error() {
    local exit_code=$1
    local line_num=$2
    echo "FAILED" > LLM-CONTEXT/fix-anal/plan/status.txt
    echo "❌ Plan analysis failed - check logs for details"
    cat > LLM-CONTEXT/fix-anal/plan/ERROR.txt << EOF
Error occurred in Plan subagent
Exit code: $exit_code
Failed at line: $line_num
Time: $(date -Iseconds)
Check log file: LLM-CONTEXT/fix-anal/logs/plan.log
EOF
    exit $exit_code
}
```

### Step 1: Read Review Report

```bash
echo "Reading review report..."

if [ ! -f "LLM-CONTEXT/review-anal/report/review_report.md" ]; then
    echo "ERROR: Review report not found at LLM-CONTEXT/review-anal/report/review_report.md"
    echo "Run /bx_review_anal first"
    echo "FAILED" > LLM-CONTEXT/fix-anal/plan/status.txt
    exit 1
fi

# Copy report for reference
cp LLM-CONTEXT/review-anal/report/review_report.md LLM-CONTEXT/fix-anal/plan/review_report_snapshot.md

echo "✓ Review report loaded"
```

### Step 2: Extract and Categorize Issues

```bash

cat > LLM-CONTEXT/fix-anal/plan/extract_issues.py << 'EOF'
import re
import json
import sys
from pathlib import Path
from datetime import datetime

# Initialize error logging for Python script
LOG_FILE = Path('LLM-CONTEXT/fix-anal/logs/plan.log')

def log_error(message):
    timestamp = datetime.now().isoformat()
    log_msg = f"[{timestamp}] ERROR (extract_issues.py): {message}\n"
    print(log_msg, file=sys.stderr, end='')
    with open(LOG_FILE, 'a') as f:
        f.write(log_msg)

def log_info(message):
    timestamp = datetime.now().isoformat()
    log_msg = f"[{timestamp}] INFO (extract_issues.py): {message}\n"
    print(log_msg, end='')
    with open(LOG_FILE, 'a') as f:
        f.write(log_msg)

def extract_security_issues():
    """Extract security issues from security report."""
    try:
        security_file = Path('LLM-CONTEXT/review-anal/security/security_analysis_report.md')
        if not security_file.exists():
            print("⚠ Security report not found - skipping security issues")
            return []


        content = security_file.read_text()
        issues = []

        # Extract HIGH/CRITICAL severity issues
        high_pattern = r'Severity:\s*(HIGH|CRITICAL).*?(?=Severity:|$)'
        matches = re.finditer(high_pattern, content, re.DOTALL | re.IGNORECASE)

        for match in matches:
            issue_text = match.group(0)
            # Extract file and line if present
            file_match = re.search(r'File:\s*([^\n]+)', issue_text)
            line_match = re.search(r'Line:\s*(\d+)', issue_text)

            issues.append({
                'category': 'security',
                'severity': 'CRITICAL',
                'file': file_match.group(1).strip() if file_match else 'Unknown',
                'line': line_match.group(1) if line_match else None,
                'description': issue_text[:200],
                'complexity': 'high'
            })

        return issues
    except Exception as e:
        print(f"ERROR parsing security issues: {e}")
        return []

def extract_quality_issues():
    """Extract quality issues from quality report."""
    try:
        quality_file = Path('LLM-CONTEXT/review-anal/quality/refactoring_recommendations.md')
        if not quality_file.exists():
            print("⚠ Quality report not found - skipping quality issues")
            return []


        content = quality_file.read_text()
        issues = []

        # Extract functions >50 lines
        long_func_pattern = r'Function:\s*([^\n]+).*?Lines:\s*(\d+)'
        for match in re.finditer(long_func_pattern, content, re.DOTALL):
            func_name = match.group(1).strip()
            lines = int(match.group(2))

            issues.append({
                'category': 'quality',
                'severity': 'MAJOR',
                'type': 'long_function',
                'function': func_name,
                'lines': lines,
                'description': f'Function {func_name} is {lines} lines (max: 50)',
                'complexity': 'medium'
            })

        # Extract complex functions
        complex_pattern = r'Complexity:\s*(\d+)'
        for match in re.finditer(complex_pattern, content):
            complexity = int(match.group(1))
            if complexity > 10:
                issues.append({
                    'category': 'quality',
                    'severity': 'MAJOR',
                    'type': 'high_complexity',
                    'complexity_value': complexity,
                    'description': f'Function has complexity {complexity} (max: 10)',
                    'complexity': 'medium'
                })

        # Extract duplication
        dup_pattern = r'Duplication.*?(\d+)\s+lines'
        for match in re.finditer(dup_pattern, content, re.IGNORECASE):
            dup_lines = int(match.group(1))
            issues.append({
                'category': 'quality',
                'severity': 'MAJOR',
                'type': 'duplication',
                'lines': dup_lines,
                'description': f'Code duplication: {dup_lines} lines',
                'complexity': 'low'
            })

        return issues
    except Exception as e:
        print(f"ERROR parsing quality issues: {e}")
        return []

def extract_docs_issues():
    """Extract documentation issues from docs report."""
    try:
        docs_file = Path('LLM-CONTEXT/review-anal/docs/documentation_analysis.txt')
        if not docs_file.exists():
            print("⚠ Documentation report not found - skipping doc issues")
            return []

        content = docs_file.read_text()
        issues = []

        # Extract missing docstrings
        missing_pattern = r'Missing docstring.*?([^\n]+\.py).*?line\s*(\d+)'
        for match in re.finditer(missing_pattern, content, re.IGNORECASE):
            file_path = match.group(1)
            line_num = match.group(2)

            issues.append({
                'category': 'docs',
                'severity': 'MINOR',
                'type': 'missing_docstring',
                'file': file_path,
                'line': line_num,
                'description': f'Missing docstring in {file_path}:{line_num}',
                'complexity': 'low'
            })

        return issues
    except Exception as e:
        print(f"ERROR parsing documentation issues: {e}")
        return []

def extract_test_failures():
    """Extract test failures from deps report."""
    try:
        deps_file = Path('LLM-CONTEXT/review-anal/deps/test_results.txt')
        if not deps_file.exists():
            print("⚠ Test results not found - skipping test failure issues")
            return []

        content = deps_file.read_text()
        issues = []

        # Check if tests failed
        if 'FAILED' in content or 'ERROR' in content:
            issues.append({
                'category': 'tests',
                'severity': 'CRITICAL',
                'type': 'test_failure',
                'description': 'Tests failing after dependency updates',
                'complexity': 'high'
            })

        return issues
    except Exception as e:
        print(f"ERROR parsing test failures: {e}")
        return []

def extract_performance_issues():
    """Extract performance issues from performance report."""
    try:
        perf_file = Path('LLM-CONTEXT/review-anal/perf/performance_analysis_report.md')
        if not perf_file.exists():
            print("⚠ Performance report not found - skipping performance issues")
            return []

        content = perf_file.read_text()
        issues = []

        # Extract slow operations, inefficient algorithms
        slow_pattern = r'SLOW:.*?File:\s*([^\n]+).*?Line:\s*(\d+)'
        matches = re.finditer(slow_pattern, content, re.DOTALL)

        for match in matches:
            issues.append({
                'category': 'performance',
                'severity': 'MAJOR',
                'file': match.group(1).strip(),
                'line': match.group(2),
                'description': match.group(0)[:200],
                'complexity': 'medium'
            })

        # Extract inefficient algorithm patterns
        inefficient_pattern = r'Inefficient.*?File:\s*([^\n]+).*?Line:\s*(\d+)'
        matches = re.finditer(inefficient_pattern, content, re.DOTALL | re.IGNORECASE)

        for match in matches:
            issues.append({
                'category': 'performance',
                'severity': 'MAJOR',
                'file': match.group(1).strip(),
                'line': match.group(2),
                'description': match.group(0)[:200],
                'complexity': 'medium'
            })

        return issues
    except Exception as e:
        print(f"ERROR parsing performance issues: {e}")
        return []

def categorize_by_severity(issues):
    """Group issues by severity."""
    critical = [i for i in issues if i['severity'] == 'CRITICAL']
    major = [i for i in issues if i['severity'] == 'MAJOR']
    minor = [i for i in issues if i['severity'] == 'MINOR']

    return {
        'critical': critical,
        'major': major,
        'minor': minor
    }

if __name__ == '__main__':
    all_issues = []

    try:
        # Extract from all sources
        all_issues.extend(extract_security_issues())
        all_issues.extend(extract_quality_issues())
        all_issues.extend(extract_docs_issues())
        all_issues.extend(extract_test_failures())
        all_issues.extend(extract_performance_issues())
    except Exception as e:
        sys.exit(1)

    # Categorize by severity
    categorized = categorize_by_severity(all_issues)

    # Save to JSON
    with open('LLM-CONTEXT/fix-anal/plan/issues.json', 'w') as f:
        json.dump(categorized, f, indent=2)


    # Print summary
    print(f"Issues extracted:")
    print(f"  CRITICAL: {len(categorized['critical'])}")
    print(f"  MAJOR: {len(categorized['major'])}")
    print(f"  MINOR: {len(categorized['minor'])}")
    print(f"  TOTAL: {len(all_issues)}")
EOF

$PYTHON_CMD LLM-CONTEXT/fix-anal/plan/extract_issues.py 2>&1 | tee -a "$LOG_FILE"

if [ ${PIPESTATUS[0]} -ne 0 ]; then
    echo "FAILED" > LLM-CONTEXT/fix-anal/plan/status.txt
    exit 1
fi

```

**NOTE:** All Python scripts in this subagent include comprehensive error handling to prevent crashes and provide helpful error messages.

```bash
```

### Step 3: Create Fixing Order

```bash
cat > LLM-CONTEXT/fix-anal/plan/create_order.py << 'EOF'
import json

def create_fix_order():
    """Create fixing order respecting dependencies."""
    with open('LLM-CONTEXT/fix-anal/plan/issues.json') as f:
        issues = json.load(f)

    order = []

    # 1. CRITICAL issues first (security, test failures)
    order.append({
        'phase': 1,
        'name': 'Critical Fixes',
        'issues': issues['critical'],
        'description': 'Fix blocking issues: security vulnerabilities, test failures'
    })

    # 2. MAJOR issues (quality, refactoring)
    order.append({
        'phase': 2,
        'name': 'Quality Fixes',
        'issues': issues['major'],
        'description': 'Fix quality issues: long functions, complexity, duplication'
    })

    # 3. MINOR issues (documentation)
    order.append({
        'phase': 3,
        'name': 'Documentation Fixes',
        'issues': issues['minor'],
        'description': 'Fix documentation: missing docstrings, parameters, returns'
    })

    return order

if __name__ == '__main__':
    order = create_fix_order()

    with open('LLM-CONTEXT/fix-anal/plan/fix_order.json', 'w') as f:
        json.dump(order, f, indent=2)

    print("Fix order created:")
    for phase in order:
        print(f"  Phase {phase['phase']}: {phase['name']} ({len(phase['issues'])} issues)")
EOF

$PYTHON_CMD LLM-CONTEXT/fix-anal/plan/create_order.py
```

### Step 4: Estimate Effort

```bash
cat > LLM-CONTEXT/fix-anal/plan/estimate_effort.py << 'EOF'
import json

def estimate_complexity(issue):
    """Estimate fix complexity based on code analysis and issue type."""
    # Default complexity if not specified
    base_complexity = issue.get('complexity', 'medium')

    # Actually measure complexity if file and line are available
    file_path = issue.get('file')
    line_num = issue.get('line')

    # Enhanced complexity estimation based on actual code metrics
    if file_path and file_path != 'Unknown' and line_num:
        try:
            from pathlib import Path
            import re

            file_obj = Path(file_path)
            if file_obj.exists():
                content = file_obj.read_text()
                lines = content.split('\n')

                # Try to extract function containing this line
                func_start = max(0, int(line_num) - 50)
                func_end = min(len(lines), int(line_num) + 50)
                func_content = '\n'.join(lines[func_start:func_end])

                # Measure function length
                func_length = len([l for l in func_content.split('\n') if l.strip()])

                # Count conditionals (if, elif, for, while, case, switch)
                conditionals = len(re.findall(r'\b(if|elif|else|for|while|switch|case)\b', func_content))

                # Determine complexity based on measurements
                if func_length > 100 or conditionals > 15:
                    return 'high'
                elif func_length > 50 or conditionals > 7:
                    return 'medium'
                else:
                    return 'low'
        except Exception:
            # If analysis fails, fall back to category-based estimation
            pass

    # Category-based complexity estimation (fallback)
    category = issue.get('category', '').lower()
    severity = issue.get('severity', '').upper()

    # Security issues always high complexity due to sensitive nature
    if category == 'security' or severity == 'CRITICAL':
        return 'high'

    # Test failures depend on nature
    if category == 'tests':
        return 'high'

    # Performance issues tend to be medium complexity
    if category == 'performance':
        return 'medium'

    # Quality issues depend on type
    if category == 'quality':
        issue_type = issue.get('type', '')
        if issue_type == 'long_function':
            # Long functions need refactoring - medium to high complexity
            lines = issue.get('lines', 0)
            if lines > 100:
                return 'high'
            else:
                return 'medium'
        elif issue_type == 'high_complexity':
            return 'high'
        elif issue_type == 'duplication':
            return 'low'
        else:
            return 'medium'

    # Documentation is usually low complexity
    if category == 'docs':
        return 'low'

    # Default to base complexity or medium
    complexity_map = {
        'low': 'low',
        'medium': 'medium',
        'high': 'high'
    }
    return complexity_map.get(base_complexity, 'medium')

def estimate_total_effort():
    """Calculate total effort estimate."""
    with open('LLM-CONTEXT/fix-anal/plan/issues.json') as f:
        issues = json.load(f)

    total = 0
    breakdown = {}

    # Complexity to effort points mapping
    complexity_points = {
        'low': 1,
        'medium': 3,
        'high': 5,
        'unknown': 2
    }

    for severity in ['critical', 'major', 'minor']:
        # Calculate effort for each issue based on estimated complexity
        issue_list = issues[severity]
        category_effort = 0

        for issue in issue_list:
            complexity = estimate_complexity(issue)
            points = complexity_points.get(complexity, 3)
            category_effort += points

            # Update issue with calculated complexity if not already set
            if 'complexity' not in issue or issue['complexity'] != complexity:
                issue['calculated_complexity'] = complexity

        breakdown[severity] = {
            'count': len(issue_list),
            'effort_points': category_effort
        }
        total += category_effort

    # Save updated issues with calculated complexity
    with open('LLM-CONTEXT/fix-anal/plan/issues.json', 'w') as f:
        json.dump(issues, f, indent=2)

    return total, breakdown

if __name__ == '__main__':
    total, breakdown = estimate_total_effort()

    print(f"\nEffort estimate:")
    print(f"  CRITICAL: {breakdown['critical']['count']} issues = {breakdown['critical']['effort_points']} points")
    print(f"  MAJOR: {breakdown['major']['count']} issues = {breakdown['major']['effort_points']} points")
    print(f"  MINOR: {breakdown['minor']['count']} issues = {breakdown['minor']['effort_points']} points")
    print(f"  TOTAL: {total} effort points")
    print(f"\nEstimated time: {total * 5} minutes ({total * 5 / 60:.1f} hours)")

    with open('LLM-CONTEXT/fix-anal/plan/effort_estimate.txt', 'w') as f:
        f.write(f"Total effort: {total} points\n")
        f.write(f"Estimated time: {total * 5} minutes\n")
        for severity, data in breakdown.items():
            f.write(f"{severity.upper()}: {data['count']} issues, {data['effort_points']} points\n")
EOF

$PYTHON_CMD LLM-CONTEXT/fix-anal/plan/estimate_effort.py
```

### Step 5: Generate Comprehensive Fix Plan

(Generated after Step 5.5 - see below)

### Step 5.5: Define Fix Strategy & Evidence Requirements

```bash
cat > LLM-CONTEXT/fix-anal/plan/add_fix_strategies.py << 'EOF'
import json
from pathlib import Path

def get_fix_strategy(issue):
    """Define specific fix strategy based on issue type and category."""
    category = issue.get('category', '').lower()
    issue_type = issue.get('type', '')

    strategies = {
        'security': {
            'default': {
                'fix_strategy': 'Replace vulnerable code with secure alternative (parameterized queries, input validation, safe API calls)',
                'evidence_before': ['Run bandit/semgrep on affected file', 'Count vulnerabilities by type', 'Document exact vulnerability location'],
                'evidence_after': ['Re-run bandit/semgrep', 'Verify specific vulnerability eliminated', 'Confirm no new vulnerabilities introduced'],
                'success_criteria': 'Target vulnerability count decreases by >=1 AND no new vulnerabilities introduced',
                'rollback_trigger': 'Tests fail OR new security issues detected OR code coverage decreases'
            },
            'sql_injection': {
                'fix_strategy': 'Replace string concatenation/f-strings with parameterized queries using prepared statements',
                'evidence_before': ['Run bandit -t B608', 'Identify SQL string concatenation locations'],
                'evidence_after': ['Re-run bandit -t B608', 'Verify SQL injection issues = 0'],
                'success_criteria': 'SQL injection count = 0',
                'rollback_trigger': 'Database tests fail OR new SQL errors'
            }
        },
        'quality': {
            'long_function': {
                'fix_strategy': f'Extract lines into helper functions. Target: reduce {issue.get("function", "function")} from {issue.get("lines", "N")} to <50 lines',
                'evidence_before': ['Count lines in function', 'Run full test suite 3x', 'Measure code coverage'],
                'evidence_after': ['Verify function <50 lines', 'Run tests 3x, all pass', 'Verify coverage maintained or improved'],
                'success_criteria': f'Function length <50 lines AND tests pass 3/3 runs AND coverage >= baseline',
                'rollback_trigger': 'Any test run fails OR coverage decreases by >2%'
            },
            'high_complexity': {
                'fix_strategy': f'Reduce complexity from {issue.get("complexity_value", "N")} to <10 via: flatten nesting, extract conditions, use guard clauses, split logic',
                'evidence_before': ['Measure cyclomatic complexity', 'Run tests 3x', 'Note flaky tests'],
                'evidence_after': ['Verify complexity <10', 'Run tests 3x, same reliability', 'No new flaky tests'],
                'success_criteria': 'Complexity <10 AND no new flaky tests AND tests 3/3 pass',
                'rollback_trigger': 'Complexity unchanged OR new test failures OR flaky behavior'
            },
            'duplication': {
                'fix_strategy': f'Extract {issue.get("lines", "N")} duplicated lines to shared utility function',
                'evidence_before': ['Run pylint duplicate-code', 'Count duplication lines', 'Run tests'],
                'evidence_after': ['Re-run pylint duplicate-code', 'Verify duplication reduced', 'Tests pass'],
                'success_criteria': f'Duplication reduced by >={issue.get("lines", 10)} lines AND tests pass',
                'rollback_trigger': 'Tests fail OR new duplication introduced'
            }
        },
        'docs': {
            'missing_docstring': {
                'fix_strategy': f'Add comprehensive docstring to {issue.get("file", "file")}:{issue.get("line", "N")} following language conventions (Google/NumPy/Sphinx style)',
                'evidence_before': ['Count functions without docstrings', 'Check doc coverage %'],
                'evidence_after': ['Verify docstring added', 'Check doc coverage increased'],
                'success_criteria': 'Function has valid docstring AND doc coverage increases',
                'rollback_trigger': 'Docstring syntax invalid OR breaks doc generation'
            }
        },
        'tests': {
            'test_failure': {
                'fix_strategy': 'Identify root cause: fix code bug OR update test expectations OR fix test environment',
                'evidence_before': ['Run test suite', 'Capture failure output', 'Identify failure pattern'],
                'evidence_after': ['Run tests 5x', 'All runs pass', 'No flaky behavior'],
                'success_criteria': 'Tests pass 5/5 runs with no stderr warnings',
                'rollback_trigger': 'Any test run fails OR other tests break'
            }
        },
        'performance': {
            'default': {
                'fix_strategy': 'Replace inefficient algorithm/operation with optimized version (e.g., O(n²)→O(n log n), list→set lookup)',
                'evidence_before': ['Profile code with cProfile/timeit', 'Measure baseline execution time', 'Run tests'],
                'evidence_after': ['Re-profile optimized code', 'Measure new execution time', 'Verify behavior unchanged'],
                'success_criteria': 'Execution time improves by >=20% AND tests pass AND behavior identical',
                'rollback_trigger': 'Performance degrades OR tests fail OR behavior changes'
            }
        }
    }

    # Get category-specific strategy
    category_strats = strategies.get(category, {})
    strategy = category_strats.get(issue_type) or category_strats.get('default')

    if not strategy:
        # Generic fallback
        strategy = {
            'fix_strategy': f'Address {category} issue: {issue.get("description", "unknown issue")[:100]}',
            'evidence_before': ['Document current state', 'Run relevant tests', 'Capture metrics'],
            'evidence_after': ['Verify issue resolved', 'Re-run tests', 'Confirm metrics improved'],
            'success_criteria': 'Issue resolved AND tests pass AND no regressions',
            'rollback_trigger': 'Tests fail OR new issues introduced'
        }

    return strategy

def add_strategies_to_issues():
    """Add fix strategies and evidence requirements to all issues."""
    issues_file = Path('LLM-CONTEXT/fix-anal/plan/issues.json')

    if not issues_file.exists():
        print("ERROR: issues.json not found")
        return

    with open(issues_file) as f:
        issues = json.load(f)

    # Process each severity level
    for severity in ['critical', 'major', 'minor']:
        issue_list = issues[severity]

        for idx, issue in enumerate(issue_list):
            # Generate unique issue ID
            issue_id = f"{issue.get('category', 'UNK').upper()}_{severity[:3].upper()}_{idx+1:03d}"
            issue['issue_id'] = issue_id

            # Get fix strategy
            strategy = get_fix_strategy(issue)

            # Add strategy fields
            issue['fix_strategy'] = strategy['fix_strategy']
            issue['evidence_before'] = strategy['evidence_before']
            issue['evidence_after'] = strategy['evidence_after']
            issue['success_criteria'] = strategy['success_criteria']
            issue['rollback_trigger'] = strategy['rollback_trigger']

    # Save enhanced issues
    with open(issues_file, 'w') as f:
        json.dump(issues, f, indent=2)

    print("✓ Added fix strategies and evidence requirements to all issues")

    # Create summary report
    summary_lines = []
    summary_lines.append("# Fix Strategies Summary\n")
    summary_lines.append(f"Generated: {Path('LLM-CONTEXT/fix-anal/plan/issues.json').stat().st_mtime}\n\n")

    for severity in ['critical', 'major', 'minor']:
        issue_list = issues[severity]
        if issue_list:
            summary_lines.append(f"## {severity.upper()} Issues ({len(issue_list)})\n\n")

            for issue in issue_list:
                summary_lines.append(f"### {issue['issue_id']}: {issue.get('description', 'Unknown')[:80]}\n")
                summary_lines.append(f"**Fix Strategy:** {issue['fix_strategy']}\n\n")
                summary_lines.append(f"**Success Criteria:** {issue['success_criteria']}\n\n")
                summary_lines.append("**Evidence Before:**\n")
                for ev in issue['evidence_before']:
                    summary_lines.append(f"- {ev}\n")
                summary_lines.append("\n**Evidence After:**\n")
                for ev in issue['evidence_after']:
                    summary_lines.append(f"- {ev}\n")
                summary_lines.append(f"\n**Rollback If:** {issue['rollback_trigger']}\n\n")
                summary_lines.append("---\n\n")

    # Save summary
    with open('LLM-CONTEXT/fix-anal/plan/fix_strategies.md', 'w') as f:
        f.writelines(summary_lines)

    print("✓ Generated fix_strategies.md summary")

if __name__ == '__main__':
    add_strategies_to_issues()
EOF

$PYTHON_CMD LLM-CONTEXT/fix-anal/plan/add_fix_strategies.py
```

**NOTE:** This step adds actionable fix strategies to each issue:
- **Fix Strategy:** Specific actions to resolve the issue
- **Evidence Before:** What to measure/capture before fixing
- **Evidence After:** What to measure/verify after fixing
- **Success Criteria:** Quantifiable metrics for success
- **Rollback Trigger:** Conditions that require reverting the fix

This makes the plan fully actionable - other subagents know exactly what to do, how to verify it worked, and when to keep or revert changes.

### Step 5.6: Generate Comprehensive Fix Plan

```bash
echo "Generating comprehensive fix plan..."

cat > LLM-CONTEXT/fix-anal/plan/fix_plan.md << EOF
# Comprehensive Fix Plan

Generated: $(date -Iseconds)

## Executive Summary

This plan addresses all issues identified by the code review system.

$(cat LLM-CONTEXT/fix-anal/plan/effort_estimate.txt)

## Fixing Strategy

Fixes will be applied in priority order:
1. **CRITICAL** - Security vulnerabilities, test failures (MUST fix)
2. **MAJOR** - Quality issues, refactoring needs (SHOULD fix)
3. **MINOR** - Documentation gaps (NICE to fix)

## Phase 1: Critical Fixes (BLOCKING)

**Goal:** Fix all blocking issues that prevent code from being production-ready.

### Security Vulnerabilities

$($PYTHON_CMD -c "
import json
with open('LLM-CONTEXT/fix-anal/plan/issues.json') as f:
    issues = json.load(f)
security = [i for i in issues['critical'] if i.get('category') == 'security']
if security:
    for i, issue in enumerate(security, 1):
        print(f'{i}. {issue.get(\"description\", \"Security issue\")}')
        print(f'   File: {issue.get(\"file\", \"Unknown\")}')
        print(f'   Severity: CRITICAL')
        print()
else:
    print('None found ✓')
" 2>/dev/null || echo "No security issues found ✓")

### Test Failures

$($PYTHON_CMD -c "
import json
with open('LLM-CONTEXT/fix-anal/plan/issues.json') as f:
    issues = json.load(f)
tests = [i for i in issues['critical'] if i.get('category') == 'tests']
if tests:
    for i, issue in enumerate(tests, 1):
        print(f'{i}. {issue.get(\"description\", \"Test failure\")}')
        print(f'   Type: {issue.get(\"type\", \"Unknown\")}')
        print()
else:
    print('None found ✓')
" 2>/dev/null || echo "All tests passing ✓")

**Verification Required:**
- All security vulnerabilities must be fixed
- All tests must pass before proceeding to Phase 2

**Fix Strategies & Evidence:**
See LLM-CONTEXT/fix-anal/plan/fix_strategies.md for detailed fix strategies, evidence requirements, success criteria, and rollback triggers for each issue

---

## Phase 2: Quality Fixes (IMPORTANT)

**Goal:** Improve code quality to meet standards (no functions >50 lines, no complexity >10).

### Long Functions (>50 lines)

$($PYTHON_CMD -c "
import json
with open('LLM-CONTEXT/fix-anal/plan/issues.json') as f:
    issues = json.load(f)
long_funcs = [i for i in issues['major'] if i.get('type') == 'long_function']
if long_funcs:
    for i, issue in enumerate(long_funcs, 1):
        print(f'{i}. {issue.get(\"function\", \"Unknown function\")}')
        print(f'   Current: {issue.get(\"lines\")} lines, Target: 50 lines')
        print(f'   Action: Refactor into smaller, focused functions')
        print()
else:
    print('None found ✓')
" 2>/dev/null || echo "No long functions ✓")

### High Complexity Functions

$($PYTHON_CMD -c "
import json
with open('LLM-CONTEXT/fix-anal/plan/issues.json') as f:
    issues = json.load(f)
complex = [i for i in issues['major'] if i.get('type') == 'high_complexity']
if complex:
    for i, issue in enumerate(complex, 1):
        print(f'{i}. Complexity: {issue.get(\"complexity_value\")}')
        print(f'   Target: <10')
        print(f'   Action: Flatten nesting, extract functions, use guard clauses')
        print()
else:
    print('None found ✓')
" 2>/dev/null || echo "No complex functions ✓")

### Code Duplication

$($PYTHON_CMD -c "
import json
with open('LLM-CONTEXT/fix-anal/plan/issues.json') as f:
    issues = json.load(f)
dup = [i for i in issues['major'] if i.get('type') == 'duplication']
if dup:
    for i, issue in enumerate(dup, 1):
        print(f'{i}. {issue.get(\"description\", \"Duplicated code\")}')
        print(f'   Action: Extract to shared function')
        print()
else:
    print('None found ✓')
" 2>/dev/null || echo "No duplication ✓")

**Verification Required:**
- Run tests after each refactoring
- Verify complexity metrics improved
- No new duplication introduced

**Fix Strategies & Evidence:**
See LLM-CONTEXT/fix-anal/plan/fix_strategies.md for detailed fix strategies, evidence requirements, success criteria, and rollback triggers for each issue

---

## Phase 3: Documentation Fixes (NICE TO HAVE)

**Goal:** Complete all missing documentation.

### Missing Docstrings

$($PYTHON_CMD -c "
import json
with open('LLM-CONTEXT/fix-anal/plan/issues.json') as f:
    issues = json.load(f)
docs = [i for i in issues['minor'] if i.get('type') == 'missing_docstring']
count = len(docs)
if count > 0:
    print(f'{count} functions/classes missing docstrings')
    print()
    print('Action: Add comprehensive docstrings documenting:')
    print('- Purpose and behavior')
    print('- Parameters and their types')
    print('- Return values')
    print('- Examples for complex APIs')
else:
    print('None found ✓')
" 2>/dev/null || echo "All APIs documented ✓")

**Verification Required:**
- All public APIs have docstrings
- Documentation follows language conventions
- Examples provided for complex functions

**Fix Strategies & Evidence:**
See LLM-CONTEXT/fix-anal/plan/fix_strategies.md for detailed fix strategies, evidence requirements, success criteria, and rollback triggers for each issue

---

## Risk Assessment

### High Risk Fixes
- Security vulnerability patches (may change behavior)
- Test failure fixes (may require API changes)

### Medium Risk Fixes
- Refactoring long functions (behavior must remain identical)
- Complexity reduction (logic must be preserved)

### Low Risk Fixes
- Documentation additions (no code behavior change)

## Success Criteria

Phase 1 (Critical):
- [ ] All security vulnerabilities fixed
- [ ] All tests passing
- [ ] No CRITICAL issues remaining

Phase 2 (Quality):
- [ ] All functions <50 lines
- [ ] All complexity scores <10
- [ ] No code duplication
- [ ] All tests still passing

Phase 3 (Documentation):
- [ ] All public APIs documented
- [ ] All parameters documented
- [ ] All return values documented

## Rollback Plan

If any fix causes test failures:
1. Revert the specific change
2. Document why it failed
3. Investigate root cause more deeply
4. Try alternative approach

## Next Steps

1. Review this plan with user
2. Get approval to proceed
3. Execute Phase 1 (critical fixes)
4. Verify Phase 1 before Phase 2
5. Execute Phase 2 (quality fixes)
6. Verify Phase 2 before Phase 3
7. Execute Phase 3 (documentation)
8. Final comprehensive verification
9. Generate fix report

---

**Detailed Issues:** See LLM-CONTEXT/fix-anal/plan/issues.json
**Fix Strategies:** See LLM-CONTEXT/fix-anal/plan/fix_strategies.md
**Fix Order:** See LLM-CONTEXT/fix-anal/plan/fix_order.json
**Effort Estimate:** See LLM-CONTEXT/fix-anal/plan/effort_estimate.txt

## Actionable Fix Strategies

Each issue now includes:
- **Issue ID:** Unique identifier (e.g., SEC_CRI_001)
- **Fix Strategy:** Specific actions to resolve the issue
- **Evidence Before:** Measurements to capture before fixing
- **Evidence After:** Verification steps after fixing
- **Success Criteria:** Quantifiable metrics for success
- **Rollback Trigger:** Conditions that require reverting

This ensures every fix is:
1. **Actionable** - Clear steps to implement
2. **Verifiable** - Evidence-based validation
3. **Safe** - Clear rollback criteria
EOF

echo "✓ Comprehensive fix plan generated"

# CRITICAL: Update status to SUCCESS immediately after plan generation
echo "SUCCESS" > LLM-CONTEXT/fix-anal/plan/status.txt
echo "✓ Status updated to SUCCESS"
```

## Output Format

Return to orchestrator:

```
## Fix Planning Complete

**Total Issues Found:** [count]
- CRITICAL: [count] (security, test failures)
- MAJOR: [count] (quality, refactoring)
- MINOR: [count] (documentation)

**Estimated Effort:** [X] points ([Y] minutes)

**Fixing Order:**
1. Phase 1: Critical fixes (security, tests) - BLOCKING
2. Phase 2: Quality fixes (refactoring, complexity) - IMPORTANT
3. Phase 3: Documentation fixes (docstrings) - NICE TO HAVE

**Generated Files:**
- LLM-CONTEXT/fix-anal/plan/fix_plan.md - Comprehensive fix plan
- LLM-CONTEXT/fix-anal/plan/issues.json - Categorized issues with fix strategies
- LLM-CONTEXT/fix-anal/plan/fix_strategies.md - Actionable fix strategies and evidence requirements
- LLM-CONTEXT/fix-anal/plan/fix_order.json - Fixing order
- LLM-CONTEXT/fix-anal/plan/effort_estimate.txt - Effort estimate

**Key Enhancement:**
Each issue now includes actionable fix strategies with:
- Specific implementation steps
- Evidence requirements (before/after)
- Quantifiable success criteria
- Clear rollback triggers

**Ready for next step:** Yes - Issues are now fully actionable
```

### Final Step: Verify Status File

```bash
# Integration Protocol: Verify status.txt exists and is SUCCESS
if [ -f "LLM-CONTEXT/fix-anal/plan/status.txt" ]; then
    STATUS=$(cat LLM-CONTEXT/fix-anal/plan/status.txt)
    echo "✓ Planning complete - status: $STATUS"
else
    echo "WARNING: status.txt missing - creating it now"
    echo "SUCCESS" > LLM-CONTEXT/fix-anal/plan/status.txt
    echo "✓ Status file created"
fi

echo ""
echo "Integration Protocol Verification:"
echo "  - status.txt: $(cat LLM-CONTEXT/fix-anal/plan/status.txt)"
echo "  - Summary: fix_plan.md"
echo "  - Data: issues.json, fix_strategies.md"
echo "  - Logs: $LOG_FILE"
echo ""
echo "Planning subagent complete!"
```

## Key Behaviors

- **ALWAYS extract from all review sources** - Quality, security, docs, tests, performance
- **ALWAYS categorize by severity** - CRITICAL, MAJOR, MINOR
- **ALWAYS create fixing order** - Respect dependencies
- **ALWAYS estimate effort** - Help user understand scope
- **ALWAYS define fix strategies** - Specific, actionable steps for each issue
- **ALWAYS specify evidence requirements** - Before/after measurements for verification
- **ALWAYS set success criteria** - Quantifiable metrics (e.g., "reduce to <50 lines", "tests pass 3/3 runs")
- **ALWAYS define rollback triggers** - Clear conditions for reverting changes
- **ALWAYS save all data** - JSON for machine, Markdown for humans
- **NEVER skip issues** - Every finding gets a complete fix strategy
- **NEVER use vague strategies** - "Fix it" is not actionable; "Extract lines 45-67 to helper function" is actionable

## Example Workflow

When this subagent processes findings:

**Input:** Review report identifies "Function `process_data` is 85 lines (max: 50)"

**Output:** Enhanced issue with actionable strategy
```json
{
  "issue_id": "QUALITY_MAJ_003",
  "category": "quality",
  "severity": "MAJOR",
  "type": "long_function",
  "function": "process_data",
  "lines": 85,
  "description": "Function process_data is 85 lines (max: 50)",
  "fix_strategy": "Extract lines into helper functions. Target: reduce process_data from 85 to <50 lines",
  "evidence_before": [
    "Count lines in process_data function",
    "Run full test suite 3x",
    "Measure code coverage with pytest-cov"
  ],
  "evidence_after": [
    "Verify process_data function <50 lines",
    "Run tests 3x, all pass",
    "Verify coverage maintained or improved"
  ],
  "success_criteria": "Function length <50 lines AND tests pass 3/3 runs AND coverage >= baseline",
  "rollback_trigger": "Any test run fails OR coverage decreases by >2%"
}
# Mark as complete
echo "SUCCESS" > LLM-CONTEXT/fix-anal/plan/status.txt
echo "✓ Plan analysis complete"
echo "✓ Status: SUCCESS"
```

**Next Subagent Usage:** A fix execution subagent can now:
1. Read the fix_strategy to know exactly what to do
2. Capture evidence_before measurements
3. Implement the fix
4. Verify using evidence_after steps
5. Compare results against success_criteria
6. Decide to commit or rollback based on rollback_trigger
