# Fix Analysis - Log Analyzer Subagent

**Purpose**: Analyze ONLY the .log files in LLM-CONTEXT/fix-anal/logs/ to identify errors, warnings, and issues that occurred during fix execution. This is NOT about code fixes - only about execution errors in the log files.

**Scope**: ONLY analyze files ending in .log in the logs directory
- orchestrator.log
- plan.log
- critical.log
- quality.log
- refactor_tests.log
- cache.log
- docs.log
- verification.log
- report.log
- etc.

**When to use**:
- After fix orchestrator completes (success or failure)
- When debugging fix execution issues
- To understand what went wrong during the fix process itself (not code issues)

**Outputs**:
- `LLM-CONTEXT/fix-anal/logs/log_analysis_report.md` - Analysis of log file errors
- `LLM-CONTEXT/fix-anal/logs/error_summary.json` - Structured error data from logs
- `LLM-CONTEXT/fix-anal/logs/recommendations.txt` - How to fix execution errors

---

## Step 1: Initialize

```bash
#!/bin/bash


echo "════════════════════════════════════════════════════════════════"
echo "Fix Log Analyzer"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Create output directory
mkdir -p LLM-CONTEXT/fix-anal/logs

# Set status
echo "IN_PROGRESS" > LLM-CONTEXT/fix-anal/logs/log_analyzer_status.txt

# Check if logs directory exists
if [ ! -d "LLM-CONTEXT/fix-anal/logs" ]; then
    echo "ERROR: No logs found to analyze"
    echo "FAILED" > LLM-CONTEXT/fix-anal/logs/log_analyzer_status.txt
    exit 1
fi

echo "✓ Logs directory found"
```

---

## Step 2: Scan All Log Files

```bash

cat > LLM-CONTEXT/fix-anal/logs/scan_logs.py << 'EOF'
"""Scan and analyze all fix log files.

Executed with: $PYTHON_CMD scan_logs.py
Requires: Python 3.13+
"""

import re
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

class FixLogAnalyzer:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.failures = []
        self.subagent_status = {}
        self.patterns = {
            'error': re.compile(r'\[ERROR\]|ERROR:|Error:|❌|FAILED', re.IGNORECASE),
            'warning': re.compile(r'\[WARNING\]|WARNING:|Warning:|⚠', re.IGNORECASE),
            'failure': re.compile(r'exit code [1-9]|command failed|not found|No such file', re.IGNORECASE),
            'success': re.compile(r'✓|SUCCESS|completed successfully', re.IGNORECASE),
            'timeout': re.compile(r'timeout|timed out', re.IGNORECASE),
            'permission': re.compile(r'permission denied|not permitted', re.IGNORECASE),
            'missing': re.compile(r'not found|does not exist|no such', re.IGNORECASE),
            'network': re.compile(r'connection refused|network error|could not resolve', re.IGNORECASE),
            'test_failure': re.compile(r'test.*failed|FAIL:|assertion|AssertionError', re.IGNORECASE),
            'git_error': re.compile(r'git.*error|merge conflict|rebase failed', re.IGNORECASE),
            'syntax_error': re.compile(r'SyntaxError|IndentationError|invalid syntax', re.IGNORECASE),
        }

    def analyze_log_file(self, log_path):
        """Analyze a single log file."""
        try:
            content = log_path.read_text(errors='ignore')
            lines = content.split('\n')

            result = {
                'file': str(log_path),
                'errors': [],
                'warnings': [],
                'failures': [],
                'test_failures': [],
                'git_errors': [],
                'line_count': len(lines),
                'error_count': 0,
                'warning_count': 0,
            }

            for i, line in enumerate(lines, 1):
                # Check for errors
                if self.patterns['error'].search(line):
                    result['errors'].append({
                        'line': i,
                        'text': line.strip(),
                        'type': self._classify_error(line)
                    })
                    result['error_count'] += 1

                # Check for warnings
                if self.patterns['warning'].search(line):
                    result['warnings'].append({
                        'line': i,
                        'text': line.strip(),
                    })
                    result['warning_count'] += 1

                # Check for failures
                if self.patterns['failure'].search(line):
                    result['failures'].append({
                        'line': i,
                        'text': line.strip(),
                    })

                # Check for test failures
                if self.patterns['test_failure'].search(line):
                    result['test_failures'].append({
                        'line': i,
                        'text': line.strip(),
                    })

                # Check for git errors
                if self.patterns['git_error'].search(line):
                    result['git_errors'].append({
                        'line': i,
                        'text': line.strip(),
                    })

            return result
        except Exception as e:
            return {
                'file': str(log_path),
                'error': f"Failed to analyze: {e}",
            }

    def _classify_error(self, line):
        """Classify error type based on content."""
        if self.patterns['test_failure'].search(line):
            return 'test_failure'
        elif self.patterns['git_error'].search(line):
            return 'git_error'
        elif self.patterns['syntax_error'].search(line):
            return 'syntax_error'
        elif self.patterns['timeout'].search(line):
            return 'timeout'
        elif self.patterns['permission'].search(line):
            return 'permission'
        elif self.patterns['missing'].search(line):
            return 'missing_resource'
        elif self.patterns['network'].search(line):
            return 'network'
        else:
            return 'general'

    def analyze_subagent_status(self):
        """Check status files for each fix subagent."""
        status_files = [
            'plan/status.txt',
            'critical/status.txt',
            'quality/status.txt',
            'refactor-tests/status.txt',
            'cache/status.txt',
            'docs/status.txt',
            'verification/status.txt',
            'report/status.txt',
        ]

        results = {}
        for status_file in status_files:
            path = Path(f'LLM-CONTEXT/fix-anal/{status_file}')
            subagent = status_file.split('/')[0]

            if path.exists():
                try:
                    status = path.read_text().strip()
                    results[subagent] = status
                except Exception as e:
                    results[subagent] = f'ERROR_READING: {e}'
            else:
                results[subagent] = 'MISSING'

        return results

    def analyze_git_commits(self):
        """Analyze git commits made during fix."""
        git_logs = []

        for domain in ['critical', 'quality', 'refactor-tests', 'cache', 'docs']:
            git_file = Path(f'LLM-CONTEXT/fix-anal/{domain}/git_commits.txt')
            if git_file.exists():
                try:
                    commits = git_file.read_text().strip()
                    if commits:
                        git_logs.append({
                            'domain': domain,
                            'commits': commits.split('\n')
                        })
                except Exception:
                    pass

        return git_logs

    def analyze_files_modified(self):
        """Analyze which files were modified during fix."""
        modified = {}

        for domain in ['critical', 'quality', 'refactor-tests', 'cache', 'docs']:
            mod_file = Path(f'LLM-CONTEXT/fix-anal/{domain}/files_modified.txt')
            if mod_file.exists():
                try:
                    files = mod_file.read_text().strip()
                    if files:
                        modified[domain] = files.split('\n')
                except Exception:
                    pass

        return modified

    def generate_report(self, log_results, status_results, git_commits, files_modified):
        """Generate comprehensive analysis report."""
        report = []
        report.append("# Fix Command Log Analysis Report")
        report.append(f"\n**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("\n---\n")

        # Summary
        total_errors = sum(r.get('error_count', 0) for r in log_results)
        total_warnings = sum(r.get('warning_count', 0) for r in log_results)
        total_failures = sum(len(r.get('failures', [])) for r in log_results)
        total_test_failures = sum(len(r.get('test_failures', [])) for r in log_results)
        total_git_errors = sum(len(r.get('git_errors', [])) for r in log_results)

        report.append("## Summary")
        report.append(f"\n- **Total Errors**: {total_errors}")
        report.append(f"- **Total Warnings**: {total_warnings}")
        report.append(f"- **Total Failures**: {total_failures}")
        report.append(f"- **Test Failures**: {total_test_failures}")
        report.append(f"- **Git Errors**: {total_git_errors}")
        report.append(f"- **Log Files Analyzed**: {len(log_results)}")

        # Subagent Status
        report.append("\n\n## Subagent Status\n")
        failed_subagents = []
        missing_subagents = []
        success_subagents = []

        for subagent, status in sorted(status_results.items()):
            if status == 'SUCCESS':
                success_subagents.append(subagent)
                report.append(f"- ✅ **{subagent}**: {status}")
            elif status == 'FAILED':
                failed_subagents.append(subagent)
                report.append(f"- ❌ **{subagent}**: {status}")
            elif status == 'MISSING':
                missing_subagents.append(subagent)
                report.append(f"- ⚠️  **{subagent}**: Status file not found")
            else:
                report.append(f"- ❓ **{subagent}**: {status}")

        # Git Commits
        if git_commits:
            report.append("\n\n## Git Commits Made\n")
            total_commits = sum(len(gc['commits']) for gc in git_commits)
            report.append(f"**Total commits**: {total_commits}\n")

            for gc in git_commits:
                report.append(f"\n### {gc['domain']}")
                for commit in gc['commits'][:10]:  # First 10 commits
                    report.append(f"- {commit}")

        # Files Modified
        if files_modified:
            report.append("\n\n## Files Modified\n")
            total_files = sum(len(files) for files in files_modified.values())
            report.append(f"**Total files modified**: {total_files}\n")

            for domain, files in files_modified.items():
                report.append(f"\n### {domain}")
                for file in files[:10]:  # First 10 files
                    report.append(f"- {file}")

        # Error Details
        if total_errors > 0:
            report.append("\n\n## Error Details\n")

            for result in log_results:
                if result.get('error_count', 0) > 0:
                    log_name = Path(result['file']).name
                    report.append(f"\n### {log_name}")
                    report.append(f"\n**Errors found**: {result['error_count']}\n")

                    # Group errors by type
                    errors_by_type = defaultdict(list)
                    for error in result['errors'][:20]:  # Limit to first 20
                        error_type = error.get('type', 'general')
                        errors_by_type[error_type].append(error)

                    for error_type, errors in errors_by_type.items():
                        report.append(f"\n**{error_type.upper()} Errors** ({len(errors)}):")
                        for error in errors[:5]:  # Show first 5 of each type
                            report.append(f"\n- Line {error['line']}: `{error['text'][:100]}`")

        # Test Failures
        if total_test_failures > 0:
            report.append("\n\n## Test Failures\n")

            for result in log_results:
                if result.get('test_failures'):
                    log_name = Path(result['file']).name
                    report.append(f"\n### {log_name}\n")

                    for failure in result['test_failures'][:10]:
                        report.append(f"- Line {failure['line']}: `{failure['text'][:100]}`")

        # Git Errors
        if total_git_errors > 0:
            report.append("\n\n## Git Errors\n")

            for result in log_results:
                if result.get('git_errors'):
                    log_name = Path(result['file']).name
                    report.append(f"\n### {log_name}\n")

                    for error in result['git_errors'][:10]:
                        report.append(f"- Line {error['line']}: `{error['text'][:100]}`")

        # Warnings
        if total_warnings > 0:
            report.append("\n\n## Warnings\n")

            warning_count = 0
            for result in log_results:
                if result.get('warning_count', 0) > 0 and warning_count < 10:
                    log_name = Path(result['file']).name
                    report.append(f"\n### {log_name}\n")

                    for warning in result['warnings'][:5]:
                        report.append(f"- Line {warning['line']}: `{warning['text'][:100]}`")
                        warning_count += 1
                        if warning_count >= 10:
                            break

        # Recommendations
        report.append("\n\n## Recommendations\n")

        if failed_subagents:
            report.append(f"\n### Failed Subagents ({len(failed_subagents)})\n")
            for subagent in failed_subagents:
                report.append(f"\n**{subagent}**:")
                report.append(f"- Check log: `LLM-CONTEXT/fix-anal/logs/{subagent}.log`")
                report.append(f"- Review output: `LLM-CONTEXT/fix-anal/{subagent}/`")
                report.append(f"- Look for ERROR messages indicating root cause")
                if subagent in ['critical', 'quality', 'refactor-tests']:
                    report.append(f"- Check if tests are passing: run test suite")
                if subagent == 'cache':
                    report.append(f"- Check before/after performance: `LLM-CONTEXT/fix-anal/cache/before_after_performance.txt`")

        if missing_subagents:
            report.append(f"\n### Missing Status Files ({len(missing_subagents)})\n")
            for subagent in missing_subagents:
                report.append(f"\n**{subagent}**:")
                report.append(f"- Subagent may not have run")
                report.append(f"- Check orchestrator log: `LLM-CONTEXT/fix-anal/logs/orchestrator.log`")
                report.append(f"- May have been skipped or crashed before completion")

        # Common issues
        report.append("\n\n## Common Issues and Solutions\n")

        # Analyze error types
        error_types = defaultdict(int)
        for result in log_results:
            for error in result.get('errors', []):
                error_types[error.get('type', 'general')] += 1

        if error_types.get('test_failure', 0) > 0:
            report.append("\n### Test Failures")
            report.append("\n**Issue**: Tests failing after fixes applied")
            report.append("\n**Solutions**:")
            report.append("- Review test output in critical/quality logs")
            report.append("- Check if fixes introduced regressions")
            report.append("- Verify test suite is up to date")
            report.append("- Consider reverting last commit and re-applying fix")

        if error_types.get('git_error', 0) > 0:
            report.append("\n### Git Errors")
            report.append("\n**Issue**: Git operations failed")
            report.append("\n**Solutions**:")
            report.append("- Check git status for conflicts")
            report.append("- Verify git repository is in clean state")
            report.append("- Review git_commits.txt in each subagent directory")
            report.append("- May need to manually resolve merge conflicts")

        if error_types.get('syntax_error', 0) > 0:
            report.append("\n### Syntax Errors")
            report.append("\n**Issue**: Code has syntax errors after fixes")
            report.append("\n**Solutions**:")
            report.append("- Review files_modified.txt in each subagent")
            report.append("- Check AST manipulation logs")
            report.append("- Run linter on modified files")
            report.append("- Consider reverting problematic commits")

        if error_types.get('missing_resource', 0) > 0:
            report.append("\n### Missing Resources")
            report.append("\n**Issue**: Files or commands not found")
            report.append("\n**Solutions**:")
            report.append("- Check if review was run first")
            report.append("- Verify review report exists: `LLM-CONTEXT/review-anal/report/review_report.md`")
            report.append("- Install missing dependencies")
            report.append("- Check if required tools are in PATH")

        if error_types.get('permission', 0) > 0:
            report.append("\n### Permission Errors")
            report.append("\n**Issue**: Permission denied errors")
            report.append("\n**Solutions**:")
            report.append("- Check file/directory permissions")
            report.append("- Verify write access to project files")
            report.append("- Verify write access to LLM-CONTEXT directory")
            report.append("- Check git repository permissions")

        return '\n'.join(report)

    def generate_json_summary(self, log_results, status_results, git_commits, files_modified):
        """Generate JSON summary for programmatic use."""
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_errors': sum(r.get('error_count', 0) for r in log_results),
            'total_warnings': sum(r.get('warning_count', 0) for r in log_results),
            'total_failures': sum(len(r.get('failures', [])) for r in log_results),
            'total_test_failures': sum(len(r.get('test_failures', [])) for r in log_results),
            'total_git_errors': sum(len(r.get('git_errors', [])) for r in log_results),
            'logs_analyzed': len(log_results),
            'subagent_status': status_results,
            'failed_subagents': [k for k, v in status_results.items() if v == 'FAILED'],
            'missing_subagents': [k for k, v in status_results.items() if v == 'MISSING'],
            'total_commits': sum(len(gc['commits']) for gc in git_commits),
            'total_files_modified': sum(len(files) for files in files_modified.values()),
            'git_commits': git_commits,
            'files_modified': files_modified,
            'error_details': []
        }

        for result in log_results:
            if result.get('error_count', 0) > 0:
                summary['error_details'].append({
                    'log_file': Path(result['file']).name,
                    'error_count': result['error_count'],
                    'warning_count': result['warning_count'],
                    'errors': result['errors'][:10]  # First 10 errors
                })

        return summary

def main():
    analyzer = FixLogAnalyzer()

    # Find all log files - ONLY .log files, nothing else
    log_dir = Path('LLM-CONTEXT/fix-anal/logs')
    if not log_dir.exists():
        print("ERROR: Logs directory not found")
        return

    log_files = [f for f in log_dir.glob('*.log') if f.is_file() and f.suffix == '.log']

    # DO NOT analyze any other files - only .log files
    print(f"Found {len(log_files)} .log files to analyze")
    print("SCOPE: Only analyzing execution log files, NOT fix findings or evidence")

    # Analyze each log file
    log_results = []
    for log_file in log_files:
        print(f"Analyzing: {log_file.name}")
        result = analyzer.analyze_log_file(log_file)
        log_results.append(result)

    # Analyze subagent status files
    print("Checking subagent status files...")
    status_results = analyzer.analyze_subagent_status()

    # Analyze git commits
    print("Analyzing git commits...")
    git_commits = analyzer.analyze_git_commits()

    # Analyze files modified
    print("Analyzing files modified...")
    files_modified = analyzer.analyze_files_modified()

    # Generate reports
    print("Generating analysis report...")
    report = analyzer.generate_report(log_results, status_results, git_commits, files_modified)

    report_path = Path('LLM-CONTEXT/fix-anal/logs/log_analysis_report.md')
    report_path.write_text(report)
    print(f"✓ Report written to: {report_path}")

    # Generate JSON summary
    print("Generating JSON summary...")
    summary = analyzer.generate_json_summary(log_results, status_results, git_commits, files_modified)

    summary_path = Path('LLM-CONTEXT/fix-anal/logs/error_summary.json')
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"✓ Summary written to: {summary_path}")

    # Generate recommendations file
    recommendations = []
    if summary['failed_subagents']:
        recommendations.append("FAILED SUBAGENTS:")
        for subagent in summary['failed_subagents']:
            recommendations.append(f"  - Check {subagent}: LLM-CONTEXT/fix-anal/logs/{subagent}.log")

    if summary['total_test_failures'] > 0:
        recommendations.append(f"\nTEST FAILURES: {summary['total_test_failures']}")
        recommendations.append("  - Review test output in logs")
        recommendations.append("  - Consider reverting last changes")

    if summary['total_git_errors'] > 0:
        recommendations.append(f"\nGIT ERRORS: {summary['total_git_errors']}")
        recommendations.append("  - Check git status")
        recommendations.append("  - Review git_commits.txt files")

    if summary['total_errors'] > 0:
        recommendations.append(f"\nTOTAL ERRORS: {summary['total_errors']}")
        recommendations.append("  - Review log_analysis_report.md for details")
        recommendations.append("  - Check error_summary.json for structured data")

    if summary['total_errors'] == 0 and not summary['failed_subagents']:
        recommendations.append("✓ No errors detected in fix execution")
        recommendations.append("✓ All subagents completed successfully")
        recommendations.append(f"✓ {summary['total_commits']} commits made")
        recommendations.append(f"✓ {summary['total_files_modified']} files modified")

    rec_path = Path('LLM-CONTEXT/fix-anal/logs/recommendations.txt')
    rec_path.write_text('\n'.join(recommendations))
    print(f"✓ Recommendations written to: {rec_path}")

    # Summary output
    print("\n" + "="*60)
    print("ANALYSIS SUMMARY")
    print("="*60)
    print(f"Errors:        {summary['total_errors']}")
    print(f"Warnings:      {summary['total_warnings']}")
    print(f"Test Failures: {summary['total_test_failures']}")
    print(f"Git Errors:    {summary['total_git_errors']}")
    print(f"Failed:        {len(summary['failed_subagents'])} subagents")
    print(f"Commits:       {summary['total_commits']}")
    print(f"Files:         {summary['total_files_modified']} modified")
    print("="*60)

if __name__ == '__main__':
    main()
EOF

python3 LLM-CONTEXT/fix-anal/logs/scan_logs.py 2>&1 | tee -a LLM-CONTEXT/fix-anal/logs/log_analyzer.log

if [ $? -eq 0 ]; then
    echo "SUCCESS" > LLM-CONTEXT/fix-anal/logs/log_analyzer_status.txt
else
    echo "FAILED" > LLM-CONTEXT/fix-anal/logs/log_analyzer_status.txt
    exit 1
fi

echo ""
echo "⚠️  IMPORTANT: This analysis is ONLY about .log file errors"
echo "⚠️  DO NOT analyze fix findings, evidence, or metrics from other directories"
echo "⚠️  DO NOT read files outside LLM-CONTEXT/fix-anal/logs/*.log"
echo ""
```

---

## Step 3: Present Results

```bash
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "Log Analysis Complete"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Show quick summary
if [ -f "LLM-CONTEXT/fix-anal/logs/error_summary.json" ]; then
    echo "📊 Summary:"
    python3 << 'EOF'
import json
from pathlib import Path

try:
    summary = json.loads(Path('LLM-CONTEXT/fix-anal/logs/error_summary.json').read_text())
    print(f"  Errors:        {summary['total_errors']}")
    print(f"  Warnings:      {summary['total_warnings']}")
    print(f"  Test Failures: {summary['total_test_failures']}")
    print(f"  Git Errors:    {summary['total_git_errors']}")
    print(f"  Failed:        {len(summary['failed_subagents'])} subagents")
    print(f"  Commits:       {summary['total_commits']}")
    print(f"  Files:         {summary['total_files_modified']} modified")

    if summary['failed_subagents']:
        print(f"\n  Failed subagents: {', '.join(summary['failed_subagents'])}")
except Exception as e:
    print(f"  Error reading summary: {e}")
EOF
fi

echo ""
echo "📄 Reports generated:"
echo "  - LLM-CONTEXT/fix-anal/logs/log_analysis_report.md"
echo "  - LLM-CONTEXT/fix-anal/logs/error_summary.json"
echo "  - LLM-CONTEXT/fix-anal/logs/recommendations.txt"
echo ""

# Show recommendations
if [ -f "LLM-CONTEXT/fix-anal/logs/recommendations.txt" ]; then
    echo "💡 Recommendations:"
    cat LLM-CONTEXT/fix-anal/logs/recommendations.txt | head -20
    echo ""
fi

```

---

## Notes

- **Runs after fix**: Should be final step in fix orchestrator
- **Non-blocking**: Errors in log analysis don't fail the fix
- **Comprehensive**: Analyzes all log files, status files, git commits, and modified files
- **Actionable**: Provides specific recommendations for fixing issues
- **Structured output**: JSON for programmatic access, Markdown for humans
- **Fix-specific**: Also tracks git commits and file modifications

**Usage**:
```bash
/bx_fix_anal_sub_analyze_command_logs
# Mark as complete
echo "SUCCESS" > LLM-CONTEXT/fix-anal/logs/status.txt
echo "✓ Analyze Command Logs analysis complete"
echo "✓ Status: SUCCESS"
```

**Output files**:
- `log_analysis_report.md` - Detailed human-readable report
- `error_summary.json` - Machine-readable error data
- `recommendations.txt` - Quick actionable fixes
- `log_analyzer.log` - Log of the analysis itself
- `log_analyzer_status.txt` - SUCCESS/FAILED status
