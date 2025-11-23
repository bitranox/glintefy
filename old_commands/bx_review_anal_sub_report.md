# Code Review - Report Compilation Sub-Agent

## Purpose

Compile all findings from other sub-agents into a comprehensive final report.

## Responsibilities

1. Gather results from all analysis sub-agents
2. Synthesize findings into coherent report
3. Categorize issues by severity (Critical, Major, Minor)
4. Generate actionable recommendations
5. Provide clear approval status

## Execution Steps

```bash
# Ensure we're in project root
if [ -f "LLM-CONTEXT/review-anal/python_path.txt" ]; then
    PROJECT_ROOT=$(pwd)
elif git rev-parse --show-toplevel &>/dev/null; then
    PROJECT_ROOT=$(git rev-parse --show-toplevel)
    cd "$PROJECT_ROOT" || exit 1
else
    PROJECT_ROOT=$(pwd)
fi
echo "✓ Working directory: $PROJECT_ROOT"

mkdir -p LLM-CONTEXT/review-anal/report
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


# Initialize status tracking
echo "IN_PROGRESS" > LLM-CONTEXT/review-anal/report/status.txt
```

### Step 1: Gather All Analysis Results

```bash
echo "Gathering analysis results from LLM-CONTEXT/..."

# Check which analyses were performed
analyses_done=""

[ -f "LLM-CONTEXT/review-anal/scope/scope_summary.txt" ] && analyses_done="$analyses_done scope"
[ -f "LLM-CONTEXT/review-anal/deps/dependency_update_summary.md" ] && analyses_done="$analyses_done deps"
[ -f "LLM-CONTEXT/review-anal/quality/complexity_analysis.txt" ] && analyses_done="$analyses_done quality"
[ -f "LLM-CONTEXT/review-anal/security/security_analysis_report.md" ] && analyses_done="$analyses_done security"
[ -f "LLM-CONTEXT/review-anal/perf/performance_analysis_report.md" ] && analyses_done="$analyses_done perf"
[ -f "LLM-CONTEXT/review-anal/cache/cache_analysis_report.md" ] && analyses_done="$analyses_done cache"

echo "Analyses performed:$analyses_done"
```

### Step 2: Extract Key Findings

```bash
echo "Extracting key findings..."

cat > LLM-CONTEXT/review-anal/report/extract_findings.py << 'EOF'
import os
import json
import re

def extract_scope_info():
    """Extract scope information from scope analysis results."""
    if not os.path.exists('LLM-CONTEXT/review-anal/scope/scope_summary.txt'):
        return {}

    with open('LLM-CONTEXT/review-anal/scope/scope_summary.txt') as f:
        content = f.read()

    info = {
        'files_reviewed': re.search(r'files:\s*(\d+)', content, re.I),
        'scope_type': re.search(r'SCOPE:\s*(.+?)===', content, re.S),
    }

    return {k: v.group(1).strip() if v else 'N/A' for k, v in info.items()}

def extract_dependency_info():
    """Extract dependency update information and test status."""
    if not os.path.exists('LLM-CONTEXT/review-anal/deps/dependency_update_summary.md'):
        return {}

    with open('LLM-CONTEXT/review-anal/deps/dependency_update_summary.md') as f:
        content = f.read()

    # Count packages updated
    npm_updates = len(re.findall(r'npm.*updated', content, re.I))
    pip_updates = len(re.findall(r'pip.*updated', content, re.I))

    return {
        'npm_updates': npm_updates,
        'pip_updates': pip_updates,
        'test_status': '✓ Passing' if 'passed' in content.lower() else '⚠ Issues'
    }

def extract_quality_issues():
    """Extract code quality issues from analysis files."""
    issues = {
        'long_functions': 0,
        'complex_functions': 0,
        'duplications': 0
    }

    if os.path.exists('LLM-CONTEXT/review-anal/quality/complexity_analysis.txt'):
        with open('LLM-CONTEXT/review-anal/quality/complexity_analysis.txt') as f:
            content = f.read()
            issues['long_functions'] = len(re.findall(r'TOO_LONG', content))
            issues['complex_functions'] = len(re.findall(r'TOO_NESTED', content))

    if os.path.exists('LLM-CONTEXT/review-anal/quality/duplication_analysis.txt'):
        with open('LLM-CONTEXT/review-anal/quality/duplication_analysis.txt') as f:
            content = f.read()
            issues['duplications'] = len(re.findall(r'Similar lines', content))

    return issues

def extract_security_issues():
    """Extract security vulnerabilities by severity level."""
    issues = {
        'high': 0,
        'medium': 0,
        'low': 0
    }

    if os.path.exists('LLM-CONTEXT/review-anal/security/security_analysis_report.md'):
        with open('LLM-CONTEXT/review-anal/security/security_analysis_report.md') as f:
            content = f.read()
            issues['high'] = len(re.findall(r'Severity:\s*High', content, re.I))
            issues['medium'] = len(re.findall(r'Severity:\s*Medium', content, re.I))
            issues['low'] = len(re.findall(r'Severity:\s*Low', content, re.I))

    return issues

if __name__ == '__main__':
    findings = {
        'scope': extract_scope_info(),
        'dependencies': extract_dependency_info(),
        'quality': extract_quality_issues(),
        'security': extract_security_issues()
    }

    print(json.dumps(findings, indent=2))
EOF

$PYTHON_CMD LLM-CONTEXT/review-anal/report/extract_findings.py > LLM-CONTEXT/review-anal/report/extracted_findings.json 2>&1 || true
```

### Step 3: Determine Approval Status

```bash
echo "Determining approval status..."

cat > LLM-CONTEXT/review-anal/report/determine_approval.py << 'EOF'
import json
import os

def determine_approval():
    """Determine review approval status based on findings.

    Returns:
        tuple: (status_string, list_of_issues)
    """
    if not os.path.exists('LLM-CONTEXT/review-anal/report/extracted_findings.json'):
        return 'UNKNOWN', 'No findings available'

    with open('LLM-CONTEXT/review-anal/report/extracted_findings.json') as f:
        findings = json.load(f)

    blockers = []
    warnings = []

    # Check security
    security = findings.get('security', {})
    if security.get('high', 0) > 0:
        blockers.append(f"HIGH severity security issues: {security['high']}")

    # Check quality
    quality = findings.get('quality', {})
    if quality.get('long_functions', 0) > 5:
        warnings.append(f"Functions >50 lines: {quality['long_functions']}")
    if quality.get('complex_functions', 0) > 5:
        warnings.append(f"Over-complicated functions: {quality['complex_functions']}")

    # Check dependencies
    deps = findings.get('dependencies', {})
    if deps.get('test_status') != '✓ Passing':
        blockers.append("Tests not passing after dependency updates")

    # Determine status
    if blockers:
        return '✗ CHANGES REQUIRED', blockers
    elif warnings:
        return '⚠ APPROVED WITH COMMENTS', warnings
    else:
        return '✓ APPROVED', []

if __name__ == '__main__':
    status, issues = determine_approval()
    print(f"Status: {status}")
    if issues:
        print("\nIssues:")
        for issue in issues:
            print(f"  - {issue}")
EOF

approval_info=$($PYTHON_CMD LLM-CONTEXT/review-anal/report/determine_approval.py)
echo "$approval_info"
```

### Step 4: Generate Final Report

```bash
echo "Generating executive summary report..."

cat > LLM-CONTEXT/review-anal/report/generate_summary.py << 'PYEOF'
"""Generate executive summary report with links to detailed reports.

Executed with: $PYTHON_CMD generate_summary.py
Requires: Python 3.13+
"""

import json
import os
import re
from pathlib import Path
from datetime import datetime

def count_lines(file_path):
    """Count non-empty lines in a file."""
    try:
        with open(file_path) as f:
            return sum(1 for line in f if line.strip())
    except:
        return 0

def count_pattern(file_path, pattern):
    """Count occurrences of pattern in file."""
    try:
        with open(file_path) as f:
            content = f.read()
            return len(re.findall(pattern, content, re.IGNORECASE))
    except:
        return 0

def read_first_n_lines(file_path, n=10):
    """Read first N non-empty lines."""
    try:
        with open(file_path) as f:
            lines = [line.strip() for line in f if line.strip()]
            return '\n'.join(lines[:n])
    except:
        return "No data available"

def extract_section(file_path, section_marker, max_lines=5):
    """Extract a specific section from a file."""
    try:
        with open(file_path) as f:
            lines = f.readlines()
            in_section = False
            section_lines = []

            for line in lines:
                if section_marker in line:
                    in_section = True
                    continue
                if in_section:
                    if line.startswith('#') or line.startswith('---'):
                        break
                    if line.strip():
                        section_lines.append(line.rstrip())
                        if len(section_lines) >= max_lines:
                            break

            return '\n'.join(section_lines)
    except:
        return ""

def load_json(file_path):
    """Load JSON file with proper error handling."""
    try:
        with open(file_path) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: {file_path} not found, using empty dict")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error: {file_path} contains invalid JSON: {e}")
        return {}
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return {}

def generate_summary():
    """Generate executive summary."""

    report = []
    report.append("# Code Review - Executive Summary\n\n")
    report.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    report.append("---\n\n")

    # Load extracted findings
    findings = load_json('LLM-CONTEXT/review-anal/report/extracted_findings.json')

    # === SCOPE SECTION ===
    scope_file = "LLM-CONTEXT/review-anal/scope/scope_summary.txt"
    if os.path.exists(scope_file):
        try:
            with open(scope_file) as f:
                scope_content = f.read()
                files_match = re.search(r'(\d+)\s+files', scope_content, re.I)
                files_count = files_match.group(1) if files_match else "N/A"
        except:
            files_count = "N/A"

        report.append("## 📋 Scope\n\n")
        report.append(f"**Files Reviewed**: {files_count}\n\n")
        report.append("→ **Full details**: `LLM-CONTEXT/review-anal/scope/scope_summary.txt`\n\n")
        report.append("---\n\n")

    # === CRITICAL ISSUES ===
    report.append("## 🔴 Critical Issues\n\n")

    has_critical = False

    # Security
    security_file = "LLM-CONTEXT/review-anal/security/security_analysis_report.md"
    if os.path.exists(security_file):
        security = findings.get('security', {})
        high_count = security.get('high', 0)
        critical_count = count_pattern(security_file, r'\bCRITICAL\b')

        total_critical = high_count + critical_count

        if total_critical > 0:
            has_critical = True
            report.append(f"### 🔒 Security ({total_critical} issues)\n\n")

            # Show top 5 critical/high severity only
            top_issues = extract_section(security_file, "HIGH", max_lines=5)
            if not top_issues:
                top_issues = extract_section(security_file, "CRITICAL", max_lines=5)

            if top_issues:
                report.append("**Top Issues**:\n\n")
                report.append(f"```\n{top_issues}\n```\n\n")

            report.append("→ **Full security analysis**: `LLM-CONTEXT/review-anal/security/security_analysis_report.md`\n\n")

    # Test Failures
    deps_file = "LLM-CONTEXT/review-anal/deps/test_results.txt"
    if os.path.exists(deps_file):
        failed_tests = count_pattern(deps_file, r'\bFAILED\b|\bERROR\b')

        if failed_tests > 0:
            has_critical = True
            report.append(f"### ❌ Test Failures ({failed_tests} tests)\n\n")

            # Show first 5 failures
            failures = extract_section(deps_file, "FAILED", max_lines=5)
            if failures:
                report.append(f"```\n{failures}\n```\n\n")

            report.append("→ **Full test results**: `LLM-CONTEXT/review-anal/deps/test_results.txt`\n\n")

    if not has_critical:
        report.append("✅ **No critical issues found**\n\n")

    report.append("---\n\n")

    # === MAJOR ISSUES ===
    report.append("## ⚠️ Major Issues\n\n")

    has_major = False

    # Quality
    quality_file = "LLM-CONTEXT/review-anal/quality/refactoring_recommendations.md"
    if os.path.exists(quality_file):
        quality = findings.get('quality', {})
        complex_funcs = quality.get('complex_functions', 0)
        long_funcs = quality.get('long_functions', 0)
        duplications = quality.get('duplications', 0)

        total_quality = complex_funcs + long_funcs + duplications

        if total_quality > 0:
            has_major = True
            report.append(f"### 📊 Code Quality ({total_quality} recommendations)\n\n")

            # Show summary stats only
            if complex_funcs > 0:
                report.append(f"- **{complex_funcs}** complex functions (complexity >10)\n")
            if long_funcs > 0:
                report.append(f"- **{long_funcs}** long functions (>50 lines)\n")
            if duplications > 0:
                report.append(f"- **{duplications}** code duplications\n")

            report.append("\n→ **Full quality analysis**: `LLM-CONTEXT/review-anal/quality/refactoring_recommendations.md`\n\n")

    # Performance
    perf_file = "LLM-CONTEXT/review-anal/perf/performance_analysis_report.md"
    if os.path.exists(perf_file):
        hotspots = count_pattern(perf_file, r'\bHOTSPOT\b|\bSLOW\b')

        if hotspots > 0:
            has_major = True
            report.append(f"### ⚡ Performance ({hotspots} opportunities)\n\n")
            report.append(f"{hotspots} performance optimization opportunities identified through profiling\n\n")
            report.append("→ **Full performance analysis**: `LLM-CONTEXT/review-anal/perf/performance_analysis_report.md`\n\n")

    # Cache
    cache_file = "LLM-CONTEXT/review-anal/cache/priority_cache_candidates.txt"
    if os.path.exists(cache_file):
        candidates = count_lines(cache_file)

        if candidates > 0:
            has_major = True
            report.append(f"### 💾 Caching ({candidates} candidates)\n\n")

            # Show top 3 candidates
            top_candidates = read_first_n_lines(cache_file, 3)
            if top_candidates and top_candidates != "No data available":
                report.append(f"**Top candidates**:\n```\n{top_candidates}\n```\n\n")

            report.append("→ **Full cache analysis**: `LLM-CONTEXT/review-anal/cache/cache_analysis_report.md`\n\n")

    # Security - Medium severity
    if os.path.exists(security_file):
        security = findings.get('security', {})
        medium_count = security.get('medium', 0)

        if medium_count > 0:
            has_major = True
            report.append(f"### 🔐 Security - Medium Severity ({medium_count} issues)\n\n")
            report.append("→ **Full security analysis**: `LLM-CONTEXT/review-anal/security/security_analysis_report.md`\n\n")

    if not has_major:
        report.append("✅ **No major issues found**\n\n")

    report.append("---\n\n")

    # === MINOR ISSUES ===
    report.append("## 📝 Minor Issues\n\n")

    has_minor = False

    # Documentation
    docs_file = "LLM-CONTEXT/review-anal/docs/documentation_analysis.txt"
    if os.path.exists(docs_file):
        missing_docs = count_pattern(docs_file, r'\bmissing\b|\bundocumented\b')

        if missing_docs > 0:
            has_minor = True
            report.append(f"### 📚 Documentation ({missing_docs} items)\n\n")
            report.append(f"{missing_docs} functions/modules missing or incomplete documentation\n\n")
            report.append("→ **Full documentation analysis**: `LLM-CONTEXT/review-anal/docs/documentation_analysis.txt`\n\n")

    # Dependencies
    deps_summary = "LLM-CONTEXT/review-anal/deps/dependency_update_summary.md"
    if os.path.exists(deps_summary):
        outdated = count_pattern(deps_summary, r'\boutdated\b|\bupdate\b')

        if outdated > 0:
            has_minor = True
            report.append(f"### 📦 Dependencies ({outdated} updates available)\n\n")
            report.append("→ **Full dependency analysis**: `LLM-CONTEXT/review-anal/deps/dependency_update_summary.md`\n\n")

    if not has_minor:
        report.append("✅ **No minor issues found**\n\n")

    report.append("---\n\n")

    # === NEXT STEPS ===
    report.append("## 🎯 Next Steps\n\n")

    step_num = 1

    # Priority 1: Critical security
    if os.path.exists(security_file):
        security = findings.get('security', {})
        if security.get('high', 0) + count_pattern(security_file, r'\bCRITICAL\b') > 0:
            report.append(f"{step_num}. **CRITICAL**: Fix security vulnerabilities (see security report)\n")
            step_num += 1

    # Priority 2: Test failures
    if os.path.exists(deps_file) and count_pattern(deps_file, r'\bFAILED\b') > 0:
        report.append(f"{step_num}. **CRITICAL**: Fix failing tests (see deps report)\n")
        step_num += 1

    # Priority 3: Quality issues
    if os.path.exists(quality_file):
        quality = findings.get('quality', {})
        if quality.get('complex_functions', 0) + quality.get('long_functions', 0) > 0:
            report.append(f"{step_num}. **HIGH**: Refactor complex/long functions (see quality report)\n")
            step_num += 1

    # Priority 4: Performance
    if os.path.exists(perf_file) and count_pattern(perf_file, r'\bHOTSPOT\b') > 0:
        report.append(f"{step_num}. **MEDIUM**: Address performance bottlenecks (see perf report)\n")
        step_num += 1

    # Always suggest fix command
    report.append(f"\n{step_num}. Run `/bx_fix_anal` to automatically apply fixes\n\n")

    report.append("---\n\n")

    # === DETAILED REPORTS ===
    report.append("## 📂 Detailed Reports\n\n")
    report.append("All complete analysis data available in:\n\n")
    report.append("```\n")
    report.append("LLM-CONTEXT/review-anal/\n")
    report.append("├── security/\n")
    report.append("│   └── security_analysis_report.md\n")
    report.append("├── quality/\n")
    report.append("│   ├── refactoring_recommendations.md\n")
    report.append("│   ├── complexity_analysis.txt\n")
    report.append("│   └── duplication_analysis.txt\n")
    report.append("├── perf/\n")
    report.append("│   └── performance_analysis_report.md\n")
    report.append("├── cache/\n")
    report.append("│   ├── cache_analysis_report.md\n")
    report.append("│   └── priority_cache_candidates.txt\n")
    report.append("├── docs/\n")
    report.append("│   └── documentation_analysis.txt\n")
    report.append("├── deps/\n")
    report.append("│   ├── dependency_update_summary.md\n")
    report.append("│   └── test_results.txt\n")
    report.append("└── scope/\n")
    report.append("    └── scope_summary.txt\n")
    report.append("```\n\n")

    report.append("---\n\n")

    # === APPROVAL STATUS ===
    report.append("## ✅ Approval Status\n\n")

    # Determine approval
    has_critical_security = os.path.exists(security_file) and (findings.get('security', {}).get('high', 0) > 0)
    has_test_failures = os.path.exists(deps_file) and count_pattern(deps_file, r'\bFAILED\b') > 0

    if has_critical_security or has_test_failures:
        report.append("**Status**: ❌ **CHANGES REQUIRED**\n\n")
        report.append("Critical issues must be fixed before approval.\n\n")
    elif has_major:
        report.append("**Status**: ⚠️ **APPROVED WITH COMMENTS**\n\n")
        report.append("Major issues should be addressed but do not block approval.\n\n")
    else:
        report.append("**Status**: ✅ **APPROVED**\n\n")
        report.append("No critical or major issues found.\n\n")

    report.append("---\n\n")
    report.append("**End of Executive Summary**\n\n")
    report.append("*For complete details, see the full reports linked above.*\n")

    return ''.join(report)

# Generate and save report
try:
    summary = generate_summary()
    with open('LLM-CONTEXT/review-anal/report/review_report.md', 'w') as f:
        f.write(summary)

    word_count = len(summary.split())
    token_estimate = int(word_count * 1.3)

    print("✓ Executive summary generated")
    print(f"  Word count: {word_count}")
    print(f"  Token estimate: ~{token_estimate} tokens")

    if token_estimate > 10000:
        print(f"  ⚠️ Warning: Summary is larger than expected ({token_estimate} tokens)")
    else:
        print(f"  ✓ Summary within token budget (<10k tokens)")

except Exception as e:
    print(f"❌ Error generating summary: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
PYEOF

$PYTHON_CMD LLM-CONTEXT/review-anal/report/generate_summary.py

if [ $? -eq 0 ]; then
    echo "✓ Final report generated: LLM-CONTEXT/review-anal/report/review_report.md"
else
    echo "❌ Failed to generate summary report"
    exit 1
fi
```
```

## Output Format

Return to orchestrator:

```
## Review Report Compilation Complete

**Approval Status:** [✓ APPROVED | ⚠ APPROVED WITH COMMENTS | ✗ CHANGES REQUIRED]

**Summary:**
- Files Reviewed: [count]
- Dependencies Updated: [count]
- Critical Issues: [count]
- Major Issues: [count]
- Minor Issues: [count]

**Critical Actions Required:**
[List of must-fix issues, or "None"]

**Report Location:** LLM-CONTEXT/review-anal/report/review_report.md

**Full Report:**

[Include the complete report content here for presentation to user]
# Mark as complete
echo "SUCCESS" > LLM-CONTEXT/review-anal/report/status.txt
echo "✓ Report analysis complete"
echo "✓ Status: SUCCESS"
```

## Key Behaviors

- **ALWAYS gather all available analysis** results
- **ALWAYS categorize issues** by severity
- **ALWAYS provide clear approval status**
- **ALWAYS list actionable recommendations**
- **ALWAYS save final report** to LLM-CONTEXT/review-anal/report/review_report.md
- **NEVER approve with critical issues** - Security and test failures are blockers
