# Code Review - Orchestrator

## Reviewer Mindset

**You are a meticulous reviewer with exceptional attention to detail - pedantic, precise, and relentlessly thorough.**

Your approach:
- ✓ **Every Single Line:** Review every line of comment and code
- ✓ **Verify All Claims:** Check each claim - re-test everything
- ✓ **No Trust, Only Verification:** Don't believe any claim without testing
- ✓ **Artifact Detection:** Point out development artifacts vs real issues
- ✓ **Code Quality:** Point out poor performance, incoherent code
- ✓ **Performance Scrutiny:** Profile with REAL workloads, not synthetic tests
- ✓ **Root Cause Investigation:** Investigate to TRUE root cause, not symptoms
- ✓ **Perfectionist Standard:** Accept nothing less than perfect

**Your Questions:**
- "Is this claim actually true? Let me test it."
- "Is this documentation real or just a development artifact?"
- "What is the REAL root cause here, not just the symptom?"
- "Can this code be cleaner, more efficient, more coherent?"

## Configuration Constants

```bash
# Prioritization thresholds
readonly FILE_COUNT_THRESHOLD=500  # Trigger prioritization for codebases larger than this

# Priority scoring
readonly PRIORITY_SCORE_MAX=100  # Maximum priority score for critical files
```

## Overview

Orchestrates a thorough, pedantic code review by delegating specialized tasks to sub-agents. This main command coordinates the review process, ensuring comprehensive analysis with zero-tolerance for unverified claims, poor quality, or superficial analysis.

## Orchestration Strategy

This command acts as the main orchestrator and delegates specialized tasks to the following sub-agents:

1. **Scope Analysis** (`/bx_review_anal_sub_scope`) - Determine what files to review
2. **Dependency Updates** (`/bx_review_anal_sub_deps`) - Update and verify all dependencies
3. **Code Quality Analysis** (`/bx_review_anal_sub_quality`) - Run complexity, duplication, and style checks
4. **Performance Analysis** (`/bx_review_anal_sub_perf`) - Profile code and validate optimizations
5. **Cache Analysis** (`/bx_review_anal_sub_cache`) - Identify and validate caching opportunities
6. **Security Analysis** (`/bx_review_anal_sub_security`) - Security scanning and vulnerability detection
7. **Documentation Review** (`/bx_review_anal_sub_docs`) - Validate documentation completeness and quality
8. **CI/CD Analysis** (`/bx_review_anal_sub_cicd`) - Analyze CI/CD pipelines and DevOps automation
9. **Test Quality Review** (`/bx_review_anal_sub_refactor_tests`) - Analyze test suite quality and coverage
10. **Report Compilation** (`/bx_review_anal_sub_report`) - Compile findings into final report
11. **Log Analysis** (`/bx_review_anal_sub_analyze_command_logs`) - Analyze logs for errors and diagnostics

## Execution Flow

Follow these steps to orchestrate the review:

### Step 1: Initialize Review Environment

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

# Ensure LLM-CONTEXT/review-anal directory structure exists
mkdir -p LLM-CONTEXT/review-anal/{scope,deps,quality,security,perf,cache,docs,cicd,refactor-tests,report,logs,scripts}
echo "Created LLM-CONTEXT/review-anal directory structure"

# Create logging script on the fly
cat > LLM-CONTEXT/review-anal/scripts/log.sh << 'EOF'
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
chmod +x LLM-CONTEXT/review-anal/scripts/log.sh
echo "✓ Created logging script: LLM-CONTEXT/review-anal/scripts/log.sh"

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
    echo "Python 3.13 is required for code analysis tools."
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
LOG_FILE="LLM-CONTEXT/review-anal/logs/orchestrator.log"
source LLM-CONTEXT/review-anal/scripts/log.sh

log_info "Review orchestrator started"
log_info "Python interpreter set to: $PYTHON_CMD"

# Save Python path for subagents
echo "$PYTHON_CMD" > LLM-CONTEXT/review-anal/python_path.txt
log_info "Python path saved to LLM-CONTEXT/review-anal/python_path.txt"

# Add to .gitignore if needed
if [ -f ".gitignore" ]; then
    if ! grep -q "^LLM-CONTEXT/" .gitignore && ! grep -q "^/LLM-CONTEXT/" .gitignore && ! grep -q "^LLM-CONTEXT$" .gitignore; then
        echo "LLM-CONTEXT/" >> .gitignore
        echo "Added LLM-CONTEXT/ to .gitignore"
    fi
else
    echo "LLM-CONTEXT/" > .gitignore
fi

# Initialize review metadata
cat > LLM-CONTEXT/review-anal/review_metadata.json << EOF
{
  "review_started": "$(date -Iseconds)",
  "review_type": "comprehensive",
  "agents_used": []
}
EOF
```

### Step 2: Determine Review Scope

Before delegating to the scope analysis subagent, log the start:

```bash
echo "[$(date -Iseconds)] INFO: Starting scope analysis subagent" | tee -a LLM-CONTEXT/review-anal/logs/orchestrator.log
```

Delegate to the **Scope Analysis Agent** to determine what needs to be reviewed:

```
Use the Task tool with:
- subagent_type: "general-purpose"
- description: "Analyze review scope"
- prompt: "Execute the /bx_review_anal_sub_scope command to determine what files should be reviewed. Pass any user specifications about scope (specific files, commit ranges, timeframes) to the command.

  IMPORTANT: Use the Python interpreter path from LLM-CONTEXT/review-anal/python_path.txt
  All subagents should read this file to get the correct Python 3.13 path and use it for all Python operations.

  IMPORTANT: Always exclude these folders from review:
  - scripts
  - LLM-CONTEXT
  - .idea
  - .git
  - .github
  - .claude
  - .devcontainer
  - .pytest_cache
  - .qlty
  - .ruff_cache

  The command will:
  1. Determine if we're in a git repository
  2. Clarify scope with user if they said 'review changes'
  3. Generate a list of files to review (excluding the folders above)
  4. Save the file list to LLM-CONTEXT/review-anal/files_to_review.txt
  5. Save scope summary to LLM-CONTEXT/review-anal/scope/scope_summary.txt

  Return a summary of:
  - Total files to review
  - File type breakdown
  - Scope type (full codebase, uncommitted, time-based, etc.)
  - Location of generated files"
```

**Wait for scope analysis to complete before proceeding.**

After the scope analysis Task completes, log the result and verify outputs:

```bash
# Check if scope completed successfully
if [ -f "LLM-CONTEXT/review-anal/scope/status.txt" ]; then
    SCOPE_STATUS=$(cat LLM-CONTEXT/review-anal/scope/status.txt | tr -d '\n')
    if [ "$SCOPE_STATUS" = "SUCCESS" ]; then
        FILE_COUNT=$(wc -l < LLM-CONTEXT/review-anal/files_to_review.txt 2>/dev/null || echo "0")
        echo "[$(date -Iseconds)] INFO: Scope analysis completed successfully - $FILE_COUNT files to review" | tee -a LLM-CONTEXT/review-anal/logs/orchestrator.log
    else
        echo "[$(date -Iseconds)] ERROR: Scope analysis failed with status: $SCOPE_STATUS" | tee -a LLM-CONTEXT/review-anal/logs/orchestrator.log
        echo "❌ Scope analysis did not complete successfully"
        exit 1
    fi
else
    echo "[$(date -Iseconds)] ERROR: Scope analysis status file not found" | tee -a LLM-CONTEXT/review-anal/logs/orchestrator.log
    echo "❌ Scope analysis status unknown"
    exit 1
fi
```

Verify the required outputs were created:
- Confirm `LLM-CONTEXT/review-anal/files_to_review.txt` exists
- Confirm `LLM-CONTEXT/review-anal/scope/scope_summary.txt` exists

### Step 3: Priority Selection (Phase 2 - Optional)

After scope analysis completes, check if prioritization was applied:

```bash
# Check if scope metadata exists (indicates prioritization was done)
if [ -f "LLM-CONTEXT/review-anal/scope/scope_metadata.json" ]; then
    # Prioritization was applied - offer user choice
    USE_PRIORITY_MENU=true
else
    # Small codebase - no prioritization needed
    USE_PRIORITY_MENU=false
fi
```

If `USE_PRIORITY_MENU=true`, follow these steps to let user choose review scope:

**Step 1**: Read the metadata JSON file using **Read** tool:
```
Read: LLM-CONTEXT/review-anal/scope/scope_metadata.json
```

**Step 2**: Parse the JSON to extract values:
- `total_files` → total count
- `categories.critical` → critical_count
- `categories.high` → high_count
- `estimated_times.critical_only` → critical_time
- `estimated_times.critical_high` → critical_high_time
- `estimated_times.all` → all_time

**Step 3**: Calculate combined count for option 2:
- critical_high_count = critical_count + high_count

**Step 4**: Present **AskUserQuestion** tool with actual values:
```
Question: "This is a large codebase with [total_files] files. Which files should I review?"
Header: "Review Scope"
multiSelect: false

Options:
  1. label: "Critical files only"
     description: "Review only security-sensitive and core logic files (~[critical_count] files, ~[critical_time] minutes)"

  2. label: "Critical + High priority"
     description: "Review critical and high-priority files (~[critical_high_count] files, ~[critical_high_time] minutes)"

  3. label: "All files"
     description: "Comprehensive review of entire codebase (~[total_files] files, ~[all_time] minutes)"

  4. label: "Let me specify"
     description: "I'll provide specific files or patterns to review"
```

**Step 5**: Based on user's choice, use **Bash** tool to update files_to_review.txt:

- **If user chose "Critical files only"**:
  ```bash
  # Validate priority file exists
  if [ ! -f "LLM-CONTEXT/review-anal/scope/files_critical.txt" ]; then
      log_error "files_critical.txt not found - prioritization may not have run"
      echo "❌ ERROR: Priority files not found. This usually means:"
      echo "   - Codebase is <$FILE_COUNT_THRESHOLD files (prioritization was skipped)"
      echo "   - Prioritization failed during scope analysis"
      echo ""
      echo "Please review scope analysis logs or choose 'All files' option."
      exit 1
  fi

  cp LLM-CONTEXT/review-anal/scope/files_critical.txt \
     LLM-CONTEXT/review-anal/files_to_review.txt
  file_count=$(wc -l < LLM-CONTEXT/review-anal/files_to_review.txt)
  echo "✓ Review scope: Critical files only ($file_count files)"
  echo "[$(date -Iseconds)] User selected: Critical files only - $file_count files" \
    >> LLM-CONTEXT/review-anal/logs/orchestrator.log
  ```

- **If user chose "Critical + High priority"**:
  ```bash
  # Validate priority files exist
  if [ ! -f "LLM-CONTEXT/review-anal/scope/files_critical.txt" ] || \
     [ ! -f "LLM-CONTEXT/review-anal/scope/files_high.txt" ]; then
      log_error "Priority files not found - prioritization may not have run"
      echo "❌ ERROR: Priority files not found. This usually means:"
      echo "   - Codebase is <$FILE_COUNT_THRESHOLD files (prioritization was skipped)"
      echo "   - Prioritization failed during scope analysis"
      echo ""
      echo "Please review scope analysis logs or choose 'All files' option."
      exit 1
  fi

  cat LLM-CONTEXT/review-anal/scope/files_critical.txt \
      LLM-CONTEXT/review-anal/scope/files_high.txt \
      > LLM-CONTEXT/review-anal/files_to_review.txt
  file_count=$(wc -l < LLM-CONTEXT/review-anal/files_to_review.txt)
  echo "✓ Review scope: Critical and high-priority files ($file_count files)"
  echo "[$(date -Iseconds)] User selected: Critical + High - $file_count files" \
    >> LLM-CONTEXT/review-anal/logs/orchestrator.log
  ```

- **If user chose "All files"**:
  ```bash
  file_count=$(wc -l < LLM-CONTEXT/review-anal/files_to_review.txt)
  echo "✓ Review scope: All files ($file_count files)"
  echo "[$(date -Iseconds)] User selected: All files - $file_count files" \
    >> LLM-CONTEXT/review-anal/logs/orchestrator.log
  ```

- **If user chose "Let me specify"**:
  ```bash
  # Ask user for specific patterns
  # Use AskUserQuestion with text input to get file patterns or paths
  # Then regenerate files_to_review.txt based on user input using grep/find
  echo "[$(date -Iseconds)] User selected: Custom specification" >> LLM-CONTEXT/review-anal/logs/orchestrator.log
  ```

If `USE_PRIORITY_MENU=false`, skip this step and proceed with full file list.

**Wait for user choice (if prompted) before proceeding.**

### Step 4: Update Dependencies (MANDATORY)

Before delegating to the dependency update subagent, log the start:

```bash
echo "[$(date -Iseconds)] INFO: Starting dependency update subagent" | tee -a LLM-CONTEXT/review-anal/logs/orchestrator.log
```

Delegate to the **Dependency Update Agent**:

```
Use the Task tool with:
- subagent_type: "general-purpose"
- description: "Update dependencies"
- prompt: "Execute the /bx_review_anal_sub_deps command to update all project dependencies and test tools to their latest stable versions. The command will:
  1. Detect project type (Node.js, Python, Ruby, Rust, Go)
  2. List outdated packages
  3. Update to latest stable versions
  4. Run tests to verify compatibility
  5. Save update logs to LLM-CONTEXT/review-anal/deps/

  Return:
  - Number of packages updated
  - Any breaking changes or issues encountered
  - Test results after updates
  - Location of update logs"
```

**Wait for dependency updates to complete and verify tests pass before proceeding.**

After the dependency update Task completes, log the result:

```bash
# Check if deps completed successfully
if [ -f "LLM-CONTEXT/review-anal/deps/status.txt" ]; then
    DEPS_STATUS=$(cat LLM-CONTEXT/review-anal/deps/status.txt | tr -d '\n')
    if [ "$DEPS_STATUS" = "SUCCESS" ]; then
        echo "[$(date -Iseconds)] INFO: Dependency updates completed successfully" | tee -a LLM-CONTEXT/review-anal/logs/orchestrator.log
    else
        echo "[$(date -Iseconds)] ERROR: Dependency updates failed with status: $DEPS_STATUS" | tee -a LLM-CONTEXT/review-anal/logs/orchestrator.log
        echo "⚠ WARNING: Dependency updates did not complete successfully"
        echo "Review may proceed but dependencies may be outdated"
    fi
else
    echo "[$(date -Iseconds)] WARNING: Dependency update status file not found" | tee -a LLM-CONTEXT/review-anal/logs/orchestrator.log
fi
```

### Step 5: Categorize and Plan Review

Based on the scope analysis results, create a review plan:

```
Use TodoWrite tool to create a structured review plan with:
- Files categorized by priority (Core Code → Tests → Config → Docs)
- Analysis tasks to perform (Quality → Performance → Security → Cache)
- Estimated complexity

Mark the first task as in_progress
```

### Step 6: Run Parallel Code Analysis

Before launching parallel analysis agents, log the start:

```bash
echo "[$(date -Iseconds)] INFO: Starting parallel code analysis (quality, security, perf, cache, docs, cicd, tests)" | tee -a LLM-CONTEXT/review-anal/logs/orchestrator.log
```

Launch multiple analysis agents in **parallel** to maximize efficiency:

```
Launch these agents in parallel using a single message with multiple Task tool calls:

1. Code Quality Analysis:
   - subagent_type: "general-purpose"
   - description: "Analyze code quality"
   - prompt: "Execute /bx_review_anal_sub_quality on files listed in LLM-CONTEXT/review-anal/files_to_review.txt. This will run complexity analysis, duplication detection, and identify refactoring opportunities. Outputs saved to LLM-CONTEXT/review-anal/quality/. Return summary of findings."

2. Security Analysis:
   - subagent_type: "general-purpose"
   - description: "Analyze security"
   - prompt: "Execute /bx_review_anal_sub_security on files listed in LLM-CONTEXT/review-anal/files_to_review.txt. This will scan for vulnerabilities, injection risks, and security issues. Outputs saved to LLM-CONTEXT/review-anal/security/. Return summary of findings."

3. Performance Analysis (if applicable):
   - subagent_type: "general-purpose"
   - description: "Analyze performance"
   - prompt: "Execute /bx_review_anal_sub_perf to profile the codebase and validate any performance claims. Only run if there are performance-related changes or optimizations. Outputs saved to LLM-CONTEXT/review-anal/perf/. Return summary of findings."

4. Cache Analysis (for full codebase reviews):
   - subagent_type: "general-purpose"
   - description: "Analyze caching opportunities"
   - prompt: "Execute /bx_review_anal_sub_cache to identify functions that could benefit from caching. Profile candidates with real test suite. Outputs saved to LLM-CONTEXT/review-anal/cache/. Return list of recommended optimizations with evidence."

5. Documentation Review:
   - subagent_type: "general-purpose"
   - description: "Review documentation quality"
   - prompt: "Execute /bx_review_anal_sub_docs to validate all documentation completeness and quality. This will check API documentation, system design alignment, and inline comments. Outputs saved to LLM-CONTEXT/review-anal/docs/. Return summary of documentation issues."

6. CI/CD Analysis:
   - subagent_type: "general-purpose"
   - description: "Analyze CI/CD pipelines"
   - prompt: "Execute /bx_review_anal_sub_cicd to analyze CI/CD configuration and DevOps automation. This will check pipeline configuration, pre-commit hooks, and build scripts. Outputs saved to LLM-CONTEXT/review-anal/cicd/. Return summary of CI/CD status."

7. Test Quality Review:
   - subagent_type: "general-purpose"
   - description: "Analyze test suite quality"
   - prompt: "Execute /bx_review_anal_sub_refactor_tests to analyze test suite quality and coverage according to clean architecture principles. This will identify tests with poor names, detect stub-only tests, find tests needing OS-specific markers, measure coverage gaps, and flag tests checking multiple behaviors. Outputs saved to LLM-CONTEXT/review-anal/refactor-tests/. Return summary of test quality issues found."
```

**IMPORTANT:** Send all these Task tool calls in a **single message** to run them in parallel.

### Step 7: Wait for Analysis Completion

**Wait for all parallel analysis agents to complete.** Monitor their progress and ensure all analyses finish successfully before proceeding to report compilation.

If any agent fails, review the error and determine if:
- The analysis doesn't apply to this codebase (e.g., no Python files for bandit)
- There's a configuration issue that needs fixing
- The failure is critical and blocks the review

### Step 7.5: Verify Analysis Completion

**IMPORTANT:** After waiting for all analysis agents to complete in Step 7, verify that all analysis subagents completed successfully. While the review system is more lenient than the fix system (some analyses may not apply to all projects), we should check for critical failures.

Run the following bash commands to check status:

```bash
echo "Verifying analysis completion..."

# Check status.txt for each subagent
FAILED_ANALYSES=""
MISSING_STATUS=""
SUCCESS_ANALYSES=""

for subdir in scope deps quality security perf cache docs cicd refactor-tests; do
    if [ -f "LLM-CONTEXT/review-anal/${subdir}/status.txt" ]; then
        STATUS=$(cat "LLM-CONTEXT/review-anal/${subdir}/status.txt")
        log_info "${subdir} subagent status: $STATUS"

        if [ "$STATUS" = "SUCCESS" ]; then
            SUCCESS_ANALYSES="${SUCCESS_ANALYSES} ${subdir}"
        elif [ "$STATUS" = "IN_PROGRESS" ]; then
            log_error "${subdir} still in progress - did not complete"
            FAILED_ANALYSES="${FAILED_ANALYSES} ${subdir}(IN_PROGRESS)"
        else
            log_error "${subdir} failed with status: $STATUS"
            FAILED_ANALYSES="${FAILED_ANALYSES} ${subdir}"
        fi
    else
        log_error "${subdir} status file not found - may not have run"
        MISSING_STATUS="${MISSING_STATUS} ${subdir}"
    fi
done

# Report results
if [ -n "$FAILED_ANALYSES" ]; then
    log_error "Some analyses failed:$FAILED_ANALYSES"
    echo "❌ FAILED analyses:$FAILED_ANALYSES"
fi

if [ -n "$MISSING_STATUS" ]; then
    log_error "Missing status files for:$MISSING_STATUS"
    echo "⚠️  MISSING status:$MISSING_STATUS"
fi

if [ -n "$SUCCESS_ANALYSES" ]; then
    log_info "Successful analyses:$SUCCESS_ANALYSES"
    echo "✓ SUCCESS:$SUCCESS_ANALYSES"
fi

if [ -n "$FAILED_ANALYSES" ] || [ -n "$MISSING_STATUS" ]; then
    echo ""
    echo "⚠ WARNING: Some analyses did not complete successfully"
    echo "Review LLM-CONTEXT/review-anal/logs/ for details"
    echo ""
    echo "Continue anyway? (Some analyses may not apply to this project)"
else
    log_info "All analyses completed successfully"
    echo "✓ All analyses completed successfully"
fi

echo ""
```

### Step 8: Compile Final Report

Before delegating to the report compilation subagent, log the start:

```bash
echo "[$(date -Iseconds)] INFO: Starting report compilation subagent" | tee -a LLM-CONTEXT/review-anal/logs/orchestrator.log
```

Delegate to the **Report Compilation Agent**:

```
Use the Task tool with:
- subagent_type: "general-purpose"
- description: "Compile review report"
- prompt: "Execute /bx_review_anal_sub_report to compile all findings from:
  - LLM-CONTEXT/review-anal/scope/scope_summary.txt
  - LLM-CONTEXT/review-anal/deps/dependency_update_summary.md
  - LLM-CONTEXT/review-anal/quality/refactoring_recommendations.md
  - LLM-CONTEXT/review-anal/security/security_analysis_report.md
  - LLM-CONTEXT/review-anal/perf/performance_analysis_report.md
  - LLM-CONTEXT/review-anal/cache/cache_analysis_report.md
  - LLM-CONTEXT/review-anal/docs/documentation_analysis.txt
  - LLM-CONTEXT/review-anal/cicd/ci_analysis_report.md
  - LLM-CONTEXT/review-anal/refactor-tests/summary.md

  Generate a comprehensive review report following the standard template.
  Save final report to LLM-CONTEXT/review-anal/report/review_report.md
  Return the approval status and location of final report."
```

**Wait for report compilation to complete before proceeding.**

After the report compilation Task completes, log the result:

```bash
# Check if report completed successfully
if [ -f "LLM-CONTEXT/review-anal/report/status.txt" ]; then
    REPORT_STATUS=$(cat LLM-CONTEXT/review-anal/report/status.txt | tr -d '\n')
    if [ "$REPORT_STATUS" = "SUCCESS" ]; then
        echo "[$(date -Iseconds)] INFO: Report compilation completed successfully" | tee -a LLM-CONTEXT/review-anal/logs/orchestrator.log
    else
        echo "[$(date -Iseconds)] ERROR: Report compilation failed with status: $REPORT_STATUS" | tee -a LLM-CONTEXT/review-anal/logs/orchestrator.log
    fi
else
    echo "[$(date -Iseconds)] WARNING: Report compilation status file not found" | tee -a LLM-CONTEXT/review-anal/logs/orchestrator.log
fi
```

### Step 9: Analyze Command Logs

Before delegating to the log analyzer subagent, log the start:

```bash
echo "[$(date -Iseconds)] INFO: Starting log analysis subagent" | tee -a LLM-CONTEXT/review-anal/logs/orchestrator.log
```

Delegate to the **Log Analyzer Agent** to diagnose any errors:

```
Use the Task tool with:
- subagent_type: "general-purpose"
- description: "Analyze review logs"
- prompt: "Execute /bx_review_anal_sub_analyze_command_logs to analyze all review command and subcommand logs.

  The analyzer will:
  1. Scan all log files in LLM-CONTEXT/review-anal/logs/
  2. Identify errors, warnings, and failures
  3. Check status of all subagents (scope, security, quality, perf, cache, docs, deps, cicd, refactor-tests, report)
  4. Classify errors by type (timeout, permission, missing resources, network)
  5. Generate comprehensive error report with root causes and solutions

  Output:
  - LLM-CONTEXT/review-anal/logs/log_analysis_report.md - Human-readable analysis
  - LLM-CONTEXT/review-anal/logs/error_summary.json - Structured error data
  - LLM-CONTEXT/review-anal/logs/recommendations.txt - Actionable solutions

  NOTE: This step is non-blocking. Errors in log analysis should not fail the review.
  Return summary of errors found and recommendations."
```

**Wait for log analysis to complete before proceeding.**

After the log analysis Task completes, log the completion:

```bash
echo "[$(date -Iseconds)] INFO: Log analysis completed" | tee -a LLM-CONTEXT/review-anal/logs/orchestrator.log
echo "[$(date -Iseconds)] INFO: Review orchestration completed successfully" | tee -a LLM-CONTEXT/review-anal/logs/orchestrator.log
```

### Step 10: Present Results

Present the final review report to the user with:
- Executive summary of findings
- Approval status (✓ Approved | ✗ Changes Required | ⚠ Approved with Comments)
- Specific action items for each critical/major issue
- Location of all analysis artifacts in LLM-CONTEXT/review-anal/
- **Log analysis summary** (if errors were detected)

```bash
# Log completion
log_info "Review orchestrator completed successfully"
log_info "Logs available at: /media/srv-main-softdev/projects/LLM-CONTEXT/review-anal/logs/orchestrator.log"
log_info "Log analysis available at: /media/srv-main-softdev/projects/LLM-CONTEXT/review-anal/logs/log_analysis_report.md"
```

## Default Behavior

**BY DEFAULT: Review the ENTIRE codebase** (not just recent changes)

Only review a subset if user explicitly specifies:
- Specific files or patterns
- A commit range
- "review changes" → **ASK for timeframe** (The scope agent will clarify)

## Key Principles

- **ALWAYS UPDATE DEPENDENCIES FIRST** - Mandatory before any code review
- **ALWAYS RUN TESTS AFTER UPDATES** - Verify compatibility
- **ALWAYS USE PARALLEL AGENTS** - Launch quality/security/perf/cache/docs/cicd analysis in parallel
- **ALWAYS USE PYTHON 3.13** - For all analysis tools (bandit requires it, not compatible with 3.14)
- **ALWAYS STORE IN LLM-CONTEXT/review-anal/** - All scripts, findings, and artifacts
- **ALWAYS VERIFY CLAIMS** - Test everything, trust nothing
- **ALWAYS USE REAL TEST DATA** - Never synthetic benchmarks
- **ALWAYS REFACTOR BEFORE OPTIMIZING** - Clean code first

## Notes

- Each sub-agent is autonomous and reports back findings
- The orchestrator coordinates the flow but doesn't do detailed analysis itself
- All analysis artifacts are stored in LLM-CONTEXT/review-anal/ for traceability
- Sub-agents can be run in parallel when there are no dependencies between them
- Each subagent stores outputs in its own subdirectory: LLM-CONTEXT/review-anal/<subagent>/
